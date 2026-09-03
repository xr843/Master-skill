#!/usr/bin/env python3
"""Gate: a requirement may only be declared undecidable with evidence behind it.

`must_convey` is how a fixture says "the substring matcher cannot decide this" —
the honest answer for 方便 when the answer says 「应病与药」, or for 不是虚无 when
it says 「空非虚无」. It is also the easiest possible way to launder a failure:
move the inconvenient requirement there and the build goes green while looking
more rigorous than before.

So a term may sit in `must_convey` only if a committed adjudication under
`eval/reports/` ruled it an instrument artifact, on a quote that
`verify-adjudication.py` proved is still in the answer it judges. A term the
adjudication ruled `upheld` — a real failure — can never be moved there.

Same ratchet as `KNOWN_UNDECLARED` in validate-citation-references.py: an entry
records a decision that was made and shown, not a permission anyone can take.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREBUILT = ROOT / "prebuilt"
REPORTS = ROOT / "eval" / "reports"

# Verdicts that license moving a requirement out of hard grading.
PERMITTING = {"instrument", "fixture"}


def load_fixtures() -> dict[str, list[dict]]:
    fixtures: dict[str, list[dict]] = {}
    for path in sorted(PREBUILT.glob("*/tests/fidelity.jsonl")):
        master = path.parent.parent.name
        fixtures[master] = [
            json.loads(line) for line in path.read_text().splitlines() if line.strip()
        ]
    return fixtures


def load_adjudications() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(REPORTS.glob("adjudication-*.json"))]


def _permitted(adjudications: list[dict]) -> set[tuple[str, str]]:
    """(master, term) pairs an adjudication ruled an instrument artifact."""
    allowed: set[tuple[str, str]] = set()
    for adjudication in adjudications:
        for case in adjudication.get("cases", []):
            for verdict in case.get("mention_verdicts", []):
                if verdict.get("verdict") in PERMITTING:
                    allowed.add((case["master"], verdict["term"]))
    return allowed


def verify(fixtures: dict[str, list[dict]], adjudications: list[dict]) -> list[str]:
    """Return every reason a fixture declares more than the evidence supports."""
    problems: list[str] = []
    allowed = _permitted(adjudications)

    declares_any = any(
        case.get("must_convey") for cases in fixtures.values() for case in cases
    )
    if declares_any and not adjudications:
        problems.append(
            "no adjudication under eval/reports/ — must_convey entries exist but "
            "there is nothing to check them against"
        )
        return problems

    for master, cases in fixtures.items():
        for index, case in enumerate(cases):
            convey = case.get("must_convey") or []
            mention = set(case.get("must_mention") or [])
            for term in convey:
                where = f"{master} #{index}"
                if term in mention:
                    problems.append(
                        f"{where}: {term!r} is in both must_mention and must_convey — "
                        "a requirement is either graded or undecidable, not both"
                    )
                if (master, term) not in allowed:
                    problems.append(
                        f"{where}: {term!r} is declared undecidable but no adjudication "
                        f"ruled it an instrument artifact for {master}. Grade it, or "
                        "adjudicate a real run and show the evidence."
                    )
    return problems


def main() -> int:
    fixtures = load_fixtures()
    adjudications = load_adjudications()
    problems = verify(fixtures, adjudications)
    convey = sum(
        len(case.get("must_convey") or [])
        for cases in fixtures.values()
        for case in cases
    )
    graded = sum(
        len(case.get("must_mention") or [])
        for cases in fixtures.values()
        for case in cases
    )
    if problems:
        print(f"FAIL: {len(problems)} fixture term(s) declare more than the evidence supports:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(
        f"OK: {graded} graded mention requirements, {convey} declared undecidable, "
        f"every one of the latter backed by an adjudicated verdict."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
