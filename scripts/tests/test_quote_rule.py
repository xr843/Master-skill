"""Every skill that quotes carries the quotation-marks rule inside its HARD-GATE.

The 2026-10-20 claude-sonnet-4-6 run (c0f0f3b) ruled 474 quotations: 46 found
nowhere, 12 spliced, 9 on the wrong work, 3 invented — the cause of 19 of 23
fidelity failures and 21 of 26 boundary failures. The rule says what may go
inside quotation marks.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULE = "QUOTATION MARKS HOLD ORIGINAL TEXT ONLY"


def _gate(text: str) -> str:
    return text[text.rindex("<HARD-GATE>"):text.rindex("</HARD-GATE>")]


def test_every_quoting_skill_carries_the_rule_inside_its_hard_gate():
    skills = [p for p in sorted((ROOT / "prebuilt").glob("*/SKILL.md")) if p.parent.name != "master-help"]
    assert len(skills) == 19
    missing = [p.parent.name for p in skills if RULE not in _gate(p.read_text(encoding="utf-8"))]
    assert missing == []


def test_generated_personas_get_the_rule():
    assert RULE in (ROOT / "tools" / "skill_writer.py").read_text(encoding="utf-8")


def test_teaching_modes_do_not_present_cross_critique_as_a_masters_words():
    """r5 (fd3d832): master-curriculum quoted ajahn-chah's cross_critique summary of
    Mahasi as 「大意」 of 《A Still Forest Pool》 — a synthesis this repository wrote,
    presented as Ajahn Chah's own remark."""
    for name in ("compare-masters", "master-debate", "master-curriculum"):
        text = (ROOT / "prebuilt" / name / "SKILL.md").read_text(encoding="utf-8")
        assert "CROSS_CRITIQUE IS OUR SYNTHESIS" in _gate(text), name
