"""Tests for validate-cross-critique.py."""
from __future__ import annotations

import json
from pathlib import Path

import importlib.util
import sys

import pytest


def _load_module():
    spec_path = Path(__file__).resolve().parents[1] / "validate-cross-critique.py"
    spec = importlib.util.spec_from_file_location("vcc", spec_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["vcc"] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_master(prebuilt: Path, slug: str, sources: list[dict], cross_critique=None):
    d = prebuilt / f"master-{slug}"
    d.mkdir(parents=True, exist_ok=True)
    data = {"slug": slug, "sources": sources}
    if cross_critique is not None:
        data["cross_critique"] = cross_critique
    (d / "meta.json").write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def fake_tree(tmp_path):
    prebuilt = tmp_path / "prebuilt"
    # build enough masters to satisfy required_pairs in tests that need them
    for slug in [
        "huineng", "yinguang", "kumarajiva", "xuanzang", "zhiyi",
        "tsongkhapa", "ajahn-chah", "mahasi-sayadaw", "atisha", "ouyi",
    ]:
        _write_master(prebuilt, slug, [{"type": "cbeta", "id": "T00n0001", "title": "demo"}])
    return prebuilt


def test_empty_cross_critique_is_ok(fake_tree):
    vcc = _load_module()
    # No master has cross_critique; structural check passes,
    # but required_pairs check still fails (no coverage).
    errors = vcc.validate(fake_tree, check_coverage=False)
    assert errors == []


def test_well_formed_entry_passes(fake_tree):
    vcc = _load_module()
    _write_master(fake_tree, "huineng",
        [{"type": "cbeta", "id": "T48n2008", "title": "坛经"}],
        cross_critique=[
            {"target_master": "yinguang", "position": "对净土：本性弥陀唯心净土，何曾离自心。", "citation": "T48n2008"},
        ])
    errors = vcc.validate(fake_tree, check_coverage=False)
    # Only the huineng→yinguang structural check should pass.
    huineng_errors = [e for e in errors if "huineng" in e]
    assert huineng_errors == []


def test_missing_required_field(fake_tree):
    vcc = _load_module()
    _write_master(fake_tree, "huineng",
        [{"type": "cbeta", "id": "T48n2008", "title": "坛经"}],
        cross_critique=[{"target_master": "yinguang"}])  # no position, no citation
    errors = vcc.validate(fake_tree, check_coverage=False)
    assert any("position" in e for e in errors)
    assert any("citation" in e for e in errors)


def test_cannot_target_self(fake_tree):
    vcc = _load_module()
    _write_master(fake_tree, "huineng",
        [{"type": "cbeta", "id": "T48n2008", "title": "坛经"}],
        cross_critique=[{"target_master": "huineng", "position": "x" * 50, "citation": "T48n2008"}])
    errors = vcc.validate(fake_tree, check_coverage=False)
    assert any("self" in e.lower() for e in errors)


def test_cannot_target_meta_skill(fake_tree):
    vcc = _load_module()
    _write_master(fake_tree, "huineng",
        [{"type": "cbeta", "id": "T48n2008", "title": "坛经"}],
        cross_critique=[{"target_master": "curriculum", "position": "x" * 50, "citation": "T48n2008"}])
    errors = vcc.validate(fake_tree, check_coverage=False)
    assert any("meta-skill" in e or "curriculum" in e for e in errors)


def test_unknown_target_master(fake_tree):
    vcc = _load_module()
    _write_master(fake_tree, "huineng",
        [{"type": "cbeta", "id": "T48n2008", "title": "坛经"}],
        cross_critique=[{"target_master": "ghost", "position": "x" * 50, "citation": "T48n2008"}])
    errors = vcc.validate(fake_tree, check_coverage=False)
    assert any("ghost" in e for e in errors)


def test_citation_not_in_own_sources(fake_tree):
    vcc = _load_module()
    _write_master(fake_tree, "huineng",
        [{"type": "cbeta", "id": "T48n2008", "title": "坛经"}],
        cross_critique=[{"target_master": "yinguang", "position": "x" * 50, "citation": "T99n9999"}])
    errors = vcc.validate(fake_tree, check_coverage=False)
    assert any("T99n9999" in e for e in errors)


def test_position_length_bounds(fake_tree):
    vcc = _load_module()
    _write_master(fake_tree, "huineng",
        [{"type": "cbeta", "id": "T48n2008", "title": "坛经"}],
        cross_critique=[
            {"target_master": "yinguang", "position": "短", "citation": "T48n2008"},  # < 10
            {"target_master": "zhiyi", "position": "x" * 400, "citation": "T48n2008"},  # > 300
        ])
    errors = vcc.validate(fake_tree, check_coverage=False)
    assert any("length" in e for e in errors)


def test_coverage_fails_when_pairs_missing(fake_tree):
    vcc = _load_module()
    errors = vcc.validate(fake_tree, check_coverage=True)
    # Should report all 16 missing critique entries.
    missing_errors = [e for e in errors if "missing critique" in e]
    assert len(missing_errors) == 16


def test_coverage_succeeds_with_full_pairs(fake_tree):
    vcc = _load_module()
    pairs = [
        ("huineng", "yinguang"), ("yinguang", "huineng"),
        ("kumarajiva", "xuanzang"), ("xuanzang", "kumarajiva"),
        ("huineng", "zhiyi"), ("zhiyi", "huineng"),
        ("tsongkhapa", "huineng"), ("huineng", "tsongkhapa"),
        ("ajahn-chah", "mahasi-sayadaw"), ("mahasi-sayadaw", "ajahn-chah"),
        ("atisha", "huineng"), ("huineng", "atisha"),
        ("ouyi", "yinguang"), ("yinguang", "ouyi"),
        ("ouyi", "tsongkhapa"), ("tsongkhapa", "ouyi"),
    ]
    by_slug: dict[str, list[dict]] = {}
    for src, tgt in pairs:
        by_slug.setdefault(src, []).append(
            {"target_master": tgt, "position": "x" * 50, "citation": "T00n0001"})
    for slug, cc in by_slug.items():
        _write_master(fake_tree, slug, [{"type": "cbeta", "id": "T00n0001", "title": "demo"}], cc)
    errors = vcc.validate(fake_tree, check_coverage=True)
    assert errors == []
