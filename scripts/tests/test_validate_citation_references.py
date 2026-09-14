"""Tests for the static citation-reference gate.

The 2026-08-31 DeepSeek sweep cost ¥3.89 and found one instance of a defect the
repo can detect for free, deterministically, on every PR: a persona's own
SKILL.md / sources/ / references/ instructing a citation that its meta.json does
not declare. The graded run found `Toh:3861` only because a fixture happened to
trigger it; a static sweep finds every one.

`validate-citation-contract.py` validates meta.json's contract *fields* and
never reads SKILL.md, so this class had nothing looking at it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate-citation-references.py"


@pytest.fixture
def validator():
    scripts_dir = SCRIPT.parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location("validate_citation_refs", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_citation_refs"] = module
    spec.loader.exec_module(module)
    return module


# --- template blocks are documentation, not citations -----------------------

def test_curly_brace_template_is_not_a_citation(validator):
    assert validator.is_template_block("《典籍名》§章节】（BDRC: {bdrc_id}）") is True


def test_x_run_placeholder_is_not_a_citation(validator):
    """米拉日巴 documents its format as （BDRC: Wxxxxx）."""
    assert validator.is_template_block("《典籍名》§章节】（BDRC: Wxxxxx）") is True


def test_juan_n_placeholder_is_not_a_citation(validator):
    """智顗 documents 【《法華玄義》卷N，T1716】 — a real id inside a template."""
    assert validator.is_template_block("《法華玄義》卷N，T1716") is True


def test_a_real_citation_is_not_a_template(validator):
    assert validator.is_template_block("《菩提道灯论》，Toh 4465") is False


# --- the sweep itself -------------------------------------------------------

def test_finds_a_persona_instructing_an_undeclared_citation(validator, tmp_path):
    """SKILL.md:125 used to tell master-tsongkhapa to cite Toh 3861 while its
    meta.json declared five sources and none was it (resolved 2026-09-03 by
    declaring it — see KNOWN_UNDECLARED's history in CHANGELOG.md). The class of
    defect is still real, so this pins it against a synthetic persona rather than
    depending on a live-repo finding that this gate exists to make disappear.
    """
    persona = tmp_path / "master-example"
    (persona / "sources").mkdir(parents=True)
    (persona / "meta.json").write_text(
        '{"name":"x","slug":"example","sources":[{"type":"cbeta","id":"T48n2008",'
        '"title":"t"}]}',
        encoding="utf-8",
    )
    (persona / "SKILL.md").write_text(
        "印度大乘论典所引：【月称《入中论》§第六章】（Toh 3861）", encoding="utf-8"
    )
    found = {(f.master, f.citation) for f in validator.find_undeclared(tmp_path)}
    assert ("master-example", "Toh:3861") in found


def test_the_real_repo_has_no_undeclared_citations_left(validator):
    """Both KNOWN_UNDECLARED findings this gate ever recorded are now declared
    (Toh:3861 in master-tsongkhapa, J36nB348 in master-ouyi), and so are the six
    bare ids it found once it read outside brackets (2026-09-14). A live repo
    with zero real findings should produce zero — this is the gate's own green,
    not a fixture's."""
    found = validator.find_undeclared(ROOT / "prebuilt")
    assert found == []


def test_does_not_flag_format_templates(validator):
    found = {(f.master, f.citation) for f in validator.find_undeclared(ROOT / "prebuilt")}
    assert ("master-milarepa", "BDRC:Wxxxxx") not in found
    assert ("master-zhiyi", "T1716") not in found


def test_findings_name_the_file_so_they_can_be_acted_on(validator):
    for f in validator.find_undeclared(ROOT / "prebuilt"):
        assert f.path and Path(f.path).suffix == ".md"


# --- the gate ---------------------------------------------------------------

def test_known_findings_are_recorded_with_a_reason(validator):
    """A ratchet, not an allowlist: each entry is an open finding awaiting a
    maintainer decision, and it must say so."""
    for key, reason in validator.KNOWN_UNDECLARED.items():
        assert isinstance(key, tuple) and len(key) == 2
        assert len(reason) > 20


def test_gate_passes_while_only_known_findings_are_present(validator):
    assert validator.main() == 0


def test_an_unknown_finding_fails_the_gate(validator, tmp_path):
    persona = tmp_path / "master-fake"
    (persona / "sources").mkdir(parents=True)
    (persona / "meta.json").write_text(
        '{"name":"x","slug":"fake","sources":[{"type":"cbeta","id":"T48n2008",'
        '"title":"t"}]}', encoding="utf-8"
    )
    (persona / "SKILL.md").write_text("引用格式：【《伪经》，T99n9999】", encoding="utf-8")
    found = validator.find_undeclared(tmp_path)
    assert ("master-fake", "T99n9999") in {(f.master, f.citation) for f in found}


# --------------------------------------------------------------------------
# The static sweep shares the same collection-covers-member resolution the
# live judge got in verify_citations.py — a persona's own docs citing a
# collection's declared member by title should not be flagged either.
# --------------------------------------------------------------------------


def test_static_sweep_resolves_a_collection_member_via_its_note(validator, tmp_path):
    persona = tmp_path / "master-example"
    (persona / "sources").mkdir(parents=True)
    (persona / "meta.json").write_text(
        '{"name":"x","slug":"example","sources":['
        '{"type":"compiled_teaching","id":"Ex:Discourses",'
        '"title":"t","note":"Foo Sutta / Bar Sutta 等开示集"}]}',
        encoding="utf-8",
    )
    (persona / "SKILL.md").write_text(
        "开示所引：【《A Discourse on Bar Sutta》】", encoding="utf-8"
    )
    found = {(f.master, f.citation) for f in validator.find_undeclared(tmp_path)}
    assert ("master-example", "Ex:Discourses") not in found
    assert not any(f[0] == "master-example" for f in found)


# --------------------------------------------------------------------------
# Ids outside brackets. A routing table is an instruction too: until
# 2026-09-14 this gate read only 【…】 blocks, and six genuine works cited in
# persona tables and prose had never been declared.
# --------------------------------------------------------------------------

_DECLARES_CHENGWEISHI = (
    '{"name":"x","slug":"example","sources":[{"type":"cbeta","id":"T31n1585",'
    '"title":"t"}]}'
)


def test_finds_an_undeclared_id_in_a_routing_table(validator, tmp_path):
    """master-xuanzang's SKILL.md sent 五位百法 questions to 《百法明门论》
    T31n1614, in a table cell with no brackets, while meta.json never declared
    it."""
    persona = tmp_path / "master-example"
    persona.mkdir()
    (persona / "meta.json").write_text(_DECLARES_CHENGWEISHI, encoding="utf-8")
    (persona / "SKILL.md").write_text(
        "| 五位百法是什么 | `references/teaching.md` | 《百法明门论》，T31n1614 |\n",
        encoding="utf-8",
    )
    found = {(f.master, f.citation) for f in validator.find_undeclared(tmp_path)}
    assert found == {("master-example", "T31n1614")}


def test_a_fojin_link_beside_a_bare_id_does_not_declare_it(validator, tmp_path):
    """master-ouyi's sources/INDEX.md gave 《教觀綱宗》 T46n1939 an excerpt file
    and a FoJin link. In an answer a link can make one citation `live`; in the
    persona's own material a link is not a declaration."""
    persona = tmp_path / "master-example"
    (persona / "sources").mkdir(parents=True)
    (persona / "meta.json").write_text(_DECLARES_CHENGWEISHI, encoding="utf-8")
    (persona / "sources" / "INDEX.md").write_text(
        "| `jiaoguan-gangzong-excerpts.md` | 《教觀綱宗》 | T46n1939 | "
        "[T46n1939](https://fojin.app/texts/8109) |\n",
        encoding="utf-8",
    )
    found = {(f.master, f.citation) for f in validator.find_undeclared(tmp_path)}
    assert found == {("master-example", "T46n1939")}


def test_a_declared_id_in_short_form_outside_brackets_passes(validator, tmp_path):
    """master-zhiyi's frontmatter writes `cbeta_id: T1716` for the declared
    T33n1716 — the same short-form resolution the answer audit uses."""
    persona = tmp_path / "master-example"
    persona.mkdir()
    (persona / "meta.json").write_text(
        '{"name":"x","slug":"example","sources":[{"type":"cbeta","id":"T33n1716",'
        '"title":"t"}]}',
        encoding="utf-8",
    )
    (persona / "SKILL.md").write_text(
        "---\nsources:\n  - title: 妙法蓮華經玄義\n    cbeta_id: T1716\n---\n",
        encoding="utf-8",
    )
    assert validator.find_undeclared(tmp_path) == []


def test_the_sweep_reports_what_it_read(validator):
    """A sweep that reads nothing passes everything. The real repo has ids both
    inside and outside brackets, so both counts must be non-zero."""
    from collections import Counter

    reach = Counter()
    validator.find_undeclared(ROOT / "prebuilt", reach)
    assert reach["bracketed"] > 0
    assert reach["bare"] > 0


def test_a_rule_naming_the_bdrc_field_is_not_an_id(validator, tmp_path):
    """master-tsongkhapa's rules say 不得编造未验证的 BDRC W-number — the name of
    a field, which the auditor's deliberately loose recognizer reads as
    `BDRC:W-number`. A real-shaped undeclared id in prose still fails."""
    persona = tmp_path / "master-example"
    persona.mkdir()
    (persona / "meta.json").write_text(
        '{"name":"x","slug":"example","sources":[{"type":"cbeta","id":"T48n2008",'
        '"title":"t"}]}',
        encoding="utf-8",
    )
    (persona / "SKILL.md").write_text(
        "**NO UNVERIFIED BDRC W-NUMBERS.** 不得编造未验证的 BDRC W-number。\n",
        encoding="utf-8",
    )
    assert validator.find_undeclared(tmp_path) == []

    (persona / "SKILL.md").write_text("所据：BDRC: W12345\n", encoding="utf-8")
    found = {(f.master, f.citation) for f in validator.find_undeclared(tmp_path)}
    assert found == {("master-example", "BDRC:W12345")}


def test_a_citation_by_declared_title_counts_as_read(validator, tmp_path):
    """master-yinguang's Wenchao has no sutra number, so its own docs cite it by
    title. Without the persona's title aliases the sweep could not read those
    citations and silently checked fewer."""
    from collections import Counter

    persona = tmp_path / "master-example"
    persona.mkdir()
    (persona / "meta.json").write_text(
        '{"name":"x","slug":"example","sources":[{"type":"compiled_teaching",'
        '"id":"Ex:Wenchao","title":"某文钞（某文鈔）"}]}',
        encoding="utf-8",
    )
    (persona / "SKILL.md").write_text("出处：【《某文鈔》卷一】\n", encoding="utf-8")
    reach = Counter()
    assert validator.find_undeclared(tmp_path, reach) == []
    assert reach["bracketed"] == 1

