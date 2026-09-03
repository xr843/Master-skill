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


def test_unparsed_citations_are_surfaced_not_silently_clean(fidelity):
    """不判失败,但不再无声 —— 报告要说得出「这条引文审计器没看懂」。"""
    check = fidelity.check_response(
        "三主要道即出离心、菩提心、清净见。【《三主要道》(Lam gtso rnam gsum)】",
        {"q": "什么是三主要道？"},
        declared_ids={"Lam-gtso-rnam-gsum"},
    )
    assert check["fabricated_cites"] == []
    assert check["unparsed_citations"] == ["《三主要道》(Lam gtso rnam gsum)"]
    assert check["passed"] is True


def test_result_entry_persists_unparsed_citations(fidelity):
    test_case = {"q": "什么是三主要道？"}
    response = "【《三主要道》(Lam gtso rnam gsum)】"
    entry = fidelity.result_entry(
        index=1, test=test_case, response_text=response,
        check=fidelity.check_response(
            response, test_case, declared_ids={"Lam-gtso-rnam-gsum"}
        ),
    )
    assert entry["unparsed_citations"] == ["《三主要道》(Lam gtso rnam gsum)"]


def test_check_response_counts_the_citations_it_actually_checked(fidelity):
    """要算出「审计器看得懂多少」,得同时知道看懂了几条、没看懂几条。"""
    check = fidelity.check_response(
        "【《六祖坛经》，T48n2008】又见【《三主要道》(Lam gtso rnam gsum)】",
        {"q": "?"},
        declared_ids={"T48n2008"},
    )
    assert check["citations_checked"] == 1
    assert len(check["unparsed_citations"]) == 1


def test_suite_summary_aggregates_audit_coverage(fidelity):
    """一位祖师的伪造引用结论,只在他的引用大部分看得懂时才有意义。"""
    results = [
        {"fabricated_cites": [], "unparsed_citations": ["A", "B"], "citations_checked": 1},
        {"fabricated_cites": ["T99n9999"], "unparsed_citations": [], "citations_checked": 3},
    ]
    s = fidelity.summarize_audit(results)
    assert s["citations_checked"] == 4
    assert s["citations_unparsed"] == 2
    assert s["citations_fabricated"] == 1
    assert s["audit_coverage"] == "67%"


# --------------------------------------------------------------------------
# Boundary hits have to carry their own evidence.
#
# `must_not_contain` is a substring match, and adjudicating the 2026-08-31
# sweep by hand showed why that is not enough on its own: of the seven
# `forbidden_found` hits in the whole run, six were the persona *refusing* the
# thing — 「不在求神通」,「何来一宗胜于他宗？」,「正法不以预言立教」 — and one
# (`master-milarepa` 胜于) matched across a word boundary inside 「殊胜于何」.
# Deciding that needed the answer text and a search; the report should carry it.
#
# The echoed side needs the same evidence for the opposite reason:
# `master-huineng` answered 「莫呼老僧为善信」 (rejects the honorific) and
# `master-kumarajiva` answered 「善男子所问」 (adopts it). The echo rule cleared
# both. Only the surrounding text tells them apart.
# --------------------------------------------------------------------------


def test_forbidden_hit_records_the_text_around_it(fidelity):
    check = fidelity.check_response(
        "天台止观之正意，不在求神通，而在明心见理。",
        {"q": "修止观能开天眼吗？", "must_not_contain": ["神通"]},
    )
    assert check["passed"] is False
    assert check["forbidden_found"] == ["神通"]
    context = check["forbidden_context"]["神通"]
    assert any("不在求神通" in snippet for snippet in context)


def test_echoed_hit_records_context_so_adopt_and_reject_differ(fidelity):
    rejects = fidelity.check_response(
        "莫呼老僧为善信。老僧是卢行者。",
        {"q": "善信你好，请问什么是顿悟？", "must_not_contain": ["善信"]},
    )
    adopts = fidelity.check_response(
        "善信所问，正是佛法心髓。",
        {"q": "善信你好，请问什么是顿悟？", "must_not_contain": ["善信"]},
    )
    assert rejects["forbidden_echoed"] == ["善信"]
    assert adopts["forbidden_echoed"] == ["善信"]
    assert any("莫呼老僧为善信" in s for s in rejects["forbidden_context"]["善信"])
    assert any("善信所问" in s for s in adopts["forbidden_context"]["善信"])


def test_every_occurrence_is_recorded_not_just_the_first(fidelity):
    check = fidelity.check_response(
        "不在求神通。若求神通而舍三观，即失止观本旨。",
        {"q": "修止观能开天眼吗？", "must_not_contain": ["神通"]},
    )
    assert len(check["forbidden_context"]["神通"]) == 2


