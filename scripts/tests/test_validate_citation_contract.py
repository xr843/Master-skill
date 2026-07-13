"""Tests for the cross-tradition citation contract validator."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def validator():
    script_path = Path(__file__).resolve().parents[1] / "validate-citation-contract.py"
    spec = importlib.util.spec_from_file_location("validate_citation_contract", script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_citation_contract"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fake_tree(tmp_path: Path) -> Path:
    return tmp_path / "prebuilt"


def contract(*types: str) -> dict:
    return {
        "version": 1,
        "claim_policy": "declared_sources_only",
        "required_for": [
            "doctrinal_claim",
            "practice_guidance",
            "text_interpretation",
        ],
        "allowed_source_types": sorted(types),
        "minimum_claim_coverage": 0.9,
        "live_retrieval_allowed": True,
    }


def write_meta(
    prebuilt: Path,
    slug: str,
    source_types: list[str],
    value: dict | None,
) -> None:
    directory = prebuilt / f"master-{slug}"
    directory.mkdir(parents=True, exist_ok=True)
    data = {
        "slug": slug,
        "sources": [
            {"type": source_type, "id": f"id-{index}", "title": f"source-{index}"}
            for index, source_type in enumerate(source_types)
        ],
    }
    if value is not None:
        data["citation_contract"] = value
    (directory / "meta.json").write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.parametrize(
    "source_types",
    [
        ["cbeta"],
        ["tibetan_canon", "tibetan_treatise"],
        ["compiled_teaching", "pali_canon", "pali_treatise"],
    ],
)
def test_valid_source_family_contracts_pass(validator, fake_tree, source_types):
    write_meta(fake_tree, "demo", source_types, contract(*source_types))
    assert validator.validate(fake_tree) == []


def test_missing_contract_fails(validator, fake_tree):
    write_meta(fake_tree, "demo", ["cbeta"], None)
    errors = validator.validate(fake_tree)
    assert any(
        "master-demo/meta.json" in error and "citation_contract" in error
        for error in errors
    )


@pytest.mark.parametrize("allowed", [[], ["cbeta", "pali_canon"]])
def test_source_type_drift_fails(validator, fake_tree, allowed):
    value = contract("cbeta")
    value["allowed_source_types"] = allowed
    write_meta(fake_tree, "demo", ["cbeta"], value)
    errors = validator.validate(fake_tree)
    assert any(
        "master-demo/meta.json" in error and "allowed_source_types" in error
        for error in errors
    )


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("version", 2),
        ("claim_policy", "any_source"),
        ("required_for", ["doctrinal_claim"]),
        ("minimum_claim_coverage", True),
        ("minimum_claim_coverage", 0.8),
        ("live_retrieval_allowed", "yes"),
    ],
)
def test_fixed_contract_values_are_enforced(
    validator,
    fake_tree,
    field,
    invalid,
):
    value = contract("cbeta")
    value[field] = invalid
    write_meta(fake_tree, "demo", ["cbeta"], value)
    errors = validator.validate(fake_tree)
    assert any(
        "master-demo/meta.json" in error and field in error for error in errors
    )


def test_meta_skill_without_sources_is_ignored(validator, fake_tree):
    write_meta(fake_tree, "debate", [], None)
    assert validator.validate(fake_tree) == []


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_contract_keys_are_exact(validator, fake_tree, mutation):
    value = contract("cbeta")
    if mutation == "missing":
        del value["claim_policy"]
    else:
        value["unexpected"] = "value"
    write_meta(fake_tree, "demo", ["cbeta"], value)
    errors = validator.validate(fake_tree)
    assert any(
        "master-demo/meta.json" in error and "citation_contract" in error
        for error in errors
    )


@pytest.mark.parametrize("source_type", ["", "   ", None, True])
def test_source_types_must_be_non_empty_strings(
    validator,
    fake_tree,
    source_type,
):
    write_meta(fake_tree, "demo", [source_type], contract("cbeta"))
    errors = validator.validate(fake_tree)
    assert any(
        "master-demo/meta.json" in error and "sources[].type" in error
        for error in errors
    )


def test_cli_exit_codes_and_persona_count(
    validator,
    fake_tree,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(validator, "PREBUILT_DIR", fake_tree)
    write_meta(fake_tree, "demo", ["cbeta"], None)

    assert validator.main() == 1
    assert "master-demo/meta.json" in capsys.readouterr().err

    write_meta(fake_tree, "demo", ["cbeta"], contract("cbeta"))
    assert validator.main() == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.strip() == "citation contracts OK (1 personas)"
