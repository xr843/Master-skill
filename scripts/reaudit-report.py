#!/usr/bin/env python3
"""Re-run the citation audit over a committed run's stored answers. Offline, free.

The fabrication audit is a mechanical string-resolution test — does a citation
resolve to a declared source — so every change to `verify_citations.py` changes
what an already-paid-for run would have seen. Coverage is otherwise frozen at run
time: `eval/reports/0.11.0-06b8142-deepseek.json` records `master-ajahn-chah` at
0 of 48 citations readable, and that number describes the auditor of 2026-08-31,
not the persona.

Since PR #142 every answer is stored, so the audit can simply be run again.
The ¥3.89 sweep is re-measurable for nothing, and a family added to the auditor
has to show what it bought instead of asserting it.

    python3 scripts/reaudit-report.py eval/reports/0.11.0-06b8142-deepseek.json

The report file itself is never rewritten: it is the record of what that run
measured with that instrument, and editing it would be rewriting the experiment.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_citations import audit_answer, load_declared_ids, load_member_aliases  # noqa: E402


def reaudit(report: dict) -> dict:
    """Re-audit every stored answer. Raises if the run stored none."""
    if not any(
        "response" in result
        for suite in report["suites"]
        for result in suite["results"]
    ):
        raise ValueError(
            "no stored answers in this report — nothing to re-audit. Runs before "
            "PR #142 kept only response_length."
        )

    suites = []
    totals = {
        "recorded": {"checked": 0, "unparsed": 0},
        "recomputed": {"checked": 0, "unparsed": 0},
    }
    for suite in report["suites"]:
        recorded_block = suite.get("audit") or {}
        recorded = {
            "checked": recorded_block.get("citations_checked", 0),
            "unparsed": recorded_block.get("citations_unparsed", 0),
        }
        totals["recorded"]["checked"] += recorded["checked"]
        totals["recorded"]["unparsed"] += recorded["unparsed"]

        try:
            declared = load_declared_ids(suite["master"])
            aliases = load_member_aliases(suite["master"])
        except (FileNotFoundError, ValueError):
            # No meta.json, so no declared set to audit against. Recorded as
            # unavailable rather than as a clean zero — the distinction this
            # repo lost once already.
            suites.append(
                {
                    "master": suite["master"],
                    "status": "unavailable",
                    "recorded": recorded,
                    "recomputed": None,
                    "fabricated": [],
                }
            )
            totals["recomputed"]["checked"] += recorded["checked"]
            totals["recomputed"]["unparsed"] += recorded["unparsed"]
            continue

        checked = unparsed = 0
        fabricated: list[str] = []
        for result in suite["results"]:
            if result.get("status") == "truncated":
                continue
            audit = audit_answer(declared, result.get("response") or "", aliases)
            checked += (
                len(audit["offline"]) + len(audit["live"]) + len(audit["fabricated"])
            )
            unparsed += len(audit["unparsed"])
            fabricated.extend(audit["fabricated"])
        recomputed = {"checked": checked, "unparsed": unparsed}
        totals["recomputed"]["checked"] += checked
        totals["recomputed"]["unparsed"] += unparsed
        suites.append(
            {
                "master": suite["master"],
                "status": "audited",
                "recorded": recorded,
                "recomputed": recomputed,
                "fabricated": sorted(set(fabricated)),
            }
        )
    return {"meta": report.get("meta", {}), "suites": suites, "totals": totals}


def _coverage(counts: dict | None) -> str:
    if not counts:
        return "n/a"
    total = counts["checked"] + counts["unparsed"]
    if not total:
        return "n/a"
    return f"{counts['checked']}/{total} {counts['checked'] / total:.0%}"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[0])
        print(f"usage: {Path(argv[0]).name} <eval/reports/*.json>")
        return 2
    path = Path(argv[1])
    report = json.loads(path.read_text())
    out = reaudit(report)

    meta = out["meta"]
    print(f"{path.name} — commit {meta.get('commit_short')}, model {meta.get('model')}")
    print(f"\n{'skill':26} {'as recorded':>13}  {'re-audited':>13}   fabricated")
    for suite in out["suites"]:
        if suite["status"] == "unavailable":
            print(f"{suite['master']:26} {_coverage(suite['recorded']):>13}  "
                  f"{'(no meta.json)':>13}")
            continue
        moved = "  <--" if suite["recorded"] != suite["recomputed"] else ""
        print(
            f"{suite['master']:26} {_coverage(suite['recorded']):>13}  "
            f"{_coverage(suite['recomputed']):>13}   "
            f"{', '.join(suite['fabricated'])}{moved}"
        )
    print(
        f"\ntotal coverage  {_coverage(out['totals']['recorded'])}"
        f"  ->  {_coverage(out['totals']['recomputed'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
