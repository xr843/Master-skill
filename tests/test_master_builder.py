"""Tests for the create-master generation contract lifecycle."""
from __future__ import annotations

import json
from pathlib import Path

import master_builder


SOURCES = [
    {"type": "pali_canon", "id": "SuttaCentral", "title": "Pāli Canon"},
    {
        "type": "compiled_teaching",
        "id": "AjahnChah:FoodForTheHeart",
        "title": "Food for the Heart",
    },
]


def test_review_prompt_and_writer_share_one_in_memory_contract(monkeypatch):
    context = master_builder.prepare_generation_context(SOURCES)
    prompt = master_builder.build_doctrine_review_prompt("teaching", context)
    serialized = json.dumps(
        context["citation_contract"], ensure_ascii=False, sort_keys=True
    )
    assert serialized in prompt

    captured = {}

    def fake_create_teacher(**kwargs):
        captured.update(kwargs)
        return "/tmp/generated"

    monkeypatch.setattr(master_builder, "create_teacher", fake_create_teacher)
    result = master_builder.generate_teacher_skill(
        name="Ajahn Demo",
        tradition="南传",
        school="上座部",
        era="1900",
        languages=["en"],
        teaching_content="teaching",
        voice_content="voice",
        generation_context=context,
    )

    assert result == "/tmp/generated"
    assert captured["citation_contract"] is context["citation_contract"]
    assert captured["sources"] is context["sources"]


def test_prepare_generation_context_rejects_contract_drift():
    contract = {
        "version": 1,
        "claim_policy": "declared_sources_only",
        "required_for": [
            "doctrinal_claim",
            "practice_guidance",
            "text_interpretation",
        ],
        "allowed_source_types": ["cbeta"],
        "minimum_claim_coverage": 0.9,
        "live_retrieval_allowed": True,
    }
    try:
        master_builder.prepare_generation_context(SOURCES, contract)
    except ValueError as exc:
        assert "citation_contract" in str(exc)
    else:
        raise AssertionError("contract drift was accepted")


def test_doctrine_reviewer_counts_every_contract_required_claim_class():
    reviewer = (
        Path(__file__).resolve().parents[1] / "prompts" / "doctrine_reviewer.md"
    ).read_text(encoding="utf-8")
    assert "教义断言、修行指导、文本解释三类项目的合规引用总数" in reviewer
    assert "教义断言、修行指导、文本解释三类项目总数" in reviewer
    for claim_class in (
        "doctrinal_claim",
        "practice_guidance",
        "text_interpretation",
    ):
        assert claim_class in reviewer


def test_analysis_prompt_keeps_non_cbeta_identity_and_real_locator():
    data = {
        "entity": None,
        "lineage": [],
        "sources": [
            {"type": "pali_canon", "id": "MN 10", "title": "Satipaṭṭhāna Sutta"}
        ],
        "texts": [
            {
                "id": 4242,
                "title_zh": "念处经",
                "source_type": "pali_canon",
                "source_id": "MN 10",
            }
        ],
        "content_samples": [
            {
                "text_id": 4242,
                "title": "念处经",
                "source_type": "pali_canon",
                "source_id": "MN 10",
                "content": "mindfulness source passage",
            }
        ],
        "terms": [],
    }

    prompt = master_builder.build_analysis_prompt(
        "sutra_analyzer", "Demo Sayadaw", data
    )

    assert "source_type=pali_canon" in prompt
    assert "source_id=MN 10" in prompt
    assert "FoJin text_id=4242" in prompt
    assert "mindfulness source passage" in prompt


def test_analysis_prompt_includes_manual_sources_when_no_text_results_exist():
    prompt = master_builder.build_analysis_prompt(
        "sutra_analyzer",
        "Manual Source Master",
        {
            "entity": None,
            "lineage": [],
            "sources": [
                {
                    "type": "compiled_teaching",
                    "id": "ManualArchive:TeachingOne",
                    "title": "Teaching One",
                }
            ],
            "texts": [],
            "content_samples": [],
            "terms": [],
        },
    )

    assert "title=Teaching One" in prompt
    assert "source_type=compiled_teaching" in prompt
    assert "source_id=ManualArchive:TeachingOne" in prompt
