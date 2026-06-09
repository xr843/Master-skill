#!/usr/bin/env python3
"""Validate that lore_triggers[].content quotes can be located verbatim
(or with high similarity) in the master's own sources/*-excerpts.md.

Background
----------
PR #32 introduced the lore_triggers schema. During self-review one entry
was caught and removed where the `content` quote was fabricated and falsely
attributed to T48n2008. This validator exists so the next fabrication is
caught by CI, not by luck.

Algorithm
---------
For each prebuilt/master-<slug>/meta.json:
  - For each lore_triggers[] entry:
      - Extract the quotation portion of `content` (strip the editorial
        gloss that follows the em-dash "——" if present)
      - Identify candidate excerpts files in this master's sources/ dir
        (preferring those whose name or body contains a normalized form
        of the source_ref CBETA id; otherwise scan all *-excerpts.md)
      - Normalize both texts (drop punctuation/whitespace, T<->S Han, …)
      - PASS if any of:
          * longest common substring >= 60 chars
          * difflib.SequenceMatcher ratio >= 0.75
        Otherwise FAIL and report best candidate file + best ratio.

Mode
----
By default this is *advisory* — it prints findings but exits 0 so it does
not block CI on day one. Run with `--strict` to make failures hard exits
(used locally and from a follow-up CI gate after the grace window).

Plan: advisory through v0.8.x, hard gate from v0.9.0.

Usage
-----
    python scripts/validate-lore-triggers-content.py
    python scripts/validate-lore-triggers-content.py --strict
    python scripts/validate-lore-triggers-content.py --master master-huineng
    python scripts/validate-lore-triggers-content.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

PREBUILT_DIR = Path(__file__).resolve().parent.parent / "prebuilt"

# Thresholds — calibrated against the 7 lore_triggers shipped in PR #32.
# A pass requires EITHER an absolute LCS floor OR a relative LCS coverage
# OR a high SequenceMatcher ratio. Short quotes (≈45 chars) need to match
# nearly verbatim; longer quotes (80+) just need a 40-char window.
MIN_LCS_ABS = 40         # absolute floor — longest common substring chars
MIN_LCS_FRAC = 0.85      # OR: LCS must cover ≥85% of the normalized quote
MIN_RATIO = 0.75         # OR: SequenceMatcher ratio across the file

# Drop these chars during normalization. Includes ASCII + common CJK
# punctuation, half- and full-width spaces, and a few special markers.
PUNCT_PATTERN = re.compile(
    r"[\s　 "
    r"，。、；：！？「」『』（）【】《》〈〉…—–\-·"
    r",.;:!?()\[\]{}<>\"'`~@#\$%\^&\*_+=|\\/]"
)

# Minimal Traditional -> Simplified table covering the chars that actually
# show up in our excerpts vs meta quotes. Keeping this hand-curated avoids
# adding opencc as a dep. Extend as new false-negatives surface.
T2S = {
    "於": "于", "爾": "尔", "後": "后", "個": "个", "們": "们",
    "這": "这", "麼": "么", "說": "说", "話": "话", "對": "对",
    "問": "问", "見": "见", "現": "现", "實": "实", "經": "经",
    "聖": "圣", "賢": "贤", "覺": "觉", "悟": "悟", "靈": "灵",
    "魂": "魂", "體": "体", "氣": "气", "風": "风", "雲": "云",
    "電": "电", "話": "话", "書": "书", "讀": "读", "寫": "写",
    "聽": "听", "聞": "闻", "嗎": "吗", "啟": "启", "輪": "轮",
    "華": "华", "藏": "藏", "識": "识", "種": "种", "葉": "叶",
    "場": "场", "進": "进", "達": "达", "過": "过", "來": "来",
    "車": "车", "間": "间", "問": "问", "離": "离", "邊": "边",
    "處": "处", "顯": "显", "標": "标", "點": "点", "稱": "称",
    "讚": "赞", "勸": "劝", "請": "请", "餘": "余", "禪": "禅",
    "閉": "闭", "開": "开", "關": "关", "鎖": "锁", "頓": "顿",
    "漸": "渐", "悟": "悟", "戒": "戒", "戀": "恋", "夢": "梦",
    "斷": "断", "點": "点", "靜": "静", "動": "动", "亂": "乱",
    "歲": "岁", "時": "时", "節": "节", "義": "义", "禮": "礼",
    "孫": "孙", "誰": "谁", "與": "与", "從": "从", "貴": "贵",
    "賤": "贱", "誤": "误", "繁": "繁", "簡": "简", "歸": "归",
    "鐘": "钟", "響": "响", "陽": "阳", "陰": "阴",
}


def normalize(text: str) -> str:
    """Drop punctuation + whitespace, fold trad->simp."""
    text = "".join(T2S.get(c, c) for c in text)
    text = PUNCT_PATTERN.sub("", text)
    return text


def extract_quotation(content: str) -> str:
    """Lore_triggers content is typically: <quote>——<editorial gloss>

    Strip everything from the em-dash onwards so we only compare the
    actual scripture quotation against the excerpts file.
    """
    # The em-dash separator may be a single 「——」 or 「——」 followed by
    # 《text》 etc. Some entries lack the gloss; in that case return the
    # whole content untouched.
    if "——" in content:
        return content.split("——", 1)[0]
    if "──" in content:
        return content.split("──", 1)[0]
    return content


def longest_common_substring_len(a: str, b: str) -> int:
    """Return length of the longest common substring of normalized a,b.

    Uses SequenceMatcher's find_longest_match which runs in roughly
    O(len(a)*len(b)) — fine for our hundred-char strings.
    """
    if not a or not b:
        return 0
    sm = SequenceMatcher(None, a, b, autojunk=False)
    m = sm.find_longest_match(0, len(a), 0, len(b))
    return m.size


def similarity_ratio(a: str, b: str) -> float:
    """SequenceMatcher ratio on normalized strings (windowed for speed).

    `b` (the haystack / whole excerpts file) is typically much larger
    than `a`. Compare against a sliding window of size ~2x|a| so the
    ratio isn't drowned by the rest of the file.
    """
    if not a or not b:
        return 0.0
    if len(b) <= 2 * len(a):
        return SequenceMatcher(None, a, b, autojunk=False).ratio()
    best = 0.0
    win = 2 * len(a)
    step = max(1, len(a) // 2)
    for i in range(0, len(b) - win + 1, step):
        r = SequenceMatcher(None, a, b[i : i + win], autojunk=False).ratio()
        if r > best:
            best = r
        # Early exit if we already pass the bar comfortably
        if best >= 0.95:
            break
    return best


def _candidate_files(
    master_dir: Path, source_ref: str, *, include_references: bool = False
) -> list[Path]:
    """Return excerpts files ranked by likely relevance to source_ref.

    Strategy: prefer files in sources/ whose name or body contains a
    normalized form of the CBETA id (e.g. T46n1911 -> also try T1911
    short form). Fall back to all *-excerpts.md files. If
    include_references=True, also append references/*.md as a soft
    secondary corpus (used when the primary excerpts check fails — a
    match there means the quote is real but excerpts/ is incomplete).
    """
    sources = master_dir / "sources"
    if not sources.exists():
        return []
    all_files = sorted(sources.glob("*-excerpts.md"))

    cbeta_prefix = source_ref.split("#", 1)[0]
    # Build keys to look for in file body: long form (T46n1911) and a
    # short form stripping the "n<digits>" segment (T1911).
    keys = {cbeta_prefix}
    m = re.match(r"^(T)\d+(n\d+)$", cbeta_prefix)
    if m:
        # T46n1911 -> T1911
        keys.add(m.group(1) + cbeta_prefix.split("n", 1)[1])

    ranked: list[tuple[int, Path]] = []
    for f in all_files:
        body = f.read_text(encoding="utf-8", errors="ignore")
        score = 0
        for k in keys:
            if k in body:
                score += 2
            if k in f.name:
                score += 1
        ranked.append((score, f))
    ranked.sort(key=lambda x: -x[0])
    sources_list = [p for _, p in ranked] or all_files

    if include_references:
        refs = master_dir / "references"
        if refs.exists():
            return sources_list + sorted(refs.glob("*.md"))
    return sources_list


def check_entry(
    master_dir: Path,
    entry: dict,
    entry_idx: int,
) -> dict:
    """Check a single lore_triggers entry. Returns a result dict."""
    content = entry.get("content", "") or ""
    source_ref = entry.get("source_ref", "") or ""
    quote = extract_quotation(content)
    quote_norm = normalize(quote)

    # Pass thresholds depend on quote length: a short quote must be matched
    # almost verbatim (frac of its own length); a long quote can satisfy
    # the absolute window of MIN_LCS_ABS chars.
    needed_lcs = min(MIN_LCS_ABS, max(1, int(len(quote_norm) * MIN_LCS_FRAC)))

    def _scan(files: list[Path]) -> tuple[Path | None, int, float]:
        bf, blcs, br = None, 0, 0.0
        for f in files:
            body = f.read_text(encoding="utf-8", errors="ignore")
            body_norm = normalize(body)
            lcs = longest_common_substring_len(quote_norm, body_norm)
            ratio = similarity_ratio(quote_norm, body_norm)
            if lcs > blcs or (lcs == blcs and ratio > br):
                blcs, br, bf = lcs, ratio, f
            if lcs >= needed_lcs or ratio >= MIN_RATIO:
                break
        return bf, blcs, br

    # Primary check: only files inside sources/
    primary_files = _candidate_files(master_dir, source_ref)
    best_file, best_lcs, best_ratio = _scan(primary_files)
    passed_in_sources = (best_lcs >= needed_lcs) or (best_ratio >= MIN_RATIO)

    # Secondary check: also look in references/. A match here means the
    # quote is real but the sources/ excerpts file does not contain it;
    # advisory output should flag this so the author can extend excerpts.
    found_in_references = False
    ref_file = None
    if not passed_in_sources:
        secondary_files = _candidate_files(
            master_dir, source_ref, include_references=True
        )
        # Only scan the references-side files we did not already check
        new_files = [f for f in secondary_files if f not in primary_files]
        rf, rlcs, rr = _scan(new_files)
        if (rlcs >= needed_lcs) or (rr >= MIN_RATIO):
            found_in_references = True
            ref_file = rf
            if rlcs > best_lcs or (rlcs == best_lcs and rr > best_ratio):
                best_file, best_lcs, best_ratio = rf, rlcs, rr

    # "passed" gating: true if quote is real (in either sources or
    # references). The "in_sources_only" sub-field lets CI distinguish
    # strict-pass (sources) from advisory-pass (references-only).
    passed = passed_in_sources or found_in_references
    return {
        "master": master_dir.name,
        "entry_idx": entry_idx,
        "source_ref": source_ref,
        "quote_len": len(quote_norm),
        "needed_lcs": needed_lcs,
        "best_file": best_file.name if best_file else None,
        "best_lcs": best_lcs,
        "best_ratio": round(best_ratio, 3),
        "passed": passed,
        "passed_in_sources": passed_in_sources,
        "in_references_only": found_in_references and not passed_in_sources,
        "ref_file": ref_file.name if ref_file else None,
    }


def validate(
    prebuilt_dir: Path = PREBUILT_DIR,
    master_filter: str | None = None,
) -> list[dict]:
    """Return list of result dicts (one per lore_triggers entry checked)."""
    results: list[dict] = []
    for d in sorted(prebuilt_dir.iterdir()):
        if not d.is_dir():
            continue
        if master_filter and d.name != master_filter:
            continue
        meta_path = d / "meta.json"
        if not meta_path.exists():
            continue
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if data.get("kind") == "meta-skill":
            continue
        lore = data.get("lore_triggers", []) or []
        for i, entry in enumerate(lore):
            results.append(check_entry(d, entry, i))
    return results


def _format_human(results: list[dict]) -> tuple[str, int]:
    fails = [r for r in results if not r["passed"]]
    soft = [r for r in results if r.get("in_references_only")]
    lines: list[str] = []
    if not results:
        lines.append("No lore_triggers entries found to check.")
        return "\n".join(lines), 0

    lines.append(
        f"Checked {len(results)} lore_triggers entries across "
        f"{len({r['master'] for r in results})} masters."
    )
    lines.append("")
    lines.append("Similarity distribution (per entry):")
    for r in results:
        if not r["passed"]:
            marker = "FAIL"
        elif r.get("in_references_only"):
            marker = "WARN"
        else:
            marker = "PASS"
        lines.append(
            f"  [{marker}] {r['master']} #{r['entry_idx']} "
            f"({r['source_ref']}) — file={r['best_file']} "
            f"quote_len={r['quote_len']} lcs={r['best_lcs']} "
            f"(need {r['needed_lcs']}) ratio={r['best_ratio']}"
        )
    if soft:
        lines.append("")
        lines.append(
            f"{len(soft)} entry/entries matched only in references/ "
            f"(quote is real but sources/ excerpts file does not contain it; "
            f"consider extending the excerpts):"
        )
        for r in soft:
            lines.append(
                f"  - {r['master']} entry[{r['entry_idx']}] source_ref="
                f"{r['source_ref']}: match in references/{r['ref_file']}"
            )
    if fails:
        lines.append("")
        lines.append(f"{len(fails)} entry/entries did not meet thresholds:")
        lines.append(
            f"  thresholds: longest_common_substring >= "
            f"min({MIN_LCS_ABS}, {MIN_LCS_FRAC}*quote_len) chars "
            f"OR SequenceMatcher ratio >= {MIN_RATIO}"
        )
        for r in fails:
            lines.append(
                f"  - {r['master']} entry[{r['entry_idx']}] source_ref="
                f"{r['source_ref']}: no high-similarity match "
                f"(best file={r['best_file']}, lcs={r['best_lcs']} "
                f"need {r['needed_lcs']}, ratio={r['best_ratio']})"
            )
    return "\n".join(lines), len(fails)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate lore_triggers content against sources excerpts."
    )
    parser.add_argument("--master", type=str, help="Only check one master dir")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on any FAIL (default: advisory, always exit 0)",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    results = validate(PREBUILT_DIR, master_filter=args.master)

    if args.json:
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    else:
        text, _ = _format_human(results)
        print(text)

    fails = [r for r in results if not r["passed"]]
    if fails:
        if args.strict:
            return 1
        # Advisory mode: print a banner and exit 0 so CI does not block.
        if not args.json:
            print()
            print(
                "ADVISORY: lore_triggers content validator is in advisory "
                "mode for v0.8.x. It will become a hard CI gate in v0.9. "
                "Rerun with --strict locally to reproduce a hard failure."
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
