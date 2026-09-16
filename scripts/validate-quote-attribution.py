#!/usr/bin/env python3
"""Gate: every line a persona presents as a quotation must name where it is from.

Steps 3h and 3i of the weekly check ask whether a quoted line exists — in CBETA,
or in the compiled teachings CBETA does not hold. Neither asks whether the reader
is told *which book* it came from, and that gap is where a misattribution
survives both: master-nagarjuna's 「宁起我见积若须弥」 is real text, findable in
CBETA, and not his — it is in 《大宝积经》. "Found in the canon" and "correctly
attributed" are different questions, and only the first was being asked.

This one is offline, so it runs on every PR instead of once a week.

Attribution counts when the source is named:

  - on the quoted line itself — 《书名》, 【…】, `Toh 3861`, `SC: SN 22.59`, 卷N;
  - on a `> 出处：…` line a few lines below (the excerpt files put it there);
  - on a sibling item of the same numbered list (one 出处 covers the block, which
    is how master-fazang's and master-kumarajiva's voice samples are written);
  - in the nearest section heading above (master-ajahn-chah's sutta excerpts name
    the sutta in the `###` heading).

It reuses `tools/verify_sources.collect_persona_quotes`, so the set it checks is
exactly the set 3h and 3i judge — if the collector learns a new quotation shape,
this gate covers it the same day.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

try:
    from verify_sources import PREBUILT_DIR, collect_persona_quotes
except ImportError as exc:  # pragma: no cover - the gate must not pass silently
    print(f"FAIL: cannot import the quote collector from tools/ ({exc}).")
    print("A gate that cannot load what it checks has not checked anything.")
    sys.exit(1)

# 什么算「写明了出处」。SC:/Toh/PTS 是南传与藏传的写法，卷N 与《…》是汉传的。
_SOURCE_NAMED = re.compile(
    r"《[^》]{1,40}》|【|Toh[:\s]\d|SC[:：]|\b[SMAD]N \d|Vism|PTS|卷[一二三四五六七八九十百千\d]|[Ss]utta"
)
_NUMBERED_ITEM = re.compile(r"^\s*\d+\.\s")
_LOOK = 8


def attribution(lines: list[str], number: int) -> str | None:
    """这条引文的出处写在哪儿；哪儿都没写就返回 None。"""
    i = number - 1
    if i < 0 or i >= len(lines):
        return None
    if _SOURCE_NAMED.search(lines[i]):
        return "on the line"

    # 摘录文件把「出处」写在引文下方几行。
    for j in range(i + 1, min(len(lines), i + 1 + _LOOK)):
        if "出处" in lines[j]:
            return f"出处 line {j - i} below" if _SOURCE_NAMED.search(lines[j]) else None

    # 编号示例句：整块共用一个出处，挂在其中一条上。
    if _NUMBERED_ITEM.match(lines[i]):
        low = i
        while low - 1 >= 0 and _NUMBERED_ITEM.match(lines[low - 1]):
            low -= 1
        high = i
        while high + 1 < len(lines) and _NUMBERED_ITEM.match(lines[high + 1]):
            high += 1
        for j in range(low, high + 1):
            if j != i and _SOURCE_NAMED.search(lines[j]):
                return f"sibling list item {j + 1 - low}"

    # 最近的小节标题。
    for j in range(i - 1, max(-1, i - 1 - _LOOK), -1):
        if lines[j].startswith("#"):
            return f"heading {i - j} above" if _SOURCE_NAMED.search(lines[j]) else None
    return None


def unattributed(quotes: list[tuple[str, str, str]], read) -> list[tuple[str, str]]:
    """[(位置, 引文)]：读者无从知道出自哪部书的引文。"""
    cache: dict[str, list[str]] = {}
    missing: list[tuple[str, str]] = []
    for where, _master, quote in quotes:
        rel, _, number = where.rpartition(":")
        if not number.isdigit():
            continue  # meta.json 的 lore_triggers 之类，不是文档行
        if rel not in cache:
            cache[rel] = read(rel)
        if attribution(cache[rel], int(number)) is None:
            missing.append((where, quote))
    return missing


def main() -> int:
    def read(rel: str) -> list[str]:
        return Path(PREBUILT_DIR, rel).read_text(encoding="utf-8").splitlines()

    quotes = collect_persona_quotes()
    if not quotes:
        print("FAIL: the quote collector returned nothing — this gate examined an empty set.")
        return 1

    missing = unattributed(quotes, read)
    if missing:
        print(f"FAIL: {len(missing)} quoted line(s) name no source:")
        for where, quote in missing:
            print(f"  {where}\n      「{quote[:56]}」")
        print(
            "\nA reader cannot check a quotation whose book is never named, and a line\n"
            "that happens to exist somewhere in the canon passes the weekly checks while\n"
            "still being the wrong master's words. Name the work on the line, in the\n"
            "`> 出处：` line below it, on a sibling numbered item, or in the heading above."
        )
        return 1

    print(f"OK: all {len(quotes)} quoted lines name the work they come from.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