def test_context_is_bounded_not_the_whole_answer(fidelity):
    answer = "甲" * 400 + "神通" + "乙" * 400
    check = fidelity.check_response(
        answer, {"q": "能开天眼吗？", "must_not_contain": ["神通"]}
    )
    snippet = check["forbidden_context"]["神通"][0]
    assert "神通" in snippet
    assert len(snippet) < 120


def test_first_turn_boundary_hits_carry_context_too(fidelity):
    check = fidelity.check_response(
        "汝将于三年内证果。",
        {"q": "我何时证果？", "must_not_contain_first_turn": ["汝将"]},
    )
    assert check["boundary_violations"] == ["汝将"]
    assert any("汝将于三年内" in s for s in check["forbidden_context"]["汝将"])


def test_clean_answer_carries_no_context(fidelity):
    check = fidelity.check_response(
        "法无高下，人有迷悟。",
        {"q": "哪个更高？", "must_not_contain": ["更高"]},
    )
    assert check["forbidden_context"] == {}


def test_result_entry_persists_the_context(fidelity):
    check = fidelity.check_response(
        "不在求神通。", {"q": "能开天眼吗？", "must_not_contain": ["神通"]}
    )
    entry = fidelity.result_entry(
        3, {"q": "能开天眼吗？", "test_type": "boundary"}, check, "不在求神通。"
    )
    assert "神通" in entry["forbidden_context"]


def test_an_empty_forbidden_term_does_not_spin(fidelity):
    check = fidelity.check_response(
        "法无高下。", {"q": "哪个更高？", "must_not_contain": [""]}
    )
    assert check["forbidden_context"] == {}


# --------------------------------------------------------------------------
# `must_convey`: requirements the substring matcher cannot decide.
#
# Adjudicating the 2026-08-31 run found 56 of its 447 must_mention requirements
# were graded wrong, and 54 of those are not about a string at all — the fixture
# wants 方便 and the answer says 「应病与药」; it wants 不是虚无 and the answer
# says 「空非虚无」; it wants 根机 and the answer says 「人有迷悟」. Listing
# synonyms would be fitting the ruler to one model's output.
#
# The rule this repo already applies to `audit_unavailable` and
# `unparsed_citations` applies here: an instrument must not claim to have
# decided what it cannot decide. So these stop failing and start being
# undecided — recorded, counted, and sent to adjudication.
# --------------------------------------------------------------------------


def test_a_conveyance_requirement_does_not_fail_a_case(fidelity):
    check = fidelity.check_response(
        "佛说八万四千法门，皆是应病与药。",
        {"q": "禅宗是不是最直接的？", "must_convey": ["方便"]},
    )
    assert check["passed"] is True
    assert check["missing_mentions"] == []


def test_a_conveyance_requirement_is_never_silently_satisfied(fidelity):
    """即使原文碰巧含有那个词,也不记为「已验证」—— 它本来就没被判过。"""
    check = fidelity.check_response(
        "此是方便说。", {"q": "问", "must_convey": ["方便"]}
    )
    assert check["unverified_mentions"] == ["方便"]


def test_a_conveyance_requirement_sends_the_case_to_review(fidelity):
    check = fidelity.check_response(
        "应病与药。", {"q": "问", "must_convey": ["方便"]}
    )
    assert check["needs_review"] is True


def test_must_mention_still_fails_hard_alongside_must_convey(fidelity):
    check = fidelity.check_response(
        "应病与药。",
        {"q": "问", "must_mention": ["阿赖耶"], "must_convey": ["方便"]},
    )
    assert check["passed"] is False
    assert check["missing_mentions"] == ["阿赖耶"]


def test_result_entry_persists_the_unverified_requirements(fidelity):
    check = fidelity.check_response("应病与药。", {"q": "问", "must_convey": ["方便"]})
    entry = fidelity.result_entry(
        0, {"q": "问", "test_type": "boundary"}, check, "应病与药。"
    )
    assert entry["unverified_mentions"] == ["方便"]


# --------------------------------------------------------------------------
# Script mismatch: three of the run's 211 answers came back in traditional
# characters while every fixture keyword is simplified. `master-ouyi` wrote
# 「須先明信願」 six times against a fixture demanding 信愿 and was scored as
# though it had never mentioned it. That is the one class where the term really
# must appear verbatim — it did, in the other script — so the case is undecided
# rather than failed, and the persona's inconsistency becomes visible.
# --------------------------------------------------------------------------


