"""Tests for validate-persona-fidelity.py.

Covers the v0.8 persona-fidelity schema:
  - signature_phrases (required, 3-7 entries, non-empty strings)
  - style (required, dict with all/qa/monologue, each 30-80 zh-Hans chars)
  - lore_triggers (optional, well-formed schema, content length, source_ref reality)
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_module():
    spec_path = Path(__file__).resolve().parents[1] / "validate-persona-fidelity.py"
    spec = importlib.util.spec_from_file_location("vpf", spec_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["vpf"] = mod
    spec.loader.exec_module(mod)
    return mod


def _base_meta(**overrides):
    data = {
        "slug": "huineng",
        "sources": [{"type": "cbeta", "id": "T48n2008", "title": "坛经"}],
        "signature_phrases": [
            "本来无一物",
            "明心见性",
            "不立文字",
            "无念为宗",
        ],
        "style": {
            "all": "直指自心，言简意赅；不立繁复名相，于学人执著处直下一锤打破，归于自性本具。",
            "qa": "一两句反问或机锋切入，逼学人回光返照，不给攀缘的概念阶梯，立处即真。",
            "monologue": "上堂直示自性本自清净、本不生灭，三纲领无念无相无住贯穿始终，归结见性成佛。",
        },
    }
    data.update(overrides)
    return data


def _write_master(prebuilt: Path, slug: str, data: dict):
    d = prebuilt / f"master-{slug}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def fake_tree(tmp_path):
    return tmp_path / "prebuilt"


# ---------- signature_phrases ----------


def test_missing_signature_phrases_fails(fake_tree):
    vpf = _load_module()
    data = _base_meta()
    del data["signature_phrases"]
    _write_master(fake_tree, "huineng", data)
    errors = vpf.validate(fake_tree)
    assert any("signature_phrases" in e and "missing" in e for e in errors)


def test_empty_signature_phrases_fails(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(signature_phrases=[]))
    errors = vpf.validate(fake_tree)
    assert any("signature_phrases" in e for e in errors)


def test_signature_phrases_too_few_fails(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(signature_phrases=["a", "b"]))
    errors = vpf.validate(fake_tree)
    assert any("signature_phrases" in e and "3" in e for e in errors)


def test_signature_phrases_too_many_fails(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(signature_phrases=["p%d" % i for i in range(8)]))
    errors = vpf.validate(fake_tree)
    assert any("signature_phrases" in e and "7" in e for e in errors)


def test_signature_phrases_blank_entry_fails(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(signature_phrases=["a", "  ", "c", "d"]))
    errors = vpf.validate(fake_tree)
    assert any("signature_phrases" in e for e in errors)


def test_signature_phrases_wrong_type_fails(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(signature_phrases="not-a-list"))
    errors = vpf.validate(fake_tree)
    assert any("signature_phrases" in e for e in errors)


# ---------- style ----------


def test_missing_style_fails(fake_tree):
    vpf = _load_module()
    data = _base_meta()
    del data["style"]
    _write_master(fake_tree, "huineng", data)
    errors = vpf.validate(fake_tree)
    assert any("style" in e and "missing" in e for e in errors)


def test_style_missing_key_fails(fake_tree):
    vpf = _load_module()
    style = {"all": "x" * 50, "qa": "y" * 50}  # missing monologue
    _write_master(fake_tree, "huineng", _base_meta(style=style))
    errors = vpf.validate(fake_tree)
    assert any("monologue" in e for e in errors)


def test_style_extra_key_fails(fake_tree):
    vpf = _load_module()
    style = {"all": "x" * 50, "qa": "y" * 50, "monologue": "z" * 50, "extra": "nope"}
    _write_master(fake_tree, "huineng", _base_meta(style=style))
    errors = vpf.validate(fake_tree)
    assert any("extra" in e for e in errors)


def test_style_value_too_short_fails(fake_tree):
    vpf = _load_module()
    style = {"all": "短", "qa": "y" * 50, "monologue": "z" * 50}
    _write_master(fake_tree, "huineng", _base_meta(style=style))
    errors = vpf.validate(fake_tree)
    assert any("style.all" in e and "30" in e for e in errors)


def test_style_value_too_long_fails(fake_tree):
    vpf = _load_module()
    style = {"all": "x" * 90, "qa": "y" * 50, "monologue": "z" * 50}
    _write_master(fake_tree, "huineng", _base_meta(style=style))
    errors = vpf.validate(fake_tree)
    assert any("style.all" in e and "80" in e for e in errors)


def test_style_value_not_string_fails(fake_tree):
    vpf = _load_module()
    style = {"all": 123, "qa": "y" * 50, "monologue": "z" * 50}
    _write_master(fake_tree, "huineng", _base_meta(style=style))
    errors = vpf.validate(fake_tree)
    assert any("style.all" in e for e in errors)


def test_style_wrong_type_fails(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(style=["not", "a", "dict"]))
    errors = vpf.validate(fake_tree)
    assert any("style" in e for e in errors)


# ---------- lore_triggers (optional) ----------


def test_lore_triggers_absent_is_ok(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta())
    errors = vpf.validate(fake_tree)
    assert errors == []


def test_lore_triggers_empty_list_is_ok(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(lore_triggers=[]))
    errors = vpf.validate(fake_tree)
    assert errors == []


def test_lore_triggers_well_formed_passes(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(lore_triggers=[
        {
            "keys": ["本来无一物"],
            "content": "x" * 100,
            "source_ref": "T48n2008#般若品",
        }
    ]))
    errors = vpf.validate(fake_tree)
    assert errors == []


def test_lore_triggers_wrong_type_fails(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(lore_triggers="not-a-list"))
    errors = vpf.validate(fake_tree)
    assert any("lore_triggers" in e for e in errors)


def test_lore_triggers_entry_not_dict_fails(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(lore_triggers=["nope"]))
    errors = vpf.validate(fake_tree)
    assert any("lore_triggers" in e for e in errors)


def test_lore_triggers_missing_required_fails(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(lore_triggers=[
        {"keys": ["a"], "content": "x" * 100}
    ]))
    errors = vpf.validate(fake_tree)
    assert any("source_ref" in e for e in errors)


def test_lore_triggers_empty_keys_fails(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(lore_triggers=[
        {"keys": [], "content": "x" * 100, "source_ref": "T48n2008"}
    ]))
    errors = vpf.validate(fake_tree)
    assert any("keys" in e for e in errors)


def test_lore_triggers_content_too_short_fails(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(lore_triggers=[
        {"keys": ["a"], "content": "短", "source_ref": "T48n2008"}
    ]))
    errors = vpf.validate(fake_tree)
    assert any("content" in e and "80" in e for e in errors)


def test_lore_triggers_content_too_long_fails(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(lore_triggers=[
        {"keys": ["a"], "content": "x" * 400, "source_ref": "T48n2008"}
    ]))
    errors = vpf.validate(fake_tree)
    assert any("content" in e and "300" in e for e in errors)


def test_lore_triggers_source_ref_not_in_sources_fails(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(lore_triggers=[
        {"keys": ["a"], "content": "x" * 100, "source_ref": "T99n9999"}
    ]))
    errors = vpf.validate(fake_tree)
    assert any("source_ref" in e and "T99n9999" in e for e in errors)


def test_lore_triggers_source_ref_with_anchor_resolves(fake_tree):
    vpf = _load_module()
    # `T48n2008#般若品` should still resolve to source id T48n2008.
    _write_master(fake_tree, "huineng", _base_meta(lore_triggers=[
        {"keys": ["a"], "content": "x" * 100, "source_ref": "T48n2008#般若品"}
    ]))
    errors = vpf.validate(fake_tree)
    assert errors == []


def test_lore_triggers_secondary_keys_requires_selective(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(lore_triggers=[
        {
            "keys": ["a"],
            "secondary_keys": ["b"],
            "content": "x" * 100,
            "source_ref": "T48n2008",
            # selective missing/false → must error
        }
    ]))
    errors = vpf.validate(fake_tree)
    assert any("secondary_keys" in e and "selective" in e for e in errors)


def test_lore_triggers_secondary_keys_with_selective_passes(fake_tree):
    vpf = _load_module()
    _write_master(fake_tree, "huineng", _base_meta(lore_triggers=[
        {
            "keys": ["a"],
            "secondary_keys": ["b"],
            "content": "x" * 100,
            "source_ref": "T48n2008",
            "selective": True,
        }
    ]))
    errors = vpf.validate(fake_tree)
    assert errors == []


# ---------- meta-skill exclusion ----------


def test_meta_skill_without_metajson_is_skipped(fake_tree, tmp_path):
    vpf = _load_module()
    # No meta.json under master-curriculum → validator should not blow up
    (fake_tree / "master-curriculum").mkdir(parents=True)
    _write_master(fake_tree, "huineng", _base_meta())
    errors = vpf.validate(fake_tree)
    assert errors == []


def test_meta_skill_with_kind_marker_is_skipped(fake_tree):
    """master-debate carries a protocol meta.json with kind=meta-skill —
    must not be required to declare persona fields."""
    vpf = _load_module()
    _write_master(fake_tree, "debate", {
        "slug": "debate",
        "kind": "meta-skill",
        "debate_protocol": {"default_rounds": 4},
    })
    _write_master(fake_tree, "huineng", _base_meta())
    errors = vpf.validate(fake_tree)
    assert errors == []
    assert not any("debate" in e for e in errors)
