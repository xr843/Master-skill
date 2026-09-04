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
from typing import Optional

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

    Callers use this only when a real graded result is required. A dry-run suite
    is therefore evidence that the requested grading did not happen, not an
    exemption from the check.
    """
    if not suites:
        return ["fidelity result set contains 0 suites — it graded nothing"]

    problems = []
    for suite in suites:
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


def load_fidelity_suites(path: Path) -> list[dict]:
    """Load suites from runner output or a committed report wrapper."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        suites = data
    elif isinstance(data, dict) and isinstance(data.get("suites"), list):
        suites = data["suites"]
    else:
        raise ValueError(
            f"{path}: expected a runner result list or an object containing suites[]"
        )
    if not all(isinstance(suite, dict) for suite in suites):
        raise ValueError(f"{path}: every suite must be an object")
    return suites


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


def run_all(
    root: Path, fidelity_suites: Optional[list[dict]] = None
) -> list[str]:
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
    if fidelity_suites is not None:
        problems += check_graded_suites_graded_something(fidelity_suites)
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--fidelity-results",
        type=Path,
        help="runner JSON or committed report whose graded-suite liveness must be checked",
    )
    args = parser.parse_args()

    try:
        fidelity_suites = (
            load_fidelity_suites(args.fidelity_results)
            if args.fidelity_results is not None
            else None
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        problems = [f"cannot read fidelity results: {exc}"]
    else:
        problems = run_all(args.root, fidelity_suites)

    if args.json:
        print(json.dumps({"problems": problems, "ok": not problems}, ensure_ascii=False, indent=2))
    elif problems:
        print(f"✗ {len(problems)} gate-liveness problem(s):\n")
        for p in problems:
            print(f"  - {p}")
        print("\nA gate that examines nothing reports the same green as one that passes.")
    else:
        suffix = (
            "; fidelity result set produced a real verdict"
            if args.fidelity_results is not None
            else ""
        )
        print(f"✓ gate liveness ok — every configured local gate examined a non-empty set{suffix}")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
