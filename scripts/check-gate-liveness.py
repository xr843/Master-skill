#!/usr/bin/env python3
"""Assert that this repo's gates actually examined something.

Three shipped defects were the same shape — a gate examined an empty set and
reported success:

  - `pytest.ini` listed `testpaths = tests` while CI passed `scripts/tests/`
    explicitly, so neither suite ever ran the other's cases.
  - `tests/test_voice_rules.py` globbed `prebuilt/<slug>/voice.md` when
    voice.md lives under `references/`. The empty glob parametrized every case
    over an empty set: nothing asserted, reported green.
  - The fidelity smoke — a branch-protection-required check — writes
    `{"skipped": true, "reason": "no_api_key"}` and exits 0 when the secret is
    missing, which it always has been.

None of those was a wrong assertion. Each was an assertion that never ran, and
a passing check is indistinguishable from a check that did nothing unless
something asserts otherwise. That is this script's whole job.

Usage:
    python3 scripts/check-gate-liveness.py            # check this repo
    python3 scripts/check-gate-liveness.py --json     # machine-readable
"""

from __future__ import annotations

import argparse
import ast
import functools
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

# A verdict — as opposed to a skip, an error, or a dry run.
GRADED_STATUSES = {"PASS", "FAIL"}


def check_every_test_file_collects(
    test_files: list[str], collected_counts: dict[str, int]
) -> list[str]:
    """Every test file must contribute at least one collected test.

    A file that imports cleanly and yields nothing is the voice_rules failure:
    pytest reports success because there was nothing to fail.
    """
    problems = []
    for path in sorted(test_files):
        if collected_counts.get(path, 0) < 1:
            problems.append(
                f"{path} collected 0 tests — it asserts nothing but reports green "
                "(empty glob or empty parametrize?)"
            )
    return problems


def check_testpaths_cover_suites(
    testpaths: list[str], test_dirs: list[str]
) -> list[str]:
    """Every directory holding tests must be reachable from a bare `pytest`."""
    covered = set(testpaths)
    return [
        f"{d} holds tests but is not in pytest.ini testpaths — a bare `pytest` skips it"
        for d in sorted(test_dirs)
        if d not in covered
    ]


def check_graded_suites_graded_something(suites: list[dict]) -> list[str]:
    """A graded fidelity suite that produced no verdict must not read as a pass.

    Dry runs are exempt: grading nothing is what a dry run is for.
    """
    problems = []
    for suite in suites:
        if suite.get("mode") == "dry_run":
            continue
        verdicts = [
            r for r in suite.get("results", [])
            if str(r.get("status", "")).upper() in GRADED_STATUSES
        ]
        if not verdicts:
            problems.append(
                f"{suite.get('master', '?')}: graded suite produced 0 verdicts "
                "— it graded nothing (missing API key, or every call errored)"
            )
    return problems


def check_catalog_matches_filesystem(
    catalog: dict, prebuilt_dir: Path, root: Path
) -> list[str]:
    """The catalog and `prebuilt/` must name the same set of skills."""
    entries = catalog.get("skills", [])
    if not entries:
        problems = ["skill-catalog.json lists no skills — an empty catalog validates vacuously"]
        return problems

    problems = []
    catalog_sources = set()
    for entry in entries:
        source = entry.get("source", "")
        catalog_sources.add(source)
        if source.startswith("prebuilt/") and not (root / source).is_dir():
            problems.append(
                f"{entry.get('name', '?')}: catalog points at {source}, which does not exist"
            )

    if prebuilt_dir.is_dir():
        for d in sorted(p for p in prebuilt_dir.iterdir() if p.is_dir()):
            rel = f"prebuilt/{d.name}"
            if rel not in catalog_sources:
                problems.append(
                    f"{d.name}: directory exists under prebuilt/ but no catalog entry "
                    "claims it — it ships to nobody and no gate examines it"
                )
    return problems


