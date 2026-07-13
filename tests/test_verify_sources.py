"""Tests for verify_sources.py — pure logic and offline CLI, no API calls."""

import json
from pathlib import Path
import subprocess
import sys

import pytest
from skill_writer import derive_citation_contract
from verify_sources import (
    FOJIN_URL_RE,
    FULL_CBETA_RE,
    full_to_short_cbeta,
    validate_source_document,
)


TOOLS = Path(__file__).resolve().parents[1] / "tools"


DECLARED_SOURCES = [
    {"type": "cbeta", "id": "T48n2008", "title": "Platform Sutra"},
    {"type": "tibetan_canon", "id": "Toh:4465", "title": "Lamp"},
    {"type": "kadam_corpus", "id": "BDRC:Pha-chos-Bu-chos", "title": "Kadam"},
    {"type": "tibetan_treatise", "id": "Lam-rim-chen-mo", "title": "Lamrim"},
    {"type": "pali_canon", "id": "SuttaCentral", "title": "Pāli Canon"},
    {"type": "pali_commentary", "id": "PTS:DN-Comm", "title": "DN Comm"},
    {"type": "pali_treatise", "id": "PTS:Vism", "title": "Vism"},
    {
        "type": "compiled_teaching",
        "id": "AjahnChah:FoodForTheHeart",
        "title": "Food for the Heart",
    },
]


def test_verify_sources_module_imports():
    """Verify verify_sources.py can be imported without errors."""
    import verify_sources
    assert callable(getattr(verify_sources, "main", None))


def test_full_to_short_cbeta_t_series():
    assert full_to_short_cbeta("T08n0235") == "T0235"


def test_full_to_short_cbeta_x_series():
    assert full_to_short_cbeta("X62n1182") == "X1182"


def test_full_to_short_cbeta_j_series():
    assert full_to_short_cbeta("J36n0348") == "J0348"


def test_full_to_short_cbeta_strips_volume_number():
    # Volume number (middle digits) must be dropped
    assert full_to_short_cbeta("T34n1718") == "T1718"
    assert full_to_short_cbeta("T01n0001") == "T0001"


def test_full_to_short_cbeta_invalid_returns_none():
    assert full_to_short_cbeta("invalid") is None
    assert full_to_short_cbeta("") is None
    assert full_to_short_cbeta("123") is None


def test_cbeta_id_format_recognition():
    """CBETA IDs follow format like T48n2008, X62n1182, J36n0348."""
    valid_ids = ["T48n2008", "X62n1182", "J36n0348", "T01n0001"]
    for cbeta_id in valid_ids:
        assert FULL_CBETA_RE.match(cbeta_id), f"{cbeta_id} should match FULL_CBETA_RE"


def test_cbeta_id_rejects_invalid():
    invalid_ids = ["T48", "n2008", "abc123", "t48n2008"]  # lowercase prefix is invalid
    for cbeta_id in invalid_ids:
        assert not FULL_CBETA_RE.match(cbeta_id), f"{cbeta_id} should not match FULL_CBETA_RE"


def test_fojin_url_re_matches_cbeta_url():
    line = "See https://fojin.app/texts/T08n0235 for reference"
    m = FOJIN_URL_RE.search(line)
    assert m is not None
    assert m.group(2) == "T08n0235"


def test_fojin_url_re_matches_numeric_id():
    line = "Link: https://fojin.app/texts/12345"
    m = FOJIN_URL_RE.search(line)
    assert m is not None
    assert m.group(2) == "12345"


def test_fojin_url_re_no_match_on_unrelated_url():
    line = "Visit https://example.com/texts/something"
    assert FOJIN_URL_RE.search(line) is None


def test_declared_source_families_and_membership_pass():
    document = {
        "sources": DECLARED_SOURCES,
        "citation_contract": derive_citation_contract(DECLARED_SOURCES),
        "citations": [
            {"type": source["type"], "id": source["id"]}
            for source in DECLARED_SOURCES
        ],
    }
    assert validate_source_document(document) == []


