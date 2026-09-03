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
    (Toh:3861 in master-tsongkhapa, J36n0348 in master-ouyi). A live repo with
    zero real findings should produce zero — this is the gate's own green,
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
