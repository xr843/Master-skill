#!/usr/bin/env python3
"""Validate cross_critique field structure across master meta.json files.

Verifies:
  1. Each cross_critique entry has target_master, position, citation
  2. target_master is a real master (not self, not meta-skill, exists)
  3. citation is a real id in this master's own sources[].id
  4. position length in [10, 300]
  5. Coverage: 8 canonical debate pairs are covered bidirectionally

Pure offline structural check.

Usage:
    python3 scripts/validate-cross-critique.py
"""
from __future__ import annotations

import json
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