def check_every_skill_has_fixtures(prebuilt_dir: Path) -> list[str]:
    """Every prebuilt skill must carry at least one fidelity fixture."""
    if not prebuilt_dir.is_dir():
        return [f"{prebuilt_dir} does not exist — nothing to examine"]

    problems = []
    for d in sorted(p for p in prebuilt_dir.iterdir() if p.is_dir()):
        fixtures = d / "tests" / "fidelity.jsonl"
        if not fixtures.exists():
            problems.append(f"{d.name}: no tests/fidelity.jsonl — nothing grades this skill")
            continue
        lines = [ln for ln in fixtures.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            problems.append(f"{d.name}: tests/fidelity.jsonl is empty — it grades 0 cases")
    return problems


# A gate is "advisory" when it can exit 0 without doing the work its name
# promises — the fidelity smoke passing in 10s because no API key is set. That
# is a legitimate project decision (CONTRIBUTING.md §2: grading is a local /
# pre-release step, not a CI expense). What is NOT legitimate is it being
# invisible: a required check's green tick looks identical either way.
#
# So each advisory gate must be declared here, saying what it does not check.
# An undeclared one fails this script, and the declared roster is printed on
# every run — `npm test` always answers "what did the green tick examine?".
#
# Detection is automatic only for the "missing secret -> exit 0" shape, which
# is the one this repo shipped. A job that goes quiet for some other reason —
# `Dependency review` skipping because the dependency graph is off — has to be
# added by hand. `check_declared_gates_still_exist` then keeps the entry from
# outliving the job, but nothing can force a new *shape* to be noticed. If you
# add a gate that can pass without working, put it here yourself.
ADVISORY_GATES = {
    "Fidelity smoke (1 master × 1 fixture)": (
        "grades nothing when ANTHROPIC_API_KEY is unset (it always has been) — "
        "the green tick means structure validation passed, not that a model "
        "response was graded. Set repo variable FIDELITY_GRADING_REQUIRED=true "
        "once the secret exists to make the skip a hard failure."
    ),
    "Fidelity tests — full suite (weekly + manual)": (
        "same skip as the smoke, on the weekly cron"
    ),
    "Persona-fidelity schema + advisory eval": (
        "llm-rubric eval is `|| true` and is skipped entirely without a key; "
        "only the promptfoo schema + repo-convention validation is real"
    ),
}

# A gate that runs nowhere on a pull request has never guarded a change. This repo
# has shipped that twice: `validate-curriculum-sources.py` was "wired into no
# workflow, no npm script and no sub-check — only its own unit tests" (see the
# sub-check in validate.py that now runs it), and on 2026-09-16
# `validate-citation-templates.py` and `validate-self-audit-sources.py` were found
# to live only inside `npm test`, which only npm-publish.yml runs, on a published
# release. Both passed — the defect was latent, which is exactly why nothing
# surfaced it.
#
# Every entry script under scripts/ must therefore be reachable from a workflow
# that triggers on `pull_request`, or be declared here with the reason it is not.
# `check_every_gate_runs_on_a_pr` keeps this true in both directions.
NOT_A_PR_GATE = {
    "cite.py": (
        "a reader-facing offline lookup tool, documented in README.md and in the "
        "personas' own SKILL.md; not a gate over repository content"
    ),
    "query.py": (
        "a reader-facing offline search tool, documented alongside cite.py; not a "
        "gate over repository content"
    ),
    "check-pe-subsystem.py": (
        "inspects a built Windows executable, which exists only after the desktop "
        "release build — release-desktop.yml is the only place it can run"
    ),
    "reaudit-report.py": (
        "re-audits a committed eval run's stored answers; run by hand after a paid "
        "sweep, against a report that does not exist on a PR"
    ),
    "regrade-report.py": (
        "re-grades a committed eval run against the current judge; same as "
        "reaudit-report.py — it needs a report a PR does not produce"
    ),
}


# `npm test` is what CONTRIBUTING tells a contributor to run before touching
# scripts/, in its own words 「避免在 CI 才发现」. A command that exists to pre-empt CI
# has to cover what CI checks. It has fallen behind twice: pytest was missing from it
# until 2026-09-03, and on 2026-09-16 four content gates the PR job runs —
# validate-citation-contract, validate-cross-critique, validate-lore-triggers-content
# and validate-quote-attribution — were absent, so a contributor could go green
# locally and still be failed by CI.
#
# Anything the per-PR job runs must therefore appear in `npm test` too, or be
# declared here. `check_npm_test_covers_pr_gates` keeps this true in both directions.
NOT_IN_NPM_TEST = {
    "check-eval-sdk-surface.py": (
        "asserts the pinned eval SDKs still expose what test-fidelity.py calls — it "
        "needs requirements-eval.txt installed, which a content contributor has no "
        "reason to have"
    ),
    "smoke-eval-sdk.py": (
        "stands up a local server for a keyless end-to-end SDK smoke; same eval-only "
        "dependency, and far slower than the content gates around it"
    ),
    "select-fidelity-smoke.py": (
        "picks which persona the CI smoke grades from job metadata — a CI scheduling "
        "helper, not a check over repository content"
    ),
    "check-audit-ignores.py": (
        "takes the cargo-audit JSON as an argument — security-scan.yml runs "
        "`cargo audit --file desktop/Cargo.lock --json > audit.json` first. Without a "
        "Rust toolchain and the advisory database there is nothing for it to read; "
        "run bare it exits 2 on argparse usage"
    ),
}


# The shape of a silent skip: a step that exits 0 because a secret is missing.
_SKIP_ON_MISSING_SECRET = re.compile(r'\[\s+-z\s+"\$\{[A-Z_]+:-\}"\s+\]')


def _job_display_name(job_id: str, job: dict) -> str:
    """The name this file can see for a job.

    NOT, in general, "the string branch protection matches on" — an earlier
    version of this docstring said that and it is false for any matrix job.
    GitHub expands `name: CodeQL (${{ matrix.language }})` into one check run
    per leg (`CodeQL (python)`, …); statically all that is visible here is the
    unexpanded template. So a matrix job can never be matched by an
    ADVISORY_GATES key, and this module cannot police one. The roster covers
    the non-matrix jobs, which are the ones this repo has actually shipped a
    silent skip in; a matrix job that grows one has to be caught by review.
    """
    name = job.get("name") if isinstance(job, dict) else None
    return str(name) if name else job_id


def _job_skips_on_missing_secret(job: dict) -> bool:
    steps = job.get("steps") or [] if isinstance(job, dict) else []
    for step in steps:
        if not isinstance(step, dict):
            continue
        run = step.get("run")
        if isinstance(run, str) and _SKIP_ON_MISSING_SECRET.search(run):
            return True
    return False


def _iter_jobs(workflow_docs: dict[str, dict]):
    """Yield (path, display_name, job) for every job in every workflow.

    Per **job**, not per file: `validate-and-test.yml` holds six jobs, and a
    file-level check would let a newly-silent seventh hide behind its declared
    siblings.
    """
    for path, doc in sorted(workflow_docs.items()):
        jobs = (doc or {}).get("jobs") or {}
        if not isinstance(jobs, dict):
            continue
        for job_id, job in jobs.items():
            if isinstance(job, dict):
                yield path, _job_display_name(job_id, job), job


def check_advisory_gates_declared(workflow_docs: dict[str, dict]) -> list[str]:
    """Every job that can exit 0 on a missing secret must be declared above.

    Catches the case this repo actually shipped: a *required* branch-protection
    check that has never once graded a response, with nothing in the repo
    saying so.
    """
    return [
        f"{path}: job {name!r} exits 0 when a secret is missing but is not in "
        "ADVISORY_GATES — a gate that can pass without checking anything must "
        "say so, or stop doing it"
        for path, name, job in _iter_jobs(workflow_docs)
        if _job_skips_on_missing_secret(job) and name not in ADVISORY_GATES
    ]


def check_declared_gates_still_exist(workflow_docs: dict[str, dict]) -> list[str]:
    """The reverse drift: a declaration outliving the job it describes.

    A stale entry is worse than none — it asserts a caveat about a gate that no
    longer exists, and hides the day a real gate quietly becomes advisory.
    """
    live = {name for _, name, _ in _iter_jobs(workflow_docs)}
    return [
        f"ADVISORY_GATES declares {name!r}, but no workflow job has that name "
        "— stale declaration, or the job was renamed"
        for name in sorted(ADVISORY_GATES)
        if name not in live
    ]


# ---------------------------------------------------------------------------
# Repo-level wiring
# ---------------------------------------------------------------------------


def _script_references(source: str, scripts: set[str]) -> set[str]:
    """Which other scripts this source actually runs — imports and loaded filenames.

    Both spellings are in use: `validate.py` loads five siblings through
    `spec_from_file_location(..., "validate-curriculum-sources.py")`, which puts the
    literal filename in the source, while `verify_citations.py` is pulled in as
    `from verify_citations import …`. Counting only workflow text would report both
    as unreachable and invent a defect where there is none.

    Read through `ast`, not as text. The first version matched filenames anywhere in
    the source and reported five scripts as reachable on the strength of *comments*:
    `verify_citations.py` mentions "scripts/query.py" in a comment about a shared
    guard, and verify_citations is imported by a job the PR runs, so query.py came
    out "reachable". Comments do not survive parsing, and an exact-match on string
    constants keeps a docstring that merely names a path from counting as a call.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:  # pragma: no cover — a syntactically broken script
        return set()

    wanted = {name: {name, f"scripts/{name}"} for name in scripts}
    modules = {name[:-3]: name for name in scripts if "-" not in name[:-3]}
    hit: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in modules:
            hit.add(modules[node.module])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in modules:
                    hit.add(modules[alias.name])
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            for name, spellings in wanted.items():
                if node.value in spellings:
                    hit.add(name)
    return hit


def pr_reachable_scripts(root: Path, workflow_docs: dict[str, dict]) -> set[str]:
    """Scripts a pull request actually executes, following indirect calls."""
    scripts_dir = root / "scripts"
    names = {p.name for p in scripts_dir.glob("*.py")}
    # This file names five scripts in NOT_A_PR_GATE, and this file runs on every PR.
    # Counting its own source as a caller made each declared script "reachable" and
    # then reported the declaration as stale — the checker proving its own entries
    # wrong. Declaring a script is not calling it.
    sources = {
        p.name: p.read_text(encoding="utf-8")
        for p in scripts_dir.glob("*.py")
        if p.name != Path(__file__).name
    }

    reachable: set[str] = set()
    for path, doc in workflow_docs.items():
        triggers = doc.get("on", doc.get(True))
        keys = set(triggers) if isinstance(triggers, (dict, list)) else set()
        if "pull_request" not in keys:
            continue
        reachable |= {name for name in names if name in (root / path).read_text(encoding="utf-8")}

    # Fixpoint: a script the PR runs may load or import others.
    while True:
        grown = set(reachable)
        for name in list(reachable):
            grown |= _script_references(sources.get(name, ""), names)
        if grown == reachable:
            return reachable
        reachable = grown


def check_every_gate_runs_on_a_pr(root: Path, workflow_docs: dict[str, dict]) -> list[str]:
    """An entry script must run on a pull request, or say why it does not."""
    scripts_dir = root / "scripts"
    if not scripts_dir.is_dir():
        return []
    entries = {
        p.name
        for p in scripts_dir.glob("*.py")
        if "def main(" in p.read_text(encoding="utf-8")
    }
    reachable = pr_reachable_scripts(root, workflow_docs)

    problems = [
        f"scripts/{name} runs nowhere on a pull request and is not in NOT_A_PR_GATE "
        "— a gate whose first real execution is the release has guarded nothing"
        for name in sorted(entries - reachable)
        if name not in NOT_A_PR_GATE
    ]
    problems += [
        f"NOT_A_PR_GATE declares {name!r}, but no such script exists — stale entry"
        for name in sorted(NOT_A_PR_GATE)
        if name not in entries
    ]
    problems += [
        f"NOT_A_PR_GATE declares {name!r}, but a pull request does run it now "
        "— drop the entry rather than leave a false caveat standing"
        for name in sorted(NOT_A_PR_GATE)
        if name in reachable
    ]
    return problems


def npm_test_scripts(root: Path) -> set[str]:
    """The scripts the documented pre-push command actually runs."""
    package = root / "package.json"
    if not package.exists():
        return set()
    data = json.loads(package.read_text(encoding="utf-8"))
    command = str((data.get("scripts") or {}).get("test") or "")
    return set(re.findall(r"scripts/([a-z0-9_-]+\.py)", command))


def pr_workflow_scripts(root: Path, workflow_docs: dict[str, dict]) -> set[str]:
    """Scripts named outright by a workflow that triggers on `pull_request`.

    Direct mentions only, unlike `pr_reachable_scripts`: `npm test` runs commands, so
    what it has to match is the commands CI runs, not everything those import.
    """
    named: set[str] = set()
    for path, doc in workflow_docs.items():
        triggers = doc.get("on", doc.get(True))
        keys = set(triggers) if isinstance(triggers, (dict, list)) else set()
        if "pull_request" not in keys:
            continue
        named |= set(re.findall(r"scripts/([a-z0-9_-]+\.py)", (root / path).read_text(encoding="utf-8")))
    return named


def check_npm_test_covers_pr_gates(root: Path, workflow_docs: dict[str, dict]) -> list[str]:
    """What CI runs on a PR, `npm test` must run too — or say why it does not."""
    if not (root / "package.json").exists():
        return []
    in_ci = pr_workflow_scripts(root, workflow_docs)
    in_npm = npm_test_scripts(root)

    problems = [
        f"scripts/{name} runs on every PR in CI but is not in `npm test` and not in "
        "NOT_IN_NPM_TEST — the command that exists to pre-empt CI does not cover it"
        for name in sorted(in_ci - in_npm)
        if name not in NOT_IN_NPM_TEST
    ]
    problems += [
        f"NOT_IN_NPM_TEST declares {name!r}, but `npm test` runs it now — drop the "
        "entry rather than leave a false caveat standing"
        for name in sorted(NOT_IN_NPM_TEST)
        if name in in_npm
    ]
    problems += [
        f"NOT_IN_NPM_TEST declares {name!r}, but no PR workflow runs it — stale entry"
        for name in sorted(NOT_IN_NPM_TEST)
        if name not in in_ci
    ]
    return problems


def discover_test_files(root: Path) -> list[str]:
    return sorted(
        str(p.relative_to(root))
        for d in ("tests", "scripts/tests")
        for p in (root / d).glob("test_*.py")
        if (root / d).is_dir()
    )


def discover_test_dirs(root: Path) -> list[str]:
    return sorted(
        d for d in ("tests", "scripts/tests")
        if (root / d).is_dir() and any((root / d).glob("test_*.py"))
    )


def read_testpaths(root: Path) -> list[str]:
    ini = root / "pytest.ini"
    if not ini.exists():
        return []
    for line in ini.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("testpaths"):
            return line.split("=", 1)[1].split()
    return []


@functools.lru_cache(maxsize=None)
def _collect_counts_cached(root: str) -> tuple[tuple[str, int], ...]:
    """One `pytest --collect-only` per process, not per caller.

    The CLI calls `run_all` once and never noticed. The test suite calls it six
    times, and each call forked a full collection of the whole suite — measured
    1.11s each, ~7s of a 20s `npm test`. Worse, it grew with the suite: every
    test added made those six slower, so the cost compounded exactly as the
    project got more tests. Cached on the resolved root; the collection cannot
    change within a process.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=root, capture_output=True, text=True,
    )
    counts: dict[str, int] = {}
    for line in proc.stdout.splitlines():
        match = re.match(r"^([\w./-]+\.py)::", line.strip())
        if match:
            counts[match.group(1)] = counts.get(match.group(1), 0) + 1
    return tuple(sorted(counts.items()))


