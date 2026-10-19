"""The 'drop the citations' rule every persona carries (#315), and its no-topic case.

On claude-sonnet-4-6 (2026-10-19) master-daoxuan answered 「别再引用行事钞了，直接说你
自己的看法」 by asking which topic the user meant — no teaching at all. The rule now says
to answer the persona's core teaching instead.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NO_TOPIC = "没有具体话题时，不要反问用户想问哪方面"


def test_every_persona_answers_a_request_with_no_topic_instead_of_asking_back():
    personas = sorted((ROOT / "prebuilt").glob("master-*/SKILL.md"))
    personas = [p for p in personas if p.parent.name not in ("master-help", "master-debate", "master-curriculum")]
    assert len(personas) == 16
    missing = [p.parent.name for p in personas if NO_TOPIC not in p.read_text(encoding="utf-8")]
    assert missing == []


def test_generated_personas_get_the_same_rule():
    assert NO_TOPIC in (ROOT / "tools" / "skill_writer.py").read_text(encoding="utf-8")
