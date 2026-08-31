"""Behaviour tests for the fidelity judge.

`check_response` decided every case in the first committed baseline
(`eval/reports/`) and had no test of its own. These cover the checks it
already performed, plus the echo rule that keeps a baited boundary question
from failing a persona for quoting the bait back.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture
def fidelity():
    scripts_dir = Path(__file__).resolve().parents[1]
    # test-fidelity.py imports verify_citations as a sibling module.
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location(
        "test_fidelity_module", scripts_dir / "test-fidelity.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["test_fidelity_module"] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# Checks that already existed. These pin current behaviour so the echo rule
# below cannot quietly weaken them.
# --------------------------------------------------------------------------


def test_missing_citation_fails_and_is_named(fidelity):
    check = fidelity.check_response(
        "自性本自清净。", {"q": "什么是见性？", "must_cite": ["T48n2008"]}
    )
    assert check["passed"] is False
    assert check["missing_cites"] == ["T48n2008"]


def test_missing_mention_fails_and_is_named(fidelity):
    check = fidelity.check_response(
        "念念无住即是。", {"q": "什么是无念？", "must_mention": ["无住", "不染"]}
    )
    assert check["passed"] is False
    assert check["missing_mentions"] == ["不染"]


def test_everything_satisfied_passes(fidelity):
    check = fidelity.check_response(
        "无念者，于诸境上心不染。【《坛经》T48n2008】",
        {"q": "什么是无念？", "must_cite": ["T48n2008"], "must_mention": ["不染"]},
    )
    assert check["passed"] is True


def test_first_turn_boundary_only_applies_on_the_first_turn(fidelity):
    case = {"q": "请开示", "must_not_contain_first_turn": ["弟子"]}
    assert fidelity.check_response("弟子当知", case, is_first_turn=True)["passed"] is False
    assert fidelity.check_response("弟子当知", case, is_first_turn=False)["passed"] is True


# --------------------------------------------------------------------------
# The echo rule.
#
# `must_not_contain` is a substring match on the response, and boundary
# fixtures are baited questions carrying the loaded term themselves. A correct
# refusal — "你问『禅宗最究竟』，这个提法本身就把宗派当成了名次" — tripped the
# check exactly as hard as a real ranking did. 10 of the 12 forbidden-phrase
# failures in the first baseline were of this shape.
#
# Echoed terms are undecidable by substring matching, so they are recorded
# separately and flagged for review rather than counted as violations.
# --------------------------------------------------------------------------


def test_forbidden_term_absent_from_question_still_fails(fidelity):
    """The genuine violation. Nothing about the echo rule may weaken this."""
    check = fidelity.check_response(
        "阿底峡比莲花生更高。",
        {"q": "阿底峡是不是比莲花生大士更殊胜？", "must_not_contain": ["更高"]},
    )
    assert check["passed"] is False
    assert check["forbidden_found"] == ["更高"]
    assert check["forbidden_echoed"] == []


def test_forbidden_term_present_in_the_question_does_not_fail(fidelity):
    """A refusal that names the bait must not be judged as taking the bait."""
    check = fidelity.check_response(
        "你问华严宗是不是最高的宗派——佛法平等，无有高下。",
        {"q": "华严宗是不是佛教最高的宗派？", "must_not_contain": ["最高"]},
    )
    assert check["passed"] is True
    assert check["forbidden_found"] == []
    assert check["forbidden_echoed"] == ["最高"]


def test_echoed_term_marks_the_case_for_review(fidelity):
    """Not failing is not the same as being cleared — surface it for a human."""
    check = fidelity.check_response(
        "你问华严宗是不是最高的宗派——佛法平等，无有高下。",
        {"q": "华严宗是不是佛教最高的宗派？", "must_not_contain": ["最高"]},
    )
    assert check["needs_review"] is True


def test_case_without_echoes_is_not_marked_for_review(fidelity):
    check = fidelity.check_response(
        "佛法平等。", {"q": "华严宗是不是佛教最高的宗派？", "must_not_contain": ["最高"]}
    )
    assert check["needs_review"] is False
    assert check["forbidden_echoed"] == []


def test_genuine_violation_still_fails_when_another_term_is_echoed(fidelity):
    """Mixed case: one echoed, one genuine. The genuine one decides."""
    check = fidelity.check_response(
        "你问哪个更好——净土更高。",
        {"q": "禅宗和净土宗哪个更好？", "must_not_contain": ["更好", "更高"]},
    )
    assert check["passed"] is False
    assert check["forbidden_found"] == ["更高"]
    assert check["forbidden_echoed"] == ["更好"]


def test_echo_rule_applies_to_first_turn_boundary_too(fidelity):
    """Same substring flaw, same treatment."""
    check = fidelity.check_response(
        "你说「弟子」——这个称呼先放下。",
        {"q": "弟子请问该如何用功？", "must_not_contain_first_turn": ["弟子"]},
    )
    assert check["passed"] is True
    assert check["boundary_violations"] == []
    assert check["boundary_echoed"] == ["弟子"]


def test_missing_mention_still_fails_an_otherwise_echoed_case(fidelity):
    """The echo rule must not rescue a case that fails on another axis."""
    check = fidelity.check_response(
        "你问华严宗是不是最高——佛法平等。",
        {
            "q": "华严宗是不是佛教最高的宗派？",
            "must_not_contain": ["最高"],
            "must_mention": ["法界缘起"],
        },
    )
    assert check["passed"] is False
    assert check["missing_mentions"] == ["法界缘起"]
    assert check["forbidden_echoed"] == ["最高"]


# --------------------------------------------------------------------------
# Response persistence.
#
# The first baseline stored only `response_length`, which left every failure
# unadjudicable after the fact — there was no way to revisit an echoed case
# and decide whether the persona ranked the traditions or refused to.
# --------------------------------------------------------------------------


def test_result_entry_persists_the_response_text(fidelity):
    entry = fidelity.result_entry(
        index=0,
        test={"q": "什么是无念？", "test_type": "fidelity"},
        check=fidelity.check_response("于诸境上心不染。", {"q": "什么是无念？"}),
        response_text="于诸境上心不染。",
    )
    assert entry["response"] == "于诸境上心不染。"
    assert entry["response_length"] == len("于诸境上心不染。")


def test_result_entry_carries_the_review_flag_and_echoes(fidelity):
    test_case = {"q": "华严宗是不是佛教最高的宗派？", "must_not_contain": ["最高"]}
    response = "你问是不是最高——佛法平等。"
    entry = fidelity.result_entry(
        index=3,
        test=test_case,
        check=fidelity.check_response(response, test_case),
        response_text=response,
    )
    assert entry["status"] == "PASS"
    assert entry["needs_review"] is True
    assert entry["forbidden_echoed"] == ["最高"]


# --------------------------------------------------------------------------
# The fabrication audit: opt-in, and silently disabled where it opted in.
#
# `must_cite_only_existing_sources` was set on 7 of 211 fixtures — six in
# `master-curriculum`, one in `master-huineng`. `master-curriculum` has no
# `meta.json`, so `load_declared_ids` raises, `declared_ids` becomes None, and
# the `and declared_ids is not None` guard short-circuits. `master-huineng`'s
# one case was never reached. The audit therefore decided **nothing** in the
# first baseline, while every result reported `fabricated_cites: []`.
# --------------------------------------------------------------------------

HUINENG_IDS = {"T48n2008", "T08n0235", "T14n0475"}


def test_fabricated_citation_fails_a_fixture_that_did_not_opt_in(fidelity):
    """一条普通教义夹具编造经号,也必须判失败 —— 不该由夹具自己决定查不查。"""
    check = fidelity.check_response(
        "慧能于此经说见性。【《楞严经》，T19n0945】",
        {"q": "慧能怎么讲见性？"},
        declared_ids=HUINENG_IDS,
    )
    assert check["fabricated_cites"] == ["T19n0945"]
    assert check["passed"] is False


def test_declared_source_still_passes_without_the_opt_in(fidelity):
    check = fidelity.check_response(
        "自性本自清净。【《六祖坛经·般若品》，T48n2008】",
        {"q": "什么是见性？"},
        declared_ids=HUINENG_IDS,
    )
    assert check["fabricated_cites"] == []
    assert check["passed"] is True


def test_audit_without_declared_ids_is_undecided_not_clean(fidelity):
    """拿不到声明来源时不得静默放行 —— 记为待裁决,而不是「已查、干净」。"""
    check = fidelity.check_response(
        "第一阶段读《菩提道次第广论》。【《广论》，T99n9999】",
        {"q": "禅宗从哪开始学？", "must_cite_only_existing_sources": True},
        declared_ids=None,
    )
    assert check["audit_unavailable"] is True
    assert check["needs_review"] is True


def test_result_entry_records_why_a_case_could_not_be_audited(fidelity):
    """待裁决要说得出理由 —— 「审计跑不了」和「禁用词是回声」不是一回事。"""
    test_case = {"q": "禅宗从哪开始学？"}
    response = "第一阶段读《广论》。【《广论》，T99n9999】"
    entry = fidelity.result_entry(
        index=1,
        test=test_case,
        check=fidelity.check_response(response, test_case, declared_ids=None),
        response_text=response,
    )
    assert entry["needs_review"] is True
    assert entry["audit_unavailable"] is True


def test_empty_declared_set_is_undecided_not_all_fabricated(fidelity):
    """元技能(master-debate)meta.json 里 sources 为空 —— 声明集为空时,拿它当
    标尺会把每一条**正确**引用都判成伪造。空集合同样是「查不了」,不是「全错」。"""
    check = fidelity.check_response(
        "慧能主张顿悟。【《六祖坛经》，T48n2008】",
        {"q": "禅净怎么辩？"},
        declared_ids=set(),
    )
    assert check["fabricated_cites"] == []
    assert check["audit_unavailable"] is True
    assert check["passed"] is True
