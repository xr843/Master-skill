#!/usr/bin/env python3
"""Re-grade a committed run against the current judge and fixtures. Offline, free.

`check_response` is deterministic, and every answer has been stored since PR
#142. So any change to the judge or to the fixtures can be measured against an
already-paid-for run for nothing, instead of claimed.

That matters most for changes that *relax* something. Moving a requirement into
`must_convey` — "the substring matcher cannot decide this" — is honest when the
adjudication says so and is laundering when it does not. Re-grading the ¥3.89
sweep shows exactly which cases move and whether anything moved the wrong way.

    python3 scripts/regrade-report.py eval/reports/0.11.0-06b8142-deepseek.json

Results are joined to fixtures **by question text**, never by position: a
fixture added or removed shifts every index after it, and grading an answer
against someone else's question would produce a confident, meaningless number.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import importlib.util

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "_fidelity", ROOT / "scripts" / "test-fidelity.py"
)
_fidelity = importlib.util.module_from_spec(_spec)
sys.modules["_fidelity"] = _fidelity
_spec.loader.exec_module(_fidelity)

from verify_citations import load_declared_ids, load_member_aliases  # noqa: E402


def load_fixtures() -> dict[str, list[dict]]:
    fixtures: dict[str, list[dict]] = {}
    for path in sorted((ROOT / "prebuilt").glob("*/tests/fidelity.jsonl")):
        fixtures[path.parent.parent.name] = [
            json.loads(line) for line in path.read_text().splitlines() if line.strip()
        ]
    return fixtures


def regrade(report: dict, fixtures: dict[str, list[dict]]) -> dict:
    """Re-run the judge over every stored answer. Raises if the run stored none."""
    if not any(
        "response" in result
        for suite in report["suites"]
        for result in suite["results"]
    ):
        raise ValueError("no stored answers in this report — nothing to re-grade")

    cases: list[dict] = []
    graded_results: list[dict] = []
    by_test_type: dict[str, dict[str, int]] = {}

    for suite in report["suites"]:
        master = suite["master"]
        cases_for_master = fixtures.get(master, [])
        try:
            declared = load_declared_ids(master) or None
            aliases = load_member_aliases(master) or None
        except (FileNotFoundError, ValueError):
            declared = None
            aliases = None

        for result in suite["results"]:
            if result.get("status") in ("truncated", "api_error"):
                continue
            index = result["index"]
            fixture = cases_for_master[index] if index < len(cases_for_master) else None
            if fixture is None or fixture.get("q") != result["question"]:
                raise ValueError(
                    f"{master} #{index}: the fixture at this position does not match "
                    f"the question that was graded. Fixtures moved; re-grading by "
                    f"position would compare an answer with someone else's question."
                )
            check = _fidelity.check_response(
                result.get("response") or "",
                fixture,
                declared_ids=declared,
                member_aliases=aliases,
            )
            entry = _fidelity.result_entry(index, fixture, check, result.get("response") or "")
            graded_results.append(entry)
            was = result["status"]
            now = "PASS" if check["passed"] else "FAIL"
            bucket = by_test_type.setdefault(
                result["test_type"], {"graded": 0, "was": 0, "now": 0}
            )
            bucket["graded"] += 1
            bucket["was"] += was == "PASS"
            bucket["now"] += now == "PASS"
            cases.append(
                {
                    "master": master,
                    "index": index,
                    "test_type": result["test_type"],
                    "was": was,
                    "now": now,
                    "needs_review": check["needs_review"],
                }
            )

    return {
        "meta": report.get("meta", {}),
        "cases": cases,
        "by_test_type": by_test_type,
        "mentions": _fidelity.summarize_mentions(graded_results),
        "needs_review": sum(1 for c in cases if c["needs_review"]),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {Path(argv[0]).name} <eval/reports/*.json>")
        return 2
    path = Path(argv[1])
    out = regrade(json.loads(path.read_text()), load_fixtures())
    meta = out["meta"]
    print(f"{path.name} — commit {meta.get('commit_short')}, model {meta.get('model')}")
    print(f"\n{'test_type':12} {'graded':>7} {'as graded':>11} {'re-graded':>11}")
    total = {"graded": 0, "was": 0, "now": 0}
    for test_type, b in sorted(out["by_test_type"].items()):
        for key in total:
            total[key] += b[key]
        print(f"{test_type:12} {b['graded']:>7} "
              f"{b['was']:>6} {b['was']/b['graded']:>4.0%} "
              f"{b['now']:>6} {b['now']/b['graded']:>4.0%}")
    print(f"{'TOTAL':12} {total['graded']:>7} "
          f"{total['was']:>6} {total['was']/total['graded']:>4.0%} "
          f"{total['now']:>6} {total['now']/total['graded']:>4.0%}")

    m = out["mentions"]
    print(
        f"\nmention coverage {m['mentions_decided']}/{m['mention_requirements']} "
        f"= {m['mention_coverage']}  "
        f"({m['mentions_unverified']} undecidable, "
        f"{m['script_mismatches']} answers in the wrong script)"
    )
    print(f"cases needing adjudication: {out['needs_review']}")

    moved_wrong = [c for c in out["cases"] if c["was"] == "PASS" and c["now"] == "FAIL"]
    if moved_wrong:
        print(f"\nWARNING: {len(moved_wrong)} case(s) that passed now fail:")
        for c in moved_wrong:
            print(f"  {c['master']} #{c['index']} ({c['test_type']})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