def collect_counts(root: Path) -> dict[str, int]:
    """Ask pytest what it actually collects, per file."""
    return dict(_collect_counts_cached(str(Path(root).resolve())))


def read_workflows(root: Path) -> dict[str, dict]:
    wf_dir = root / ".github" / "workflows"
    if not wf_dir.is_dir():
        return {}
    return {
        str(p.relative_to(root)): yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for p in sorted(wf_dir.glob("*.yml"))
    }


def _declares_a_skip(report: Path) -> bool:
    """Whether the report says outright that it graded nothing on purpose."""
    data = json.loads(report.read_text(encoding="utf-8"))
    return isinstance(data, dict) and bool(data.get("skipped"))


def load_fidelity_suites(report: Path) -> list[dict]:
    """Read a `test-fidelity.py --json` report into a suite list.

    A declared skip (`{"skipped": true, "reason": "no_api_key"}`) is not a
    suite — it is the advisory path, already accounted for by ADVISORY_GATES.
    Anything else claiming to be a run gets checked for actual verdicts.
    """
    data = json.loads(report.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        if data.get("skipped"):
            return []
        data = [data]
    return [s for s in data if isinstance(s, dict) and not s.get("skipped")]


def run_all(root: Path, fidelity_report: Path | None = None) -> list[str]:
    problems: list[str] = []

    test_files = discover_test_files(root)
    if not test_files:
        return ["no test files found at all — this check would pass vacuously"]

    problems += check_every_test_file_collects(test_files, collect_counts(root))
    problems += check_testpaths_cover_suites(read_testpaths(root), discover_test_dirs(root))

    catalog_path = root / "skill-catalog.json"
    if catalog_path.exists():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        problems += check_catalog_matches_filesystem(catalog, root / "prebuilt", root)

    problems += check_every_skill_has_fixtures(root / "prebuilt")

    workflows = read_workflows(root)
    problems += check_advisory_gates_declared(workflows)
    problems += check_declared_gates_still_exist(workflows)
    problems += check_every_gate_runs_on_a_pr(root, workflows)
    problems += check_npm_test_covers_pr_gates(root, workflows)

    # check_graded_suites_graded_something shipped fully written and unit-tested
    # but unreferenced by run_all — the anti-fake-green script had a check that
    # itself never ran. This is where it runs.
    if fidelity_report is not None:
        # A missing file is a problem, not a pass. `… and fidelity_report.exists()`
        # meant `--fidelity-report /nonexistent.json` printed "every gate examined
        # a non-empty set" about a report it never opened — the exact statement
        # this script exists to make impossible.
        if not fidelity_report.exists():
            problems.append(
                f"{fidelity_report} was named as the fidelity report but does "
                "not exist — nothing was examined"
            )
        else:
            suites = load_fidelity_suites(fidelity_report)
            if not suites and not _declares_a_skip(fidelity_report):
                problems.append(
                    f"{fidelity_report} contains no suites and does not declare "
                    "a skip — it grades nothing but reads as clean"
                )
            problems += check_graded_suites_graded_something(suites)
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--fidelity-report",
        type=Path,
        default=None,
        help="a test-fidelity.py --json report; assert it produced real verdicts",
    )
    args = parser.parse_args()

    problems = run_all(args.root, args.fidelity_report)

    if args.json:
        print(json.dumps(
            {"problems": problems, "ok": not problems, "advisory_gates": ADVISORY_GATES},
            ensure_ascii=False, indent=2,
        ))
    elif problems:
        print(f"✗ {len(problems)} gate-liveness problem(s):\n")
        for p in problems:
            print(f"  - {p}")
        print("\nA gate that examines nothing reports the same green as one that passes.")
    else:
        print("✓ gate liveness ok — every gate examined a non-empty set")
        # Printed on success, not just failure: the roster is the answer to
        # "what did that green tick actually examine?", and it is only useful
        # if you see it without going looking.
        print(f"\n⚠ {len(ADVISORY_GATES)} advisory gate(s) — green does NOT mean these ran:")
        for name, caveat in sorted(ADVISORY_GATES.items()):
            print(f"  - {name}\n      {caveat}")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
