"""Source-identity tests for the create-master collection boundary."""

from sutra_collector import collect_teacher_data


class PaliBridge:
    def search_kg_entities(self, *_args, **_kwargs):
        return {"results": []}

    def search_texts(self, *_args, **_kwargs):
        return {
            "results": [
                {
                    "id": 4242,
                    "title_zh": "念处经",
                    "source_type": "pali_canon",
                    "source_id": "MN 10",
                }
            ]
        }

    def get_text_content(self, *_args, **_kwargs):
        return {"content": "mindfulness source passage"}


def test_collector_carries_generic_source_identity_into_content_samples():
    data = collect_teacher_data("Demo Sayadaw", bridge=PaliBridge())

    assert data["sources"] == [
        {"type": "pali_canon", "id": "MN 10", "title": "念处经"}
    ]
    assert data["content_samples"] == [
        {
            "text_id": 4242,
            "title": "念处经",
            "source_type": "pali_canon",
            "source_id": "MN 10",
            "content": "mindfulness source passage",
        }
    ]
    assert data["citation_contract"]["allowed_source_types"] == ["pali_canon"]
