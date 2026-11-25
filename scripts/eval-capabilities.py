#!/usr/bin/env python3
"""Live evaluation of the capability skills against eval/capabilities/*.jsonl.

    python3 scripts/eval-capabilities.py                 # both sets, writes eval/reports/capabilities-<commit>.json
    python3 scripts/eval-capabilities.py --only citation --out /tmp/x.json

Hits the real services (FoJin, SuttaCentral, CBETA, BDRC); costs nothing but
takes a few minutes because FoJin allows 12 requests a minute.

Acceptance (design doc 2026-11-25):
    found_precision        >= 0.98   items judged `found` whose expectation allows `found`
    fakes_judged_found     == 0      misattribution items judged `found` when their expectation forbids it
The report also lists every `candidate` for hand review, and the English
`unverifiable` share, because neither can be graded automatically.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "capabilities" / "buddhist-quote-trace" / "scripts"))

import bcite  # noqa: E402
import qtrace  # noqa: E402

EVAL = ROOT / "eval" / "capabilities"


def _rows(name: str) -> list[dict]:
    path = EVAL / f"{name}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _short(cid: str | None) -> str | None:
    if not cid:
        return None
    parsed = bcite.parse(cid)
    return parsed.get("work") or parsed.get("uid") or cid


def eval_trace(rows: list[dict]) -> dict:
    results: dict[str, dict] = {}
    zh = [r for r in rows if r["lang"] == "zh"]
    en = [r for r in rows if r["lang"] == "en"]
    if zh:
        out = qtrace.trace(sentences=[r["text"] for r in zh], lang="zh")
        for row, item in zip(zh, out["items"]):
            results[row["id"]] = item
    for row in en:
        results[row["id"]] = qtrace.trace(sentences=[row["text"]], lang="en")["items"][0]

    cases, by_cat = [], Counter()
    found_total = found_ok = fakes_found = 0
    for row in rows:
        item = results[row["id"]]
        got = item["verdict"]
        ok = got in row["expect"]
        ids = {_short(s.get("id")) for s in item.get("sources") or []}
        # Whether the expected work is among the (at most five) works returned. Reported,
        # not graded: the same words are often in several texts (MN 10 and DN 22, 坛经 and
        # 传灯录), and FoJin ranks by its own order.
        source_ok = _short(row["expect_source"]) in ids if row.get("expect_source") and got == "found" else None
        if got == "found":
            found_total += 1
            found_ok += int("found" in row["expect"])
        if row.get("category") == "misattribution" and got == "found" and "found" not in row["expect"]:
            fakes_found += 1
        by_cat[(row["lang"], row.get("category"), ok)] += 1
        cases.append({"id": row["id"], "lang": row["lang"], "category": row.get("category"), "text": row["text"],
                      "expect": row["expect"], "got": got, "ok": ok, "source_ok": source_ok,
                      "sources": [s.get("id") for s in item.get("sources") or []][:3], "note": item.get("note")})

    categories = {}
    for (lang, cat, ok), n in sorted(by_cat.items(), key=lambda kv: (kv[0][0], str(kv[0][1]), kv[0][2])):
        c = categories.setdefault(f"{lang}/{cat}", {"ok": 0, "total": 0})
        c["total"] += n
        c["ok"] += n if ok else 0
    en_cases = [c for c in cases if c["lang"] == "en"]
    return {
        "total": len(cases),
        "ok": sum(c["ok"] for c in cases),
        "found_precision": round(found_ok / found_total, 4) if found_total else None,
        "found_judged": found_total,
        "fakes_judged_found": fakes_found,
        "expected_source_returned": f"{sum(c['source_ok'] is True for c in cases)}/{sum(c['source_ok'] is not None for c in cases)}",
        "en_unverifiable_share": round(sum(c["got"] == "unverifiable" for c in en_cases) / len(en_cases), 4) if en_cases else None,
        "by_category": categories,
        "candidates_for_review": [c for c in cases if c["got"] == "candidate"],
        "misses": [c for c in cases if not c["ok"]],
        "cases": cases,
    }


def eval_citation(rows: list[dict]) -> dict:
    cases = []
    for row in rows:
        out = bcite.resolve(row["citation"], row.get("title"))
        checks = {"exists": out["exists"] == row.get("expect_exists")}
        if "expect_canonical" in row:
            checks["canonical"] = out["canonical"] == row["expect_canonical"]
        if "expect_title_matches" in row:
            checks["title_matches"] = out["title_matches"] == row["expect_title_matches"]
        cases.append({"id": row["id"], "citation": row["citation"], "title": row.get("title"),
                      "got": {k: out.get(k) for k in ("exists", "canonical", "title", "title_matches", "note")},
                      "checks": checks, "ok": all(checks.values())})
    return {"total": len(cases), "ok": sum(c["ok"] for c in cases),
            "misses": [c for c in cases if not c["ok"]], "cases": cases}


SMOKE_TRACE = [("一切有为法，如梦幻泡影。", "found"), ("我们要好好学习，天天向上。", "not_found"),
               ("For never is hatred laid to rest by hate.", "found")]
SMOKE_CITE = [("T48n2008", True), ("T9999", False), ("SN 22.59", True), ("Dhp 5", True), ("W1KG14334", False)]


def smoke() -> int:
    """Six live calls that must keep their answers; a changed API shows up here first."""
    problems = []
    for text, want in SMOKE_TRACE:
        got = qtrace.trace(sentences=[text], entries=[])["items"][0]
        if got["verdict"] != want:
            problems.append(f"trace {text!r}: got {got['verdict']} ({got.get('note')}), want {want}")
    for citation, want in SMOKE_CITE:
        got = bcite.resolve(citation)
        if got["exists"] is not want:
            problems.append(f"resolve {citation!r}: exists={got['exists']} ({got.get('note')}), want {want}")
    for p in problems:
        print("FAIL:", p)
    print("smoke:", "OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", choices=("quote-trace", "citation"))
    ap.add_argument("--out")
    ap.add_argument("--smoke", action="store_true", help="a few live calls with fixed answers; no report")
    args = ap.parse_args(argv)
    if args.smoke:
        return smoke()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    report = {"meta": {"commit": commit, "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                       "engines": [qtrace.ENGINE, bcite.ENGINE]}}
    if args.only in (None, "quote-trace"):
        report["quote_trace"] = eval_trace(_rows("quote-trace"))
    if args.only in (None, "citation"):
        report["citation"] = eval_citation(_rows("citation"))
    out = Path(args.out) if args.out else ROOT / "eval" / "reports" / f"capabilities-{commit}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    qt = report.get("quote_trace")
    if qt:
        print(f"quote-trace: {qt['ok']}/{qt['total']} as expected; found precision {qt['found_precision']} "
              f"({qt['found_judged']} judged found); expected work among sources {qt['expected_source_returned']}; fakes judged found {qt['fakes_judged_found']}; "
              f"English unverifiable {qt['en_unverifiable_share']}; candidates to review {len(qt['candidates_for_review'])}")
        for name, c in qt["by_category"].items():
            print(f"  {name}: {c['ok']}/{c['total']}")
    ct = report.get("citation")
    if ct:
        print(f"citation: {ct['ok']}/{ct['total']} as expected")
    print(f"report: {out}")
    gate = (not qt or ((qt["found_precision"] or 1) >= 0.98 and qt["fakes_judged_found"] == 0))
    return 0 if gate else 1


if __name__ == "__main__":
    sys.exit(main())
