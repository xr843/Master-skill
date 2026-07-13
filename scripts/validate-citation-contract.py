#!/usr/bin/env python3
"""Validate source-neutral citation contracts in persona metadata."""
from __future__ import annotations

import json
import sys
from pathlib import Path


PREBUILT_DIR = Path(__file__).resolve().parent.parent / "prebuilt"

EXPECTED_REQUIRED_FOR = [
    "doctrinal_claim",
    "practice_guidance",
    "text_interpretation",
]
EXPECTED_KEYS = {
    "version",
    "claim_policy",
    "required_for",
    "allowed_source_types",
    "minimum_claim_coverage",
    "live_retrieval_allowed",
}


def _display_path(meta_path: Path) -> str:
    return f"{meta_path.parent.name}/meta.json"


def _persona_count(prebuilt_dir: Path) -> int:
    count = 0
    for meta_path in prebuilt_dir.glob("master-*/meta.json"):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("sources"):
            count += 1
    return count


def validate(prebuilt_dir: Path) -> list[str]:
    """Return deterministic citation-contract errors for persona metadata."""
    errors: list[str] = []

    for meta_path in sorted(prebuilt_dir.glob("master-*/meta.json")):
        path = _display_path(meta_path)
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: invalid metadata: {exc}")
            continue

        sources = data.get("sources")
        if not sources:
            continue
        if not isinstance(sources, list):
            errors.append(f"{path}: sources must be a list")
            continue

        source_types: list[str] = []
        for index, source in enumerate(sources):
            source_type = source.get("type") if isinstance(source, dict) else None
            if not isinstance(source_type, str) or not source_type.strip():
                errors.append(
                    f"{path}: sources[].type at index {index} must be a non-empty string"
                )
                continue
            source_types.append(source_type)

        contract = data.get("citation_contract")
        if not isinstance(contract, dict):
            errors.append(f"{path}: citation_contract must be an object")
            continue

        contract_keys = set(contract)
        if contract_keys != EXPECTED_KEYS:
            missing = sorted(EXPECTED_KEYS - contract_keys)
            extra = sorted(contract_keys - EXPECTED_KEYS)
            errors.append(
                f"{path}: citation_contract keys must be exact; "
                f"missing={missing}, extra={extra}"
            )

        version = contract.get("version")
        if type(version) is not int or version != 1:
            errors.append(f"{path}: version must be integer 1")

        if contract.get("claim_policy") != "declared_sources_only":
            errors.append(
                f"{path}: claim_policy must be 'declared_sources_only'"
            )

        if contract.get("required_for") != EXPECTED_REQUIRED_FOR:
            errors.append(
                f"{path}: required_for must equal {EXPECTED_REQUIRED_FOR}"
            )

        allowed_source_types = contract.get("allowed_source_types")
        expected_source_types = sorted(set(source_types))
        if (
            not isinstance(allowed_source_types, list)
            or any(
                not isinstance(source_type, str) or not source_type.strip()
                for source_type in allowed_source_types
            )
            or allowed_source_types != expected_source_types
        ):
            errors.append(
                f"{path}: allowed_source_types must equal {expected_source_types}"
            )

        coverage = contract.get("minimum_claim_coverage")
        if (
            isinstance(coverage, bool)
            or not isinstance(coverage, (int, float))
            or coverage != 0.9
        ):
            errors.append(f"{path}: minimum_claim_coverage must be numeric 0.9")

        if contract.get("live_retrieval_allowed") is not True:
            errors.append(f"{path}: live_retrieval_allowed must be true")

    return errors


def main() -> int:
    errors = validate(PREBUILT_DIR)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"citation contracts OK ({_persona_count(PREBUILT_DIR)} personas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