def test_documented_canonical_source_ids_match_the_offline_verifier():
    conventions = (
        Path(__file__).resolve().parents[1]
        / "references"
        / "source-conventions.md"
    ).read_text(encoding="utf-8")
    documented = [
        {"type": "cbeta", "id": "T08n0235", "title": "Diamond Sutra"},
        {"type": "tibetan_canon", "id": "BDRC:W22084", "title": "BDRC work"},
        {"type": "tibetan_canon", "id": "Toh 4465", "title": "Lamp"},
        {"type": "pali_canon", "id": "MN 10", "title": "Satipatthana"},
        {"type": "pali_treatise", "id": "PTS:Vism", "title": "Vism"},
        {
            "type": "compiled_teaching",
            "id": "AjahnChah:FoodForTheHeart",
            "title": "Food for the Heart",
        },
    ]
    for source in documented:
        assert f"`{source['id']}`" in conventions
    document = {
        "sources": documented,
        "citation_contract": derive_citation_contract(documented),
    }
    assert validate_source_document(document) == []


def test_undeclared_citation_member_fails():
    sources = [{"type": "pali_canon", "id": "SuttaCentral"}]
    document = {
        "sources": sources,
        "citation_contract": derive_citation_contract(sources),
        "citations": [{"type": "pali_treatise", "id": "PTS:Vism"}],
    }
    errors = validate_source_document(document)
    assert any("not declared" in error and "PTS:Vism" in error for error in errors)


def test_family_specific_invalid_identifier_fails():
    sources = [{"type": "cbeta", "id": "not-a-cbeta-id"}]
    document = {
        "sources": sources,
        "citation_contract": derive_citation_contract(sources),
    }
    errors = validate_source_document(document)
    assert any("cbeta" in error and "identifier" in error for error in errors)


def test_check_links_cli_validates_declared_sources_offline(tmp_path):
    payload = {
        "sources": DECLARED_SOURCES,
        "citation_contract": derive_citation_contract(DECLARED_SOURCES),
    }
    input_path = tmp_path / "collected.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS / "verify_sources.py"),
            "--check-links",
            str(input_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "declared sources OK (8 sources)"


def test_final_check_cli_validates_generated_persona_directory(tmp_path):
    persona = tmp_path / "master-demo"
    persona.mkdir()
    sources = [{"type": "compiled_teaching", "id": "OfflineSmoke:Deterministic"}]
    (persona / "meta.json").write_text(
        json.dumps(
            {
                "sources": sources,
                "citation_contract": derive_citation_contract(sources),
            }
        ),
        encoding="utf-8",
    )
    (persona / "SKILL.md").write_text(
        "---\nname: master-demo\n---\noffline smoke\n", encoding="utf-8"
    )
    for required in ("teaching.md", "voice.md"):
        (persona / required).write_text("offline smoke", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS / "verify_sources.py"),
            "--final-check",
            str(persona),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "final source check OK (1 sources)"


def test_final_check_rejects_skill_name_that_does_not_match_directory(tmp_path):
    persona = tmp_path / "master-demo"
    persona.mkdir()
    sources = [{"type": "compiled_teaching", "id": "OfflineSmoke:Deterministic"}]
    (persona / "meta.json").write_text(
        json.dumps(
            {
                "sources": sources,
                "citation_contract": derive_citation_contract(sources),
            }
        ),
        encoding="utf-8",
    )
    (persona / "SKILL.md").write_text(
        "---\nname: master_wrong\n---\n", encoding="utf-8"
    )
    for required in ("teaching.md", "voice.md"):
        (persona / required).write_text("offline smoke", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS / "verify_sources.py"),
            "--final-check",
            str(persona),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "SKILL.md name" in result.stderr
    assert "master-demo" in result.stderr
