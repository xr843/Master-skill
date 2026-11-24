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


VERIFY = "VERIFY BEFORE QUOTING"
ENDPOINT = "https://fojin.app/api/verify/trace"


def test_every_quoting_skill_requires_the_check_inside_its_hard_gate():
    """r7 (claude-sonnet-4-6): 29 of 34 failures were quotations only. A host
    that can make HTTP requests checks a recalled sentence with FoJin first."""
    skills = [p for p in sorted((ROOT / "prebuilt").glob("*/SKILL.md")) if p.parent.name != "master-help"]
    for path in skills:
        text = path.read_text(encoding="utf-8")
        gate = _gate(text)
        assert VERIFY in gate, path.parent.name
        rule = gate[gate.index(VERIFY):]
        rule = rule[:rule.index("\n\n")]
        # Single segment found, in the work it is attributed to, canon number matched.
        for needed in ("`found: true`", "不比册号", "「大意是……」", "reader_url", "8 句",
                       "请求失败"):
            assert needed in rule, (path.parent.name, needed)
        # The endpoint itself: in the FoJin section for personas, in the rule for the rest.
        where = text[:text.index("<HARD-GATE>")] if "## FoJin 实时检索" in text else rule
        assert ENDPOINT in where, path.parent.name
        assert "<<<FOJIN_DATA>>>" in where, path.parent.name


def test_generated_personas_get_the_check():
    """The template is str.format-ed: the JSON braces must come out single."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("_skill_writer_q", ROOT / "tools" / "skill_writer.py")
    writer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(writer)
    fields = dict.fromkeys(("frontmatter", "slug", "name", "tradition", "school", "disclaimer",
                            "teaching_content", "voice_content", "safety_block"), "")
    rendered = writer.SKILL_MD_TEMPLATE.format(**fields)
    gate = _gate(rendered)
    assert VERIFY in gate and ENDPOINT in gate
    assert '`{"sentences": ["……"]}`' in gate


def test_debate_rounds_carry_the_check():
    text = (ROOT / "prebuilt" / "master-debate" / "SKILL.md").read_text(encoding="utf-8")
    item = text[text.index("9. 引号只装原文"):text.index("【输出格式】")]
    assert ENDPOINT in item and "found: true" in item


def test_verified_quotes_keep_the_declared_citation_form():
    """Live pilot 2026-11-24 (huineng, 4 fixtures): told to cite the endpoint's
    `cbeta_id`, the model wrote T2008 instead of the declared T48n2008, and three
    of four answers failed on a missing citation that r7 had passed."""
    for path in sorted((ROOT / "prebuilt").glob("*/SKILL.md")):
        gate = _gate(path.read_text(encoding="utf-8"))
        if VERIFY not in gate:
            continue
        assert "`T<册>n<经号>`" in gate, path.parent.name
        assert "出处用返回的" not in gate, path.parent.name
