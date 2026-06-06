"""Tests for validate-curriculum-sources.py.

Verifies that citations (CBETA T-numbers, X-numbers, Toh, compiled-teaching ids)
and /master-<slug> references in curriculum reference files cross-check against
the actual prebuilt master metadata.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import importlib.util
import sys


def _load_module():
    spec_path = Path(__file__).resolve().parents[1] / "validate-curriculum-sources.py"
    spec = importlib.util.spec_from_file_location("vcs", spec_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["vcs"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def fake_prebuilt(tmp_path):
    """Fake prebuilt tree with two masters and a curriculum dir."""
    prebuilt = tmp_path / "prebuilt"
    # Master A: cbeta source
    (prebuilt / "master-aaa").mkdir(parents=True)
    (prebuilt / "master-aaa" / "meta.json").write_text(json.dumps({
        "slug": "aaa",
        "sources": [{"type": "cbeta", "id": "T48n2008", "title": "demo"}],
    }), encoding="utf-8")
    # Master B: compiled_teaching source + Toh
    (prebuilt / "master-bbb").mkdir(parents=True)
    (prebuilt / "master-bbb" / "meta.json").write_text(json.dumps({
        "slug": "bbb",
        "sources": [
            {"type": "compiled_teaching", "id": "AjahnChah:FoodForTheHeart", "title": "demo"},
            {"type": "84000", "id": "Toh 21", "title": "demo"},
        ],
    }), encoding="utf-8")
    (prebuilt / "master-curriculum" / "references").mkdir(parents=True)
    return prebuilt


def test_extract_citations_finds_T_numbers(fake_prebuilt):
    vcs = _load_module()
    text = "See 《坛经》【T48n2008】 for details."
    assert "T48n2008" in vcs.extract_citations(text)


def test_extract_citations_finds_Toh(fake_prebuilt):
    vcs = _load_module()
    text = "藏文藏经 Toh 21 心经..."
    assert "Toh 21" in vcs.extract_citations(text)


def test_extract_citations_finds_compiled_teaching(fake_prebuilt):
    vcs = _load_module()
    text = "见 AjahnChah:FoodForTheHeart ..."
    assert "AjahnChah:FoodForTheHeart" in vcs.extract_citations(text)


def test_extract_master_slugs(fake_prebuilt):
    vcs = _load_module()
    text = "推荐 master：/master-aaa ；交叉 /master-bbb 。"
    assert vcs.extract_master_slugs(text) == {"aaa", "bbb"}


def test_collect_known_citations(fake_prebuilt):
    vcs = _load_module()
    known = vcs.collect_known_citations(fake_prebuilt)
    assert "T48n2008" in known
    assert "AjahnChah:FoodForTheHeart" in known
    assert "Toh 21" in known


def test_validate_pass(fake_prebuilt):
    vcs = _load_module()
    ref = fake_prebuilt / "master-curriculum" / "references" / "ok.md"
    ref.write_text(
        "## Path\n- 主用经《坛经》【T48n2008】\n- master：/master-aaa\n- 藏：Toh 21\n",
        encoding="utf-8",
    )
    errors = vcs.validate(fake_prebuilt)
    assert errors == []


def test_validate_fails_on_fabricated_citation(fake_prebuilt):
    vcs = _load_module()
    ref = fake_prebuilt / "master-curriculum" / "references" / "bad.md"
    ref.write_text("【T99n9999】 fake\n", encoding="utf-8")
    errors = vcs.validate(fake_prebuilt)
    assert any("T99n9999" in e for e in errors)


def test_validate_fails_on_unknown_master_slug(fake_prebuilt):
    vcs = _load_module()
    ref = fake_prebuilt / "master-curriculum" / "references" / "bad.md"
    ref.write_text("/master-ghost\n", encoding="utf-8")
    errors = vcs.validate(fake_prebuilt)
    assert any("ghost" in e for e in errors)


def test_validate_ignores_self_reference_to_curriculum_and_compare(fake_prebuilt):
    """/master-curriculum and /compare-masters references inside the references
    files are skill self-references, not master slugs — must not raise."""
    vcs = _load_module()
    ref = fake_prebuilt / "master-curriculum" / "references" / "ok.md"
    ref.write_text(
        "延伸 → /compare-masters · /master-debate · /master-curriculum\n",
        encoding="utf-8",
    )
    errors = vcs.validate(fake_prebuilt)
    assert errors == []
