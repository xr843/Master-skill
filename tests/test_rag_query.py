"""Regression tests for source-neutral live-retrieval formatting."""

import pytest

from rag_query import format_search_results, format_semantic_results


PALI_RESULT = {
    "title": "Satipaṭṭhāna Sutta",
    "source_type": "pali_canon",
    "source_id": "MN 10",
    "text_id": 123,
    "content": "Mindfulness passage",
    "score": 0.95,
}


@pytest.mark.parametrize("brief", [False, True])
def test_search_formatter_preserves_declared_source_identity(brief):
    output = format_search_results({"results": [PALI_RESULT]}, brief=brief)
    assert "source_type=pali_canon" in output
    assert "source_id=MN 10" in output


@pytest.mark.parametrize("brief", [False, True])
def test_semantic_formatter_preserves_declared_source_identity(brief):
    output = format_semantic_results({"results": [PALI_RESULT]}, brief=brief)
    assert "source_type=pali_canon" in output
    assert "source_id=MN 10" in output


def test_cbeta_legacy_fields_are_normalized_to_source_identity():
    output = format_search_results(
        {
            "results": [
                {
                    "title": "Platform Sutra",
                    "source": "cbeta",
                    "cbeta_id": "T48n2008",
                    "content": "Passage",
                }
            ]
        }
    )
    assert "source_type=cbeta" in output
    assert "source_id=T48n2008" in output
