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

# The shape of a silent skip: a step that exits 0 because a secret is missing.
_SKIP_ON_MISSING_SECRET = re.compile(r'\[\s+-z\s+"\$\{[A-Z_]+:-\}"\s+\]')


def _job_display_name(job_id: str, job: dict) -> str:
    """The name GitHub shows — and the string branch protection matches on."""
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


def collect_counts(root: Path) -> dict[str, int]:
    """Ask pytest what it actually collects, per file."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=root, capture_output=True, text=True,
    )
    counts: dict[str, int] = {}
    for line in proc.stdout.splitlines():
        match = re.match(r"^([\w./-]+\.py)::", line.strip())
        if match:
            counts[match.group(1)] = counts.get(match.group(1), 0) + 1
    return counts


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
