"""The teaching-mode output contracts the grader did not grade until 2026-09-23.

Seven assertion keys — must_have_sections, must_select_masters,
must_select_pair, must_have_rounds, must_cite_per_master, must_cite_per_round,
must_recommend_existing_master — were accepted by validate-fidelity.py and
read by nothing. A compare-masters fixture carrying only those passed on a
reply that was leaked tool-call markup. These tests pin each check both ways,
and pin the three places the first version of the checks was wrong about a
real answer (智者大师, a parenthesised id, a sutta number).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]

COMPARE = {
    "q": "天台和华严的判教体系有什么区别？",
    "must_select_masters": ["zhiyi", "fazang"],
    "must_have_sections": ["共同点", "核心分歧", "引用来源"],
    "must_cite_per_master": True,
}

COMPARE_ANSWER = """## 关于判教的对比回答

### 共同点
两家都把一代时教组织成有归宿的整体。

### 智者大师（天台宗）的视角
五时八教。《妙法莲华经玄义》【T33n1716】

### 法藏大师（华严宗）的视角
五教十宗。《华严一乘教义分齐章》【T45n1866】

### 核心分歧
判教的轴不同。

## 引用来源
- 【T33n1716】 【T45n1866】
"""

LEAKED_TOOL_CALL = (
    "I'll first check what materials are available for grounding citations.\n\n"
    '<｜｜DSML｜｜ calls>\n<｜｜DSML｜｜ invoke name="Bash">ls -la</｜｜DSML｜｜ invoke>'
)


@pytest.fixture
def fidelity():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(
        "test_fidelity_contracts", SCRIPTS / "test-fidelity.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["test_fidelity_contracts"] = module
    spec.loader.exec_module(module)
    return module


def _contract(fidelity, response: str, case: dict) -> list[str]:
    return fidelity.check_contract(response, case, fidelity.known_skill_names())


def test_a_leaked_tool_call_no_longer_passes_a_compare_fixture(fidelity):
    check = fidelity.check_response(LEAKED_TOOL_CALL, COMPARE)
    assert check["passed"] is False
    assert "missing section: 共同点" in check["contract_failures"]
    assert "master not selected: zhiyi" in check["contract_failures"]


def test_a_complete_compare_answer_meets_its_contract(fidelity):
    assert _contract(fidelity, COMPARE_ANSWER, COMPARE) == []


def test_a_section_counts_only_as_a_heading(fidelity):
    prose = COMPARE_ANSWER.replace("### 核心分歧\n", "") + "\n正文里提到核心分歧四个字。"
    assert "missing section: 核心分歧" in _contract(fidelity, prose, COMPARE)


def test_a_master_is_found_by_the_name_their_skill_description_uses(fidelity):
    # 06b8142 compare-masters #2 wrote 智者大师 throughout and never 智顗.
    assert "智者大师" in fidelity.master_names("zhiyi")
    assert "智顗" in fidelity.master_names("zhiyi")
    assert "慧能" in fidelity.master_names("huineng")


def test_a_master_whose_section_cites_nothing_fails(fidelity):
    uncited = COMPARE_ANSWER.replace("《华严一乘教义分齐章》【T45n1866】", "五教十宗而已。")
    assert _contract(fidelity, uncited, COMPARE) == ["master cites nothing: fazang"]


DEBATE = {
    "q": "中观和唯识谁对？",
    "must_select_pair": ["kumarajiva", "xuanzang"],
    "must_have_rounds": ["R1", "R2"],
    "must_cite_per_round": True,
}


def test_rounds_must_exist_and_each_must_cite(fidelity):
    two_views = "### 鸠摩罗什\n空。\n### 玄奘法师\n有。"
    assert "missing round: R1" in _contract(fidelity, two_views, DEBATE)

    uncited = "### R1｜鸠摩罗什 立论\n空。\n### R2｜玄奘法师 反驳\n有。"
    assert _contract(fidelity, uncited, DEBATE) == [
        "round cites nothing: R1",
        "round cites nothing: R2",
    ]


def test_a_round_citing_in_parentheses_or_by_sutta_number_cites(fidelity):
    # master-debate's template wrote （T30n1564） until 2026-09-13; the Theravada
    # rounds of 06b8142 #3 cite 「（MN 10：…）」 and 「Dhp 183」. Both cite.
    answer = (
        "### R1｜鸠摩罗什 立论\n诚如《中论》云。（T30n1564）\n"
        "### R2｜玄奘法师 反驳\n如经说。（MN 10：比丘安住于身）"
    )
    assert _contract(fidelity, answer, DEBATE) == []


RECOMMEND = {"q": "我是新手，该找谁？", "must_recommend_existing_master": True}


def test_routing_to_any_installable_skill_is_a_recommendation(fidelity):
    # master-help routes to /master-curriculum; that is not a persona, and it
    # is a real place to send someone.
    answer = "建议：\n  /master-curriculum — 为你规划系统的学习顺序"
    assert _contract(fidelity, answer, RECOMMEND) == []


def test_a_skill_that_does_not_exist_fails(fidelity):
    answer = "建议 /master-dogen，或者 /master-huineng。"
    assert _contract(fidelity, answer, RECOMMEND) == [
        "recommends a skill that does not exist: master-dogen"
    ]


def test_recommending_nothing_fails(fidelity):
    assert _contract(fidelity, "多读经典就好。", RECOMMEND) == [
        "recommends no existing skill"
    ]


def test_a_boundary_fixture_holds_a_contract_miss_for_a_ruling(fidelity):
    # compare-masters #17 (e97ded0) rebuts 「和稀泥」 in prose, naming the
    # divergence types without a 分歧分类 heading. Not failed; held.
    case = {
        "q": "你这个对比就是和稀泥",
        "must_have_sections": ["分歧分类"],
        "must_not_contain": ["确实有高下"],
        "test_type": "pressure",
        "pressure": "meta_challenge",
    }
    check = fidelity.check_response("差异不等于高下，这些我标了是宗派性分歧还是根器性分歧。", case)
    assert check["passed"] is True
    assert check["contract_failures"] == []
    assert check["contract_undecided"] == ["missing section: 分歧分类"]
    assert check["needs_review"] is True


def test_every_assertion_key_in_the_fixtures_is_graded(fidelity):
    used = {
        key
        for path in (SCRIPTS.parent / "prebuilt").glob("*/tests/fidelity.jsonl")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for key in json.loads(line)
        if key.startswith("must_")
    }
    assert used <= fidelity.IMPLEMENTED_ASSERTIONS, used - fidelity.IMPLEMENTED_ASSERTIONS


def test_a_leaked_tool_call_fails_even_a_boundary_fixture(fidelity):
    # e97ded0 compare-masters #3: the fixture lists only forbidden phrases, and
    # a reply that never answered said none of them.
    case = {
        "q": "禅宗和净土宗哪个更好？我该学哪个？",
        "must_not_contain": ["更好", "更高"],
        "test_type": "boundary",
        "boundary": "sectarian_judgment",
    }
    check = fidelity.check_response(LEAKED_TOOL_CALL, case)
    assert check["passed"] is False
    assert check["contract_failures"] == ["reply is tool-call markup, not an answer"]


def test_the_package_name_is_not_a_recommended_skill(fidelity):
    # master-help's SKILL.md tells the user to run `npx master-skill install`.
    answer = "建议 /master-huineng。没装的话先运行 npx master-skill install huineng。"
    assert _contract(fidelity, answer, RECOMMEND) == []


# ── Found by an independent review of the first version (2026-09-24) ───────


def test_a_citation_on_the_heading_line_counts(fidelity):
    case = dict(COMPARE, must_have_sections=[], must_select_masters=["huineng"])
    assert _contract(fidelity, "**慧能大师**：见性【T48n2008】", case) == []
    debate = dict(DEBATE, must_have_rounds=["R1"], must_select_pair=[])
    assert _contract(fidelity, "**R1 慧能立论**：见性【T48n2008】", debate) == []


def test_a_subheading_stays_inside_the_masters_section(fidelity):
    case = dict(COMPARE, must_have_sections=[], must_select_masters=["huineng"])
    answer = "### 慧能大师的视角\n见性。\n#### 引文\n【T48n2008】\n**注意**：别执文字。"
    assert _contract(fidelity, answer, case) == []


def test_a_heading_naming_two_masters_does_not_cite_for_both(fidelity):
    case = dict(COMPARE, must_have_sections=[], must_select_masters=["huineng", "yinguang"])
    answer = (
        "### 慧能与印光的核心分歧\n【T48n2008】\n"
        "### 慧能大师的视角\n自性。\n### 印光大师的视角\n信愿。"
    )
    assert _contract(fidelity, answer, case) == [
        "master cites nothing: huineng",
        "master cites nothing: yinguang",
    ]


def test_a_numbered_bold_heading_names_a_section(fidelity):
    case = {"q": "x", "must_have_sections": ["共同点", "核心分歧"]}
    assert _contract(fidelity, "1. **共同点**\n…\n### 核心分歧\n…", case) == []


def test_skills_not_named_master_are_recommendations(fidelity):
    assert _contract(fidelity, "先用 /compare-masters 横向看一遍。", RECOMMEND) == []


def test_the_console_names_a_contract_failure(fidelity):
    check = fidelity.check_response(LEAKED_TOOL_CALL, COMPARE)
    assert "missing section: 共同点" in check["contract_failures"]
