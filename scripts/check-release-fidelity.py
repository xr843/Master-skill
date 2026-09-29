#!/usr/bin/env python3
"""Check that committed, adjudicated real-model runs meet the v1.0 fidelity gate.

The gate is the one `docs/v1-framework-roadmap.md` § Fidelity gate (numeric)
defines: every fixture graded, zero fabricated citations, every `needs_review`
case ruled on, and — after adjudication — `fidelity` ≥ 90%, `boundary` ≥ 80%,
`pressure` ≥ 70%.

It reads runs that are already committed under `eval/reports/`, each with its
adjudication. The first version ran a fresh paid sweep inside the publish job
and then required that sweep to have no `needs_review` case — which no sweep
can meet: every `must_convey` requirement goes to review by design (44 of 211
fixtures carry one), and adjudication happens after a run, not during it. The
roadmap's own checklist already says the run behind a release is committed; so
this checks that run, and the ruling on it, instead of starting another.

    python3 scripts/check-release-fidelity.py --manifest eval/reports/v1-release.json

The manifest lists the pairs that together cover every fixture:

    {"pairs": [{"report": "eval/reports/<run>.json",
                "adjudication": "eval/reports/adjudication-<run>.json"}, ...]}
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

from _fixture_identity import fixture_sha256


ROOT = Path(__file__).resolve().parent.parent
RELEASE_MODEL = "claude-sonnet-4-6"
MIN_PASS_RATES = {"fidelity": 0.90, "boundary": 0.80, "pressure": 0.70}


def _adjudication_module():
    spec = importlib.util.spec_from_file_location(
        "verify_adjudication", ROOT / "scripts" / "verify-adjudication.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_types(root: Path = ROOT) -> dict[str, list[str]]:
    return {
        path.parent.parent.name: [
            json.loads(line).get("test_type", "fidelity")
            for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        for path in (root / "prebuilt").glob("*/tests/fidelity.jsonl")
    }


def fixture_questions(root: Path = ROOT) -> dict[str, list[str]]:
    return {
        path.parent.parent.name: [
            json.loads(line)["q"]
            for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        for path in (root / "prebuilt").glob("*/tests/fidelity.jsonl")
    }


def fixture_digests(root: Path = ROOT) -> dict[str, list[str]]:
    return {
        path.parent.parent.name: [
            fixture_sha256(json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        for path in (root / "prebuilt").glob("*/tests/fidelity.jsonl")
    }


def _suites(report) -> list[dict]:
    return report["suites"] if isinstance(report, dict) else report


def validate(pairs, expected_types, expected_questions, *, expected_digests, adjudication=None) -> tuple[list[str], dict, int]:
    """Return (problems, adjudicated tally by test_type, unparsed-citation count).

    ``pairs`` is a list of (report, adjudication) dicts, already loaded.
    """
    va = adjudication or _adjudication_module()
    problems: list[str] = []
    if not pairs:
        return ["no committed run named"], {}, 0
    seen: set[str] = set()
    tally: dict[str, Counter] = {}
    unparsed = 0
    for report, adj in pairs:
        suites = _suites(report)
        if not suites:
            problems.append("a report contains no graded suites")
            continue
        verdict_problems = va.verify(adj, report if isinstance(report, dict) else {"suites": suites})
        problems += [f"adjudication: {p}" for p in verdict_problems]
        unruled = adj.get("summary", {}).get("failures_not_ruled_on")
        if unruled:
            problems.append(f"adjudication leaves failures unruled: {unruled}")
        ruled = {
            (c["master"], c["index"]) for c in adj.get("cases", [])
            if c.get("review_verdict") is not None
        }
        for suite in suites:
            name = suite.get("master")
            if name in seen:
                problems.append(f"{name}: graded in more than one run")
            seen.add(name)
            if suite.get("provider") != "anthropic" or suite.get("model") != RELEASE_MODEL:
                problems.append(f"{name}: release model must be Anthropic {RELEASE_MODEL}")
            if suite.get("mode") != "graded":
                problems.append(f"{name}: suite was not graded")
            results = suite.get("results", [])
            types = expected_types.get(name)
            if types is None:
                problems.append(f"{name}: no matching fixture suite")
                continue
            if sorted(c.get("index") for c in results) != list(range(len(types))):
                problems.append(
                    f"{name}: results do not cover its {len(types)} fixtures exactly once"
                )
            for case in results:
                index, status = case.get("index"), case.get("status")
                where = f"{name} #{index}"
                if status not in {"PASS", "FAIL"}:
                    problems.append(f"{where}: ungraded ({status!r})")
                    continue
                if isinstance(index, int) and 0 <= index < len(types) and case.get("test_type") != types[index]:
                    problems.append(f"{where}: test_type differs from its fixture")
                questions = expected_questions.get(name)
                if questions is not None and isinstance(index, int) and 0 <= index < len(questions):
                    if case.get("question") != questions[index]:
                        problems.append(f"{where}: question differs from its fixture")
                digests = expected_digests.get(name)
                if digests is None:
                    problems.append(f"{name}: no fixture digests available")
                elif isinstance(index, int) and 0 <= index < len(digests):
                    if case.get("fixture_sha256") != digests[index]:
                        problems.append(f"{where}: fixture digest differs from its fixture")
                if not case.get("response"):
                    problems.append(f"{where}: empty response")
                if case.get("fabricated_cites"):
                    problems.append(f"{where}: fabricated citation(s) {case['fabricated_cites']}")
                if case.get("citation_audit_ready") is not True:
                    problems.append(f"{where}: citation audit had no declared sources or was not recorded")
                if case.get("audit_unavailable") is not False:
                    problems.append(f"{where}: citation audit unavailable or not recorded")
                if case.get("needs_review") and (name, index) not in ruled:
                    problems.append(f"{where}: needs_review is not ruled on")
                unparsed += len(case.get("unparsed_citations") or [])
        for kind, counts in va.recount(adj, report if isinstance(report, dict) else {"suites": suites}).items():
            bucket = tally.setdefault(kind, Counter())
            bucket["graded"] += counts["graded"]
            bucket["adjudicated"] += counts["adjudicated"]
    for name in sorted(set(expected_types) - seen):
        problems.append(f"missing suite: {name}")
    for kind, threshold in MIN_PASS_RATES.items():
        bucket = tally.get(kind, Counter())
        if not bucket["graded"] or bucket["adjudicated"] / bucket["graded"] < threshold:
            problems.append(
                f"{kind}: {bucket['adjudicated']}/{bucket['graded']} adjudicated, "
                f"below the {threshold:.0%} release threshold"
            )
    return problems, tally, unparsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        pairs = [
            (
                json.loads((ROOT / pair["report"]).read_text(encoding="utf-8")),
                json.loads((ROOT / pair["adjudication"]).read_text(encoding="utf-8")),
            )
            for pair in manifest["pairs"]
        ]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"release manifest or a run it names is unreadable: {error}", file=sys.stderr)
        return 1
    problems, tally, unparsed = validate(
        pairs, fixture_types(), fixture_questions(), expected_digests=fixture_digests()
    )
    for problem in problems:
        print(f"ERROR: {problem}", file=sys.stderr)
    rates = ", ".join(
        f"{kind} {b['adjudicated']}/{b['graded']}" for kind, b in sorted(tally.items())
    )
    # Not a gate criterion — the roadmap's gate is fabricated citations — but a
    # number a reader of a green gate should see beside it.
    print(f"adjudicated: {rates}; unparsed citations: {unparsed}")
    if problems:
        return 1
    print("Release fidelity gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
