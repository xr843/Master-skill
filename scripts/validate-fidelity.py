#!/usr/bin/env python3
"""Validate fidelity.jsonl structure for all masters.

Checks that every test case has required fields and valid structure.
No API calls needed — pure structural validation.

Usage:
    python scripts/validate-fidelity.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PREBUILT_DIR = Path(__file__).resolve().parent.parent / "prebuilt"

VALID_TEST_TYPES = {"fidelity", "boundary", "pressure"}
VALID_BOUNDARIES = {
    "sectarian_judgment",
    "no_prophecy",
    "neutral_first_turn",
    "no_fabricated_dialogue",
    "no_esoteric_instruction",
}
VALID_PRESSURES = {
    "citation_bypass",
    "informality_bypass",
    "meta_challenge",
    "hostile_challenge",
    "simplicity_bypass",
    "terminology_bypass",
    "relevance_challenge",
    "misunderstanding_challenge",
}


def validate_master(master_dir: Path) -> list[str]:
    """Validate fidelity.jsonl for a single master. Returns list of errors."""
    fidelity_path = master_dir / "tests" / "fidelity.jsonl"
    if not fidelity_path.exists():
        return [f"{master_dir.name}: no fidelity.jsonl found"]

    errors = []
    lines = fidelity_path.read_text(encoding="utf-8").strip().splitlines()

    if len(lines) < 5:
        errors.append(f"{master_dir.name}: fewer than 5 test cases ({len(lines)})")

    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            test = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"{master_dir.name}:{i}: invalid JSON — {e}")
            continue

        # Every test must have "q"
        if "q" not in test:
            errors.append(f"{master_dir.name}:{i}: missing 'q' field")

        # Must have at least one assertion
        has_assertion = any(
            k in test
            for k in [
                "must_cite",
                "must_mention",
                "must_not_contain",
                "must_not_contain_first_turn",
                "must_select_masters",
                "must_have_sections",
                "must_cite_per_master",
            ]
        )
        if not has_assertion:
            errors.append(f"{master_dir.name}:{i}: no assertion fields found")

        # Validate test_type if present
        test_type = test.get("test_type")
        if test_type and test_type not in VALID_TEST_TYPES:
            errors.append(
                f"{master_dir.name}:{i}: invalid test_type '{test_type}' "
                f"(valid: {VALID_TEST_TYPES})"
            )

        # Validate boundary/pressure subtypes
        if test_type == "boundary":
            boundary = test.get("boundary")
            if not boundary:
                errors.append(f"{master_dir.name}:{i}: boundary test missing 'boundary' field")
            elif boundary not in VALID_BOUNDARIES:
                errors.append(
                    f"{master_dir.name}:{i}: unknown boundary '{boundary}' "
                    f"(valid: {VALID_BOUNDARIES})"
                )

        if test_type == "pressure":
            pressure = test.get("pressure")
            if not pressure:
                errors.append(f"{master_dir.name}:{i}: pressure test missing 'pressure' field")

        # List fields must be lists
        for field in ["must_cite", "must_mention", "must_not_contain", "must_not_contain_first_turn"]:
            if field in test and not isinstance(test[field], list):
                errors.append(f"{master_dir.name}:{i}: '{field}' must be a list")

    # Check coverage: should have at least one boundary test
    has_boundary = any(
        json.loads(l).get("test_type") == "boundary"
        for l in lines
        if l.strip()
    )
    if not has_boundary:
        errors.append(f"{master_dir.name}: no boundary tests found (need at least one)")

    return errors


def main():
    all_errors = []
    masters = sorted(
        d for d in PREBUILT_DIR.iterdir()
        if d.is_dir() and (d / "tests" / "fidelity.jsonl").exists()
    )

    for master_dir in masters:
        errors = validate_master(master_dir)
        all_errors.extend(errors)
        if not errors:
            fidelity_path = master_dir / "tests" / "fidelity.jsonl"
            count = len(fidelity_path.read_text().strip().splitlines()) if fidelity_path.exists() else 0
            print(f"  {master_dir.name}: {count} tests OK")

    if all_errors:
        print(f"\n{len(all_errors)} error(s) found:")
        for err in all_errors:
            print(f"  ERROR: {err}")
        sys.exit(1)
    else:
        print(f"\nAll {len(masters)} masters validated successfully.")


if __name__ == "__main__":
    main()
