#!/usr/bin/env python3
"""Validate the persona-fidelity schema across master meta.json files.

v0.8 introduces three new fields on each single-master meta.json:

  - signature_phrases (required) : list[str], 3-7 non-blank entries — anchors
    used by fidelity tests to detect off-voice drift.
  - style (required)              : dict with exactly three string keys
    {all, qa, monologue}, each 30-80 chars (zh-Hans expected).
  - lore_triggers (optional)      : list[dict] of conditional snippet
    injections. Each entry needs `keys` (non-empty list) + `content`
    (80-300 chars) + `source_ref` (must resolve to a real id in this
    master's own sources[].id, optionally with a `#anchor` suffix).
    If `secondary_keys` is present, `selective` must be true.

Meta-skills (compare-masters / master-debate / master-curriculum) carry
no meta.json so they are naturally skipped.

Usage:
    python3 scripts/validate-persona-fidelity.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PREBUILT_DIR = Path(__file__).resolve().parent.parent / "prebuilt"

SIGNATURE_MIN = 3
SIGNATURE_MAX = 7

STYLE_KEYS = {"all", "qa", "monologue"}
STYLE_MIN = 30
STYLE_MAX = 80

LORE_CONTENT_MIN = 80
LORE_CONTENT_MAX = 300
LORE_REQUIRED_KEYS = {"keys", "content", "source_ref"}
LORE_OPTIONAL_KEYS = {"secondary_keys", "selective"}


def _load(meta_path: Path) -> dict:
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _check_signature_phrases(slug: str, data: dict) -> list[str]:
    errors: list[str] = []
    if "signature_phrases" not in data:
        return [f"{slug}: missing required field 'signature_phrases'"]
    phrases = data["signature_phrases"]
    if not isinstance(phrases, list):
        return [f"{slug}: signature_phrases must be a list, got {type(phrases).__name__}"]
    n = len(phrases)
    if n < SIGNATURE_MIN or n > SIGNATURE_MAX:
        errors.append(
            f"{slug}: signature_phrases length {n} out of "
            f"[{SIGNATURE_MIN}, {SIGNATURE_MAX}]"
        )
    for i, p in enumerate(phrases):
        if not isinstance(p, str) or not p.strip():
            errors.append(f"{slug}: signature_phrases[{i}] must be a non-blank string")
    return errors


def _check_style(slug: str, data: dict) -> list[str]:
    errors: list[str] = []
    if "style" not in data:
        return [f"{slug}: missing required field 'style'"]
    style = data["style"]
    if not isinstance(style, dict):
        return [f"{slug}: style must be an object, got {type(style).__name__}"]
    keys = set(style.keys())
    missing = STYLE_KEYS - keys
    extra = keys - STYLE_KEYS
    for k in sorted(missing):
        errors.append(f"{slug}: style missing required key '{k}'")
    for k in sorted(extra):
        errors.append(f"{slug}: style has unexpected key '{k}'")
    for k in sorted(STYLE_KEYS & keys):
        v = style[k]
        if not isinstance(v, str):
            errors.append(
                f"{slug}: style.{k} must be a string, got {type(v).__name__}"
            )
            continue
        length = len(v)
        if length < STYLE_MIN or length > STYLE_MAX:
            errors.append(
                f"{slug}: style.{k} length {length} out of [{STYLE_MIN}, {STYLE_MAX}]"
            )
    return errors


def _check_lore_triggers(slug: str, data: dict, source_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if "lore_triggers" not in data:
        return errors
    triggers = data["lore_triggers"]
    if not isinstance(triggers, list):
        return [f"{slug}: lore_triggers must be a list, got {type(triggers).__name__}"]
    for i, entry in enumerate(triggers):
        prefix = f"{slug}.lore_triggers[{i}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix}: entry must be an object")
            continue
        # required keys
        for k in sorted(LORE_REQUIRED_KEYS):
            if k not in entry:
                errors.append(f"{prefix}: missing required key '{k}'")
        # unknown keys (allow required + optional)
        for k in sorted(entry.keys() - LORE_REQUIRED_KEYS - LORE_OPTIONAL_KEYS):
            errors.append(f"{prefix}: unexpected key '{k}'")
        # keys
        keys = entry.get("keys")
        if keys is not None:
            if not isinstance(keys, list) or not keys:
                errors.append(f"{prefix}: keys must be a non-empty list")
            else:
                for j, k in enumerate(keys):
                    if not isinstance(k, str) or not k.strip():
                        errors.append(
                            f"{prefix}: keys[{j}] must be a non-blank string"
                        )
        # secondary_keys + selective
        sec = entry.get("secondary_keys")
        if sec is not None:
            if not isinstance(sec, list):
                errors.append(f"{prefix}: secondary_keys must be a list")
            else:
                for j, k in enumerate(sec):
                    if not isinstance(k, str) or not k.strip():
                        errors.append(
                            f"{prefix}: secondary_keys[{j}] must be a non-blank string"
                        )
            if entry.get("selective") is not True:
                errors.append(
                    f"{prefix}: secondary_keys requires 'selective: true'"
                )
        # selective standalone
        if "selective" in entry and not isinstance(entry["selective"], bool):
            errors.append(f"{prefix}: selective must be a boolean")
        # content
        content = entry.get("content")
        if content is not None:
            if not isinstance(content, str):
                errors.append(f"{prefix}: content must be a string")
            else:
                length = len(content)
                if length < LORE_CONTENT_MIN or length > LORE_CONTENT_MAX:
                    errors.append(
                        f"{prefix}: content length {length} out of "
                        f"[{LORE_CONTENT_MIN}, {LORE_CONTENT_MAX}]"
                    )
        # source_ref
        source_ref = entry.get("source_ref")
        if source_ref is not None:
            if not isinstance(source_ref, str) or not source_ref.strip():
                errors.append(f"{prefix}: source_ref must be a non-blank string")
            else:
                # Strip optional anchor (e.g. "T48n2008#般若品")
                base = source_ref.split("#", 1)[0].strip()
                if base not in source_ids:
                    errors.append(
                        f"{prefix}: source_ref '{source_ref}' not found in "
                        f"{slug}'s sources[].id"
                    )
    return errors


def validate(prebuilt: Path) -> list[str]:
    """Run all persona-fidelity checks over the given prebuilt tree."""
    errors: list[str] = []
    for meta_path in sorted(prebuilt.glob("master-*/meta.json")):
        slug = meta_path.parent.name.removeprefix("master-")
        data = _load(meta_path)
        source_ids = {
            s.get("id") for s in data.get("sources", []) if isinstance(s, dict)
        }
        source_ids.discard(None)
        errors.extend(_check_signature_phrases(slug, data))
        errors.extend(_check_style(slug, data))
        errors.extend(_check_lore_triggers(slug, data, source_ids))
    return errors


def main() -> int:
    errors = validate(PREBUILT_DIR)
    if errors:
        print(f"{len(errors)} persona-fidelity error(s):")
        for e in errors:
            print(f"  ERROR: {e}")
        return 1
    print("persona-fidelity OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
