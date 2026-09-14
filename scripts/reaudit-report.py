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
    python3 scripts/reaudit-report.py eval/reports/0.11.0-06b8142-deepseek.json --online

`--online` also asks FoJin about the run's live citations, the ones that passed
offline on a link alone: does each link open, and is it the work the citation
names (same sutra number, agreeing title)? It needs the network and reads
nothing back into the report.

The report file itself is never rewritten: it is the record of what that run
measured with that instrument, and editing it would be rewriting the experiment.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_citations import (  # noqa: E402
    audit_answer,
    load_declared_ids,
    load_member_aliases,
    load_title_aliases,
    verify_online,
)


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
            titles = load_title_aliases(suite["master"])
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
        live: list[dict] = []
        fabricated: list[str] = []
        noncitation: list[str] = []
        for result in suite["results"]:
            if result.get("status") in ("truncated", "api_error"):
                continue
            audit = audit_answer(
                declared, result.get("response") or "", aliases, titles
            )
            checked += (
                len(audit["offline"]) + len(audit["live"]) + len(audit["fabricated"])
            )
            unparsed += len(audit["unparsed"])
            live.extend(audit["live_detail"])
            fabricated.extend(audit["fabricated"])
            noncitation.extend(audit.get("noncitation", ()))
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
                # Passed on a FoJin link alone; only `--online` checks the link.
                "live": live,
                # 判定为「不是引文」的【…】块。不计入覆盖率的分母,但必须
                # 数出来:排除而不申报,和静默跳过没有区别。
                "noncitation": sorted(set(noncitation)),
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


def _print_online(out: dict) -> None:
    """Ask FoJin whether each stored live citation's link is the work it names."""
    cited = [(s["master"], c) for s in out["suites"] for c in s.get("live", ())]
    if not cited:
        print("\nlive 引文在线核验：这次运行没有 live 引文")
        return
    tids = [c["text_id"] for _, c in cited]
    res = verify_online(tids, citations=[c for _, c in cited])
    print(f"\nlive 引文在线核验：{len(cited)} 条，{len(set(tids))} 个 FoJin 链接")
    if res.unreachable:
        print(f"  ⚠ 未能核验：FoJin 不可达（{res.unreachable}）")
        return
    groups: dict[tuple[str, str], int] = {}
    for master, citation in cited:
        key = (master, citation["text_id"])
        groups[key] = groups.get(key, 0) + 1
    for (master, tid), count in sorted(groups.items()):
        verdict = res.verdicts.get(tid)
        if verdict is True:
            continue
        mark = "✗" if verdict is False else "?"
        print(f"  {mark} {master} ×{count}  {res.reasons.get(tid, '未能核验')}")
    passed = sum(count for (_, tid), count in groups.items() if res.verdicts.get(tid) is True)
    print(f"  ✓ {passed} 条的链接是所引之书")


def main(argv: list[str]) -> int:
    args = argv[1:]
    online = "--online" in args
    paths = [arg for arg in args if arg != "--online"]
    if len(paths) != 1:
        print(__doc__.strip().splitlines()[0])
        print(f"usage: {Path(argv[0]).name} <eval/reports/*.json> [--online]")
        return 2
    path = Path(paths[0])
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
    skipped = sorted({b for s in out["suites"] for b in s.get("noncitation", ())})
    if skipped:
        print(
            f"\n{len(skipped)} 个【…】块判定为非引文，不计入上面的分母"
            "（人格拿它当小标题或复述问题）："
        )
        for block in skipped:
            print(f"    【{block}】")
    if online:
        _print_online(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