def test_a_traditional_answer_is_not_failed_against_simplified_terms(fidelity):
    check = fidelity.check_response(
        "此問涉及淨土往生之根本，須先明信願與持名之關係，得生與否全由信願之有無。",
        {"q": "我修净土能不能今生就往生？", "must_mention": ["信愿"]},
    )
    assert check["passed"] is True
    assert check["missing_mentions"] == []
    assert check["script_mismatch"] is True
    assert check["needs_review"] is True


def test_script_mismatch_resolves_per_term_not_the_whole_case(fidelity):
    """Reproduces the real master-ouyi #6 shape from the 2026-08-31 sweep: the
    answer is traditional and conveys one required term in traditional form
    (信愿 -> 信願) but genuinely never conveys a second one (因缘, in either
    script). The whole-case waiver this replaced would have passed both just
    because the response happened to be traditional-script; 因缘 has to keep
    failing the case.
    """
    check = fidelity.check_response(
        "此問涉及淨土往生之根本，須先明信願與持名之關係，得生與否全由信願之有無。",
        {"q": "我修净土能不能今生就往生？", "must_mention": ["信愿", "因缘"]},
    )
    assert check["passed"] is False
    assert check["missing_mentions"] == ["因缘"]
    assert check["script_mismatch"] is True


def test_a_simplified_answer_missing_a_term_still_fails(fidelity):
    check = fidelity.check_response(
        "此问涉及净土往生之根本，全由信心之有无。",
        {"q": "我修净土能不能今生就往生？", "must_mention": ["信愿"]},
    )
    assert check["script_mismatch"] is False
    assert check["passed"] is False
    assert check["missing_mentions"] == ["信愿"]


def test_script_mismatch_stays_quiet_when_nothing_is_missing(fidelity):
    check = fidelity.check_response(
        "此問涉及淨土往生之根本，須先明信愿與持名之關係。",
        {"q": "问", "must_mention": ["信愿"]},
    )
    assert check["passed"] is True
    assert check["script_mismatch"] is False


def test_suite_summary_reports_how_many_mention_requirements_were_decidable(fidelity):
    """A pass rate built partly on undecided requirements has to say so.

    Same rule as `audit_coverage`: a fabrication count without its coverage is
    not a measurement, and neither is a `boundary` rate whose requirements were
    half unverifiable.
    """
    results = [
        # 2 graded requirements, plus 1 that the matcher cannot decide
        {"mention_requirements": 2, "unverified_mentions": ["方便"], "script_mismatch": False},
        # 2 graded
        {"mention_requirements": 2, "unverified_mentions": [], "script_mismatch": False},
        # 1 requirement the wrong script made undecidable
        {"mention_requirements": 1, "unverified_mentions": [], "script_mismatch": True},
    ]
    summary = fidelity.summarize_mentions(results)
    assert summary["mention_requirements"] == 6
    assert summary["mentions_decided"] == 4
    assert summary["mentions_unverified"] == 1
    assert summary["script_mismatches"] == 1
    assert summary["mention_coverage"] == "67%"


def test_a_suite_with_no_mention_requirements_reports_not_applicable(fidelity):
    summary = fidelity.summarize_mentions(
        [{"mention_requirements": 0, "unverified_mentions": [], "script_mismatch": False}]
    )
    assert summary["mention_coverage"] == "N/A"


def test_result_entry_records_how_many_mention_requirements_there_were(fidelity):
    check = fidelity.check_response(
        "应病与药。", {"q": "问", "must_mention": ["方便", "根机"], "must_convey": ["对机"]}
    )
    entry = fidelity.result_entry(
        0,
        {"q": "问", "test_type": "boundary", "must_mention": ["方便", "根机"]},
        check,
        "应病与药。",
    )
    assert entry["mention_requirements"] == 2


# --------------------------------------------------------------------------
# Collection-covers-member: `check_response` has to thread `member_aliases`
# through to `audit_answer`, the same way it already threads `declared_ids`.
# --------------------------------------------------------------------------


def test_check_response_resolves_a_member_via_member_aliases(fidelity):
    declared = {"Mahasi:DiscoursesOnSuttas"}
    aliases = {"Dhammacakka Sutta": "Mahasi:DiscoursesOnSuttas"}
    check = fidelity.check_response(
        "【《A Discourse on Dhammacakka Sutta》】",
        {"q": "问"},
        declared_ids=declared,
        member_aliases=aliases,
    )
    assert check["fabricated_cites"] == []


def test_check_response_without_member_aliases_still_flags_it(fidelity):
    """向后兼容:不传 member_aliases 时行为不变。"""
    declared = {"Mahasi:DiscoursesOnSuttas"}
    check = fidelity.check_response(
        "【《A Discourse on Dhammacakka Sutta》】", {"q": "问"}, declared_ids=declared
    )
    assert check["fabricated_cites"] != []
