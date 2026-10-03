#!/usr/bin/env python3
"""Validate cross_critique field structure across master meta.json files.

Verifies:
  1. Each cross_critique entry has target_master, position, citation
  2. target_master is a real master (not self, not meta-skill, exists)
  3. citation is a real id in this master's own sources[].id
  4. position length in [10, 300]
  5. Coverage: 8 canonical debate pairs are covered bidirectionally
  6. No ranking words (不如 / 胜过 / 更究竟 …) or comparative constructs
     (「殊胜，然」「即是究竟」「恐落…之偏」): a position contrasts stances,
     it does not grade them (ETHICS.md §3 派系中立)
  7. A master who died before the target was born may only be set against
     him as a labelled 假设性对照 — he never critiqued a later teacher

Pure offline structural check.

Usage:
    python3 scripts/validate-cross-critique.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PREBUILT_DIR = Path(__file__).resolve().parent.parent / "prebuilt"

META_SKILL_SLUGS = {"curriculum", "debate", "compare-masters"}

REQUIRED_PAIRS = [
    ("huineng", "yinguang"),
    ("kumarajiva", "xuanzang"),
    ("huineng", "zhiyi"),
    ("tsongkhapa", "huineng"),
    ("ajahn-chah", "mahasi-sayadaw"),
    ("atisha", "huineng"),
    ("ouyi", "yinguang"),
    ("ouyi", "tsongkhapa"),
]

POSITION_MIN = 10
POSITION_MAX = 300

# master-ajahn-chah once said of Mahasi's noting 「不如观自然呼吸」 — a verdict,
# not a stance — while ETHICS.md §3 names Mahasi vs Forest as a pair the AI
# must not rank. Kept to grading words; 「殊胜」 alone describes, it does not rank.
RANKING_TERMS = ("不如", "胜过", "胜于", "胜读", "更究竟", "更殊胜", "更高明", "低劣", "劣于", "远胜")

# Comparative constructions that grade without a grading word: concede the
# other side is 殊胜 and then turn (「自然观察殊胜，然……」), declare one's own
# way 即是究竟, or warn the other 恐落……之偏. Scoped to the construction, so
# 究竟 as a doctrinal term (究竟即佛, 究竟位) is not caught.
COMPARATIVE_PATTERNS = (
    re.compile(r"(?:更|最|方为|即是|才是)究竟"),
    re.compile(r"非究竟"),
    re.compile(r"(?:更|最)殊胜"),
    re.compile(r"殊胜\s*[，,；;]\s*然"),
    re.compile(r"恐落[^，。；）)]{0,12}之偏"),
    re.compile(r"唯[^，。；]{1,12}方为"),
)

# master-huineng (d. 713) was given a critique of 应成 / 自续 and 辨了不了义,
# fourteenth-century Tsongkhapa topics. /master-debate still pairs masters
# across eras, so such an entry must say it is a hypothetical reconstruction.
HYPOTHETICAL_MARK = "假设性对照"
_YEAR = re.compile(r"\d{1,4}")
_CENTURY = re.compile(r"(\d{1,2})\s*世纪")


def life_span(era: object) -> tuple[int, int] | None:
    """(birth, death) from a meta.json `era` such as 638-713, 约150-250 or 5世纪."""
    if not isinstance(era, str):
        return None
    century = _CENTURY.search(era)
    if century:
        n = int(century.group(1))
        return (n - 1) * 100, n * 100
    years = [int(y) for y in _YEAR.findall(era)]
    if len(years) >= 2:
        return years[0], years[1]
    return None


def _load(meta_path: Path) -> dict:
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def collect_master_slugs(prebuilt: Path) -> set[str]:
    return {p.parent.name.removeprefix("master-")
            for p in prebuilt.glob("master-*/meta.json")}


def collect_sources_by_slug(prebuilt: Path) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for meta_path in prebuilt.glob("master-*/meta.json"):
        slug = meta_path.parent.name.removeprefix("master-")
        ids = set()
        for s in _load(meta_path).get("sources", []):
            sid = s.get("id")
            if sid:
                ids.add(sid)
        out[slug] = ids
    return out


def collect_critique_pairs(prebuilt: Path) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for meta_path in prebuilt.glob("master-*/meta.json"):
        src = meta_path.parent.name.removeprefix("master-")
        for e in _load(meta_path).get("cross_critique", []) or []:
            tgt = e.get("target_master")
            if isinstance(tgt, str):
                pairs.add((src, tgt))
    return pairs


def validate(prebuilt: Path, *, check_coverage: bool = True) -> list[str]:
    errors: list[str] = []
    known_slugs = collect_master_slugs(prebuilt)
    sources_by_slug = collect_sources_by_slug(prebuilt)
    spans = {
        meta_path.parent.name.removeprefix("master-"): life_span(_load(meta_path).get("era"))
        for meta_path in prebuilt.glob("master-*/meta.json")
    }

    for meta_path in sorted(prebuilt.glob("master-*/meta.json")):
        slug = meta_path.parent.name.removeprefix("master-")
        data = _load(meta_path)
        cc = data.get("cross_critique")
        if cc is None:
            continue
        if not isinstance(cc, list):
            errors.append(f"{slug}: cross_critique must be list, got {type(cc).__name__}")
            continue
        for i, entry in enumerate(cc):
            prefix = f"{slug}#{i}"
            if not isinstance(entry, dict):
                errors.append(f"{prefix}: entry must be object")
                continue
            for k in ("target_master", "position", "citation"):
                v = entry.get(k)
                if not v or not isinstance(v, str):
                    errors.append(f"{prefix}: missing or empty {k}")
            tm = entry.get("target_master") or ""
            if tm == slug:
                errors.append(f"{prefix}: cannot target self")
            elif tm in META_SKILL_SLUGS:
                errors.append(f"{prefix}: cannot target meta-skill '{tm}'")
            elif tm and tm not in known_slugs:
                errors.append(f"{prefix}: target_master '{tm}' not a known master")
            cit = entry.get("citation") or ""
            if cit and cit not in sources_by_slug.get(slug, set()):
                errors.append(f"{prefix}: citation '{cit}' not in {slug}'s sources[].id")
            pos = entry.get("position") or ""
            if pos and not (POSITION_MIN <= len(pos) <= POSITION_MAX):
                errors.append(f"{prefix}: position length {len(pos)} out of [{POSITION_MIN}, {POSITION_MAX}]")
            if isinstance(pos, str):
                ranked = [term for term in RANKING_TERMS if term in pos]
                ranked += [m.group(0) for rx in COMPARATIVE_PATTERNS for m in rx.finditer(pos)]
                if ranked:
                    errors.append(
                        f"{prefix}: position ranks rather than contrasts ({'、'.join(ranked)})"
                    )
                speaker, target = spans.get(slug), spans.get(tm)
                if (
                    speaker and target and speaker[1] < target[0]
                    and HYPOTHETICAL_MARK not in pos
                ):
                    errors.append(
                        f"{prefix}: {slug} died before {tm} was born — label the "
                        f"entry 「{HYPOTHETICAL_MARK}」 or drop it"
                    )

    if check_coverage:
        pairs = collect_critique_pairs(prebuilt)
        for a, b in REQUIRED_PAIRS:
            if (a, b) not in pairs:
                errors.append(f"missing critique: {a} → {b}")
            if (b, a) not in pairs:
                errors.append(f"missing critique: {b} → {a}")

    return errors


def main() -> int:
    errors = validate(PREBUILT_DIR)
    if errors:
        print(f"{len(errors)} cross_critique error(s):")
        for e in errors:
            print(f"  ERROR: {e}")
        return 1
    print("cross_critique OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
