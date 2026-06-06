#!/usr/bin/env python3
"""Cross-check master-curriculum references against real master metadata.

Verifies:
  1. Every CBETA T/X number, Toh number, and compiled-teaching id mentioned
     in prebuilt/master-curriculum/references/*.md appears in the union of
     all prebuilt/master-*/meta.json `sources[].id`.
  2. Every /master-<slug> reference points to an existing prebuilt/master-<slug>/
     directory (self-references to /master-curriculum, /master-debate,
     /compare-masters are ignored).

Pure offline structural check — no API calls.

Usage:
    python scripts/validate-curriculum-sources.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PREBUILT_DIR = Path(__file__).resolve().parent.parent / "prebuilt"

# Citation patterns
_T_NUM = re.compile(r"T\d+n\d+[A-Za-z]?")
_X_NUM = re.compile(r"X\d+n\d+[A-Za-z]?")
_TOH = re.compile(r"Toh\s+\d+[A-Za-z\-]*")
# Compiled teaching: prefix:Title (e.g. AjahnChah:FoodForTheHeart, Mahasi:Manual)
_COMPILED = re.compile(r"\b[A-Z][A-Za-z]+:[A-Za-z][A-Za-z0-9]+\b")
# Master slug (kebab-case)
_SLUG = re.compile(r"/master-([a-z][a-z0-9\-]*)")

# Skills that look like /master-<slug> but are meta-skills, not masters
META_SKILL_SLUGS = {"curriculum", "debate"}


def extract_citations(text: str) -> set[str]:
    out: set[str] = set()
    out.update(_T_NUM.findall(text))
    out.update(_X_NUM.findall(text))
    out.update(_TOH.findall(text))
    out.update(_COMPILED.findall(text))
    return out


def extract_master_slugs(text: str) -> set[str]:
    return {m for m in _SLUG.findall(text) if m not in META_SKILL_SLUGS}


def collect_known_citations(prebuilt: Path) -> set[str]:
    """Union of all `sources[].id` across every prebuilt/master-*/meta.json."""
    known: set[str] = set()
    for meta_path in prebuilt.glob("master-*/meta.json"):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for src in data.get("sources", []):
            sid = src.get("id")
            if sid:
                known.add(sid)
    return known


def collect_known_slugs(prebuilt: Path) -> set[str]:
    """All real master slugs (prebuilt/master-<slug>/ that have meta.json)."""
    return {
        p.parent.name.removeprefix("master-")
        for p in prebuilt.glob("master-*/meta.json")
        if (p.parent / "meta.json").exists()
    }


def validate(prebuilt: Path) -> list[str]:
    errors: list[str] = []
    refs_dir = prebuilt / "master-curriculum" / "references"
    if not refs_dir.exists():
        return [f"references dir not found: {refs_dir}"]

    known_citations = collect_known_citations(prebuilt)
    known_slugs = collect_known_slugs(prebuilt)

    for ref in sorted(refs_dir.glob("*.md")):
        text = ref.read_text(encoding="utf-8")
        for cit in extract_citations(text):
            if cit not in known_citations:
                errors.append(
                    f"{ref.name}: citation '{cit}' not found in any master meta.json"
                )
        for slug in extract_master_slugs(text):
            if slug not in known_slugs:
                errors.append(
                    f"{ref.name}: /master-{slug} refers to non-existent master"
                )
    return errors


def main() -> int:
    errors = validate(PREBUILT_DIR)
    if errors:
        print(f"{len(errors)} curriculum source error(s):")
        for e in errors:
            print(f"  ERROR: {e}")
        return 1
    print("curriculum sources OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
