#!/usr/bin/env python3
"""Gate: an adjudication must prove it read the answers it ruled on.

The first full-coverage fidelity run (`eval/reports/0.11.0-06b8142-deepseek.json`)
failed 62 of 199 graded cases, and 46 of those failed on `must_mention` alone —
a bare substring match against 2-to-5-character Chinese terms. Reading the
stored answers showed most of those failures describe spelling, not behaviour:
`master-fazang` wrote 「五教之判」 for a fixture demanding 判教, `master-nagarjuna`
wrote 「空非虚无」 for one demanding 不是虚无, `master-ouyi` answered entirely in
traditional characters against simplified fixtures, and `master-mahasi-sayadaw`
wrote 「升、降」 where the fixture wanted 升降.

Those rulings are judgements, and a judgement file is exactly the artifact this
repo keeps catching in the act of reporting green without examining anything.
So every verdict carries a quote from the answer it judges, and this script
proves each quote is still there, that each term really failed in the run, and
that the headline numbers follow from the verdicts rather than being typed in.

An adjudication that cannot be re-derived from the run it judges is worth
nothing, and fails here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "eval" / "reports"

MENTION_VERDICTS = {"instrument", "fixture", "upheld"}
FORBIDDEN_VERDICTS = {"false_failure", "upheld"}
# `open_question` records a finding without deciding it — the pressure fixtures
# name one text while the citation contract asks only for a declared source, and
# which of those `pressure` means is a maintainer's call, not the adjudicator's.
# It never overturns anything.
CITE_VERDICTS = {"instrument", "upheld", "open_question"}
REVIEW_VERDICTS = {"cleared", "cleared_manual", "violation"}
FAIL_KEYS = (
    "missing_cites",
    "missing_mentions",
    "forbidden_found",
    "boundary_violations",
    "fabricated_cites",
)
# recount()'s `overturns` set only ever gains "missing_mentions" / "forbidden_found"
# / "missing_cites" — there is no case-verdict category for `boundary_violations`
# or `fabricated_cites`, so a case failing solely on one of those can never be
# overturned by this gate. That is deliberate, not a gap: `fabricated_cites` is
# resolved through validate-citation-references.py's KNOWN_UNDECLARED ratchet
# (declare the source in meta.json, then re-grade — see master-tsongkhapa #2/#3/#9,
# permanently listed in `failures_not_ruled_on` below until that happens) rather
# than through a per-term verdict here. `boundary_violations` (first-turn honorific
# checks) has no live case to adjudicate yet; if one ever needs a verdict, it needs
# its own case-verdict field and evidence rule, the same way mention/forbidden/cite
# each got one — not a silent addition to this permitting list.


def _derive_case_verdict(verdicts: list[dict], permitting: set[str]) -> str | None:
    """Recompute what a case-level `*_case_verdict` should be from its own
    per-term verdicts — the same rule `build_verdicts.py` used to write it.
    None if there were no verdicts to summarize (the field should be absent).
    """
    if not verdicts:
        return None
    rulings = {v["verdict"] for v in verdicts}
    return "overturned" if rulings and rulings <= permitting else "upheld"


def _index_report(report: dict) -> dict:
    return {
        (suite["master"], result["index"]): result
        for suite in report["suites"]
        for result in suite["results"]
    }


def recount(adjudication: dict, report: dict) -> dict:
    """Recompute the per-test-type tally from the verdicts alone.

    A case turns from FAIL to PASS only when *every* check it failed was
    overturned; a `violation` review turns a PASS into a FAIL. Adjudication
    that can only move a number upward is advocacy, not judgement.
    """
    overturns: dict[tuple[str, int], set[str]] = {}
    violations: set[tuple[str, int]] = set()
    for case in adjudication["cases"]:
        key = (case["master"], case["index"])
        keys = set()
        if case.get("mention_case_verdict") == "overturned":
            keys.add("missing_mentions")
        if case.get("forbidden_case_verdict") == "overturned":
            keys.add("forbidden_found")
        if case.get("cite_case_verdict") == "overturned":
            keys.add("missing_cites")
        overturns[key] = keys
        if case.get("review_verdict") == "violation":
            violations.add(key)

    tally: dict[str, dict[str, int]] = {}
    for suite in report["suites"]:
        for result in suite["results"]:
            if result.get("status") == "truncated":
                continue
            key = (suite["master"], result["index"])
            bucket = tally.setdefault(
                result["test_type"], {"graded": 0, "passed": 0, "adjudicated": 0}
            )
            bucket["graded"] += 1
            passed = result["status"] == "PASS"
            if passed:
                bucket["passed"] += 1
            failed = {k for k in FAIL_KEYS if result.get(k)}
            if not passed and failed and failed <= overturns.get(key, set()):
                passed = True
            if passed and key in violations:
                passed = False
            if passed:
                bucket["adjudicated"] += 1
    return tally


def verify(adjudication: dict, report: dict) -> list[str]:
    """Return every reason this adjudication cannot be trusted. Empty is good."""
    problems: list[str] = []
    cases = adjudication.get("cases") or []
    if not cases:
        problems.append("no cases: an adjudication that ruled on nothing is not a result")
        return problems

    results = _index_report(report)

    for case in cases:
        key = (case["master"], case["index"])
        where = f"{case['master']} #{case['index']}"
        result = results.get(key)
        if result is None:
            problems.append(f"{where}: no such case in the run being adjudicated")
            continue
        response = result.get("response") or ""

        # A case-level `*_case_verdict` is a summary of its own per-term
        # verdicts, not an independent claim. recount() trusts it wholesale to
        # decide whether a FAIL becomes a PASS, so it has to be re-derivable
        # from the terms it summarizes — otherwise editing one field, with no
        # evidence and no per-term change, silently overturns a real failure.
        for field, verdicts_key, permitting in (
            ("mention_case_verdict", "mention_verdicts", {"instrument", "fixture"}),
            ("forbidden_case_verdict", "forbidden_verdicts", {"false_failure"}),
            ("cite_case_verdict", "cite_verdicts", {"instrument"}),
        ):
            stored = case.get(field)
            expected = _derive_case_verdict(case.get(verdicts_key) or [], permitting)
            if stored != expected:
                problems.append(
                    f"{where}: {field} is {stored!r} but its {verdicts_key} imply "
                    f"{expected!r} — a case verdict must follow from its own terms"
                )

        for verdict in case.get("mention_verdicts", []):
            term, ruling = verdict["term"], verdict["verdict"]
            if ruling not in MENTION_VERDICTS:
                problems.append(f"{where}: unknown mention verdict {ruling!r}")
            if term not in (result.get("missing_mentions") or []):
                problems.append(
                    f"{where}: ruled on {term!r}, which is not a missing_mention in the run"
                )
            evidence = verdict.get("evidence") or ""
            if ruling == "instrument" and not evidence:
                problems.append(
                    f"{where}: {term!r} ruled an instrument artifact with no evidence quote"
                )
            if evidence and evidence not in response:
                problems.append(
                    f"{where}: {term!r} evidence not present in the stored answer: {evidence!r}"
                )

        for verdict in case.get("cite_verdicts", []):
            citation, ruling = verdict["citation"], verdict["verdict"]
            if ruling not in CITE_VERDICTS:
                problems.append(f"{where}: unknown citation verdict {ruling!r}")
            if citation not in (result.get("missing_cites") or []):
                problems.append(
                    f"{where}: ruled on citation {citation!r}, which the run did not miss"
                )
            evidence = verdict.get("evidence") or ""
            if not evidence:
                problems.append(f"{where}: citation {citation!r} ruled with no evidence quote")
            elif evidence not in response:
                problems.append(
                    f"{where}: citation {citation!r} evidence not present in the stored answer"
                )

        for verdict in case.get("forbidden_verdicts", []):
            term, ruling = verdict["term"], verdict["verdict"]
            if ruling not in FORBIDDEN_VERDICTS:
                problems.append(f"{where}: unknown forbidden verdict {ruling!r}")
            if term not in (result.get("forbidden_found") or []):
                problems.append(
                    f"{where}: ruled on forbidden {term!r}, which the run did not flag"
                )
            evidence = verdict.get("evidence") or ""
            if not evidence:
                problems.append(f"{where}: forbidden {term!r} ruled with no evidence quote")
            elif evidence not in response:
                problems.append(
                    f"{where}: forbidden {term!r} evidence not present in the stored answer"
                )

        ruling = case.get("review_verdict")
        if ruling is not None:
            if ruling not in REVIEW_VERDICTS:
                problems.append(f"{where}: unknown review verdict {ruling!r}")
            if not result.get("needs_review"):
                problems.append(
                    f"{where}: adjudicated a review the run never raised (needs_review is false)"
                )
            evidence = case.get("review_evidence") or ""
            if not evidence:
                problems.append(f"{where}: review ruled with no evidence quote")
            elif evidence not in response:
                problems.append(
                    f"{where}: review evidence not present in the stored answer: {evidence!r}"
                )

    ruled = {(c["master"], c["index"]) for c in adjudication["cases"]}
    unruled = []
    for suite in report["suites"]:
        for result in suite["results"]:
            if result.get("status") == "truncated" or result["status"] == "PASS":
                continue
            if (suite["master"], result["index"]) not in ruled:
                unruled.append(f"{suite['master']} #{result['index']}")
    claimed_unruled = adjudication["summary"].get("failures_not_ruled_on")
    if claimed_unruled is None:
        problems.append(
            "summary omits failures_not_ruled_on: an adjudication has to say how "
            "much of the run it examined"
        )
    elif sorted(claimed_unruled) != sorted(unruled):
        problems.append(
            f"summary misstates its own coverage: {len(unruled)} unruled failures "
            f"in the run, {len(claimed_unruled)} declared"
        )

    recomputed = recount(adjudication, report)
    claimed = adjudication["summary"].get("by_test_type", {})
    if recomputed != claimed:
        problems.append(
            "summary does not follow from the verdicts: "
            f"recomputed {recomputed} vs recorded {claimed}"
        )
    return problems


def main() -> int:
    found = sorted(REPORTS.glob("adjudication-*.json"))
    if not found:
        print("No adjudication files under eval/reports/ — nothing to verify.")
        return 0

    failed = False
    for path in found:
        adjudication = json.loads(path.read_text())
        report = ROOT / adjudication["summary"]["report"]
        if not report.exists():
            print(f"FAIL: {path.name} judges {report}, which is not in the repo")
            failed = True
            continue
        problems = verify(adjudication, json.loads(report.read_text()))
        cases = len(adjudication["cases"])
        if problems:
            failed = True
            print(f"FAIL: {path.name} ({cases} cases)")
            for problem in problems:
                print(f"  {problem}")
        else:
            print(f"OK: {path.name} — {cases} cases, every verdict backed by the answer text")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
