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

from _skill_io import PREBUILT_DIR, SCRIPTS_DIR


def _implemented_assertions() -> frozenset[str]:
    """The assertion keys test-fidelity.py actually grades.

    This file used to keep its own list, and it accepted seven keys the
    grader never read — must_have_sections, must_select_masters and five
    more, 71 uses across the teaching-mode fixtures. Fixtures carrying only
    those passed on any reply at all. Reading the grader's own set means a
    key is valid here exactly when something checks it.
    """
    import importlib.util

    scripts = SCRIPTS_DIR
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("_fidelity_grader", scripts / "test-fidelity.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.IMPLEMENTED_ASSERTIONS


IMPLEMENTED_ASSERTIONS = _implemented_assertions()

VALID_TEST_TYPES = {"fidelity", "boundary", "pressure"}
VALID_BOUNDARIES = {
    "sectarian_judgment",
    "no_prophecy",
    "neutral_first_turn",
    "no_fabricated_dialogue",
    "no_esoteric_instruction",
    "no_attainment_judgment",
    "no_winner_judgment",
    "no_strawman",
    "no_fabricated_curriculum",
    # Router skills (/master-help) name a destination and stop. If a router
    # answers the doctrinal question itself, it does so with none of the
    # citation_contract / HARD-GATE machinery each persona carries — so
    # "teaching instead of routing" is a boundary breach, not a shortcut.
    "router_must_not_teach",
    # Crisis (self-harm / suicide / acute psychiatric symptoms): the reply must
    # refer to emergency services and a crisis hotline before any Dharma, per
    # the shared safety clause every persona carries in its HARD-GATE.
    "crisis_referral",
}

# Every persona must exercise the two boundaries the shared safety clause adds.
# A clause no fixture asks about is a rule nothing measures.
PERSONA_REQUIRED_BOUNDARIES = ("crisis_referral", "no_attainment_judgment")


def _is_persona(master_dir: Path) -> bool:
    """A persona declares its own sources; teaching modes declare none."""
    try:
        meta = json.loads((master_dir / "meta.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(meta, dict) and bool(meta.get("sources"))
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

COMPARE_REQUIRED_SECTIONS = {
    "共同点",
    "核心分歧",
    "适用根机",
    "分歧雷达",
    "分歧分类",
    "共通点与宗派背景",
    "推荐继续追问",
    "引用来源",
}


def validate_master(master_dir: Path) -> list[str]:
    """Validate fidelity.jsonl for a single master. Returns list of errors."""
    fidelity_path = master_dir / "tests" / "fidelity.jsonl"
    if not fidelity_path.exists():
        return [f"{master_dir.name}: no fidelity.jsonl found"]

    errors = []
    lines = fidelity_path.read_text(encoding="utf-8").splitlines()
    case_count = sum(bool(line.strip()) for line in lines)
    has_boundary = False
    boundaries_seen: set[str] = set()

    if case_count < 5:
        errors.append(f"{master_dir.name}: fewer than 5 test cases ({case_count})")

    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            test = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"{master_dir.name}:{i}: invalid JSON — {e}")
            continue

        if not isinstance(test, dict):
            errors.append(f"{master_dir.name}:{i}: expected a JSON object")
            continue

        # Every test must have "q"
        if "q" not in test:
            errors.append(f"{master_dir.name}:{i}: missing 'q' field")
            continue
        if not isinstance(test["q"], str) or not test["q"].strip():
            errors.append(f"{master_dir.name}:{i}: 'q' must be a non-empty string")
            continue

        # Check shape before semantic checks iterate fields or construct sets.
        invalid_lists = False
        for field in (
            "must_cite", "must_mention", "must_convey", "must_not_contain",
            "must_not_contain_first_turn", "must_select_pair", "must_have_rounds",
            "must_select_masters", "must_have_sections",
        ):
            if field in test and (
                not isinstance(test[field], list)
                or not all(isinstance(item, str) for item in test[field])
            ):
                errors.append(f"{master_dir.name}:{i}: '{field}' must be a list of strings")
                invalid_lists = True
        if invalid_lists:
            continue

        # Every must_* key has to be one the grader reads; anything else is
        # an assertion that looks enforced and is not.
        for key in sorted(k for k in test if k.startswith("must_")):
            if key not in IMPLEMENTED_ASSERTIONS:
                errors.append(
                    f"{master_dir.name}:{i}: '{key}' is not graded by "
                    f"scripts/test-fidelity.py — implement it there or remove it"
                )

        # A per-master or per-round citation rule applies to the masters or
        # rounds the fixture names. Without them it has nothing to apply to
        # and passes any reply — compare-masters #16 did.
        if test.get("must_cite_per_master") and not (
            test.get("must_select_masters") or test.get("must_select_pair")
        ):
            errors.append(
                f"{master_dir.name}:{i}: must_cite_per_master without "
                "must_select_masters / must_select_pair checks nothing"
            )
        if test.get("must_cite_per_round") and not test.get("must_have_rounds"):
            errors.append(
                f"{master_dir.name}:{i}: must_cite_per_round without "
                "must_have_rounds checks nothing"
            )

        # Must have at least one assertion
        if not any(k in test for k in IMPLEMENTED_ASSERTIONS):
            errors.append(f"{master_dir.name}:{i}: no assertion fields found")

        # Validate test_type if present
        test_type = test.get("test_type")
        if "test_type" in test and (
            not isinstance(test_type, str) or test_type not in VALID_TEST_TYPES
        ):
            errors.append(
                f"{master_dir.name}:{i}: invalid test_type '{test_type}' "
                f"(valid: {VALID_TEST_TYPES})"
            )
            continue

        # Validate boundary/pressure subtypes
        if test_type == "boundary":
            boundary = test.get("boundary")
            if not boundary:
                errors.append(f"{master_dir.name}:{i}: boundary test missing 'boundary' field")
            elif not isinstance(boundary, str) or boundary not in VALID_BOUNDARIES:
                errors.append(
                    f"{master_dir.name}:{i}: unknown boundary '{boundary}' "
                    f"(valid: {VALID_BOUNDARIES})"
                )
            else:
                has_boundary = True
                boundaries_seen.add(boundary)

        if test_type == "pressure":
            pressure = test.get("pressure")
            if not pressure:
                errors.append(f"{master_dir.name}:{i}: pressure test missing 'pressure' field")

        if master_dir.name == "compare-masters" and test_type not in {"boundary", "pressure"}:
            sections = set(test.get("must_have_sections", []))
            missing = sorted(COMPARE_REQUIRED_SECTIONS - sections)
            if missing:
                errors.append(
                    f"{master_dir.name}:{i}: compare test missing required output "
                    f"sections: {', '.join(missing)}"
                )

    # Check coverage: should have at least one boundary test
    if not has_boundary:
        errors.append(f"{master_dir.name}: no boundary tests found (need at least one)")

    if _is_persona(master_dir):
        for required in PERSONA_REQUIRED_BOUNDARIES:
            if required not in boundaries_seen:
                errors.append(
                    f"{master_dir.name}: persona has no '{required}' boundary test "
                    "(the shared safety clause requires one)"
                )

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
