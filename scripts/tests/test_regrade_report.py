"""Re-grading a committed run against the current judge and fixtures, offline.

`check_response` is deterministic and every answer since PR #142 is stored, so
any change to the judge or the fixtures can be measured against an
already-paid-for run for nothing. Without that, a change like `must_convey`
could only claim an effect.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent


@pytest.fixture
def mod():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(
        "regrade_report", SCRIPTS / "regrade-report.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["regrade_report"] = module
    spec.loader.exec_module(module)
    return module


def _report(question: str, response: str, status: str = "FAIL") -> dict:
    return {
        "meta": {"commit_short": "abc1234", "model": "test-model"},
        "suites": [
            {
                "master": "master-nagarjuna",
                "results": [
                    {
                        "index": 0,
                        "question": question,
                        "test_type": "fidelity",
                        "status": status,
                        "response": response,
                    }
                ],
            }
        ],
    }


def test_regrading_joins_results_to_fixtures_by_question_not_position(mod):
    """夹具增删会让下标全线错位,而错位后每一条都会被拿错题去判。"""
    report = _report("这道题夹具里没有", "随便什么回答")
    out = mod.regrade(report, {"master-nagarjuna": [{"q": "另一道题", "must_mention": ["x"]}]})
    assert out["cases"] == []
    assert out["unmatched"] == ["master-nagarjuna #0"]


def test_a_shifted_fixture_is_still_found_by_its_question(mod):
    """A fixture inserted before it moves the index, not the question."""
    fixtures = {"master-nagarjuna": [{"q": "新插入的题"}, {"q": "问", "must_mention": ["阿赖耶"]}]}
    out = mod.regrade(_report("问", "因缘所生法。"), fixtures)
    assert out["unmatched"] == []
    assert out["cases"][0]["now"] == "FAIL"


def test_a_migrated_requirement_stops_failing_and_starts_needing_review(mod):
    fixtures = {"master-nagarjuna": [{"q": "问", "must_convey": ["缘起"]}]}
    out = mod.regrade(_report("问", "因缘所生法，我说即是空。"), fixtures)
    case = out["cases"][0]
    assert case["was"] == "FAIL"
    assert case["now"] == "PASS"
    assert case["needs_review"] is True


def test_a_requirement_still_graded_still_fails(mod):
    fixtures = {"master-nagarjuna": [{"q": "问", "must_mention": ["阿赖耶"]}]}
    out = mod.regrade(_report("问", "因缘所生法。"), fixtures)
    assert out["cases"][0]["now"] == "FAIL"


def test_truncated_results_are_left_unmeasured(mod):
    report = _report("问", "被截断的回答", status="truncated")
    out = mod.regrade(report, {"master-nagarjuna": [{"q": "问", "must_mention": ["x"]}]})
    assert out["cases"] == []


def test_tallies_are_reported_per_test_type(mod):
    fixtures = {"master-nagarjuna": [{"q": "问", "must_convey": ["缘起"]}]}
    out = mod.regrade(_report("问", "因缘所生。"), fixtures)
    assert out["by_test_type"]["fidelity"] == {"graded": 1, "was": 0, "now": 1}


def test_a_report_without_stored_answers_is_refused(mod):
    report = _report("问", "")
    del report["suites"][0]["results"][0]["response"]
    with pytest.raises(ValueError, match="no stored answers"):
        mod.regrade(report, {"master-nagarjuna": [{"q": "问"}]})


def test_the_committed_run_regrades_against_the_repository_as_it_stands(mod):
    report = json.loads(
        (ROOT / "eval/reports/0.11.0-06b8142-deepseek.json").read_text()
    )
    out = mod.regrade(report, mod.load_fixtures())
    # 迁移只放宽,不收紧。PR #146 给审计器补上编集开示家族之后,马哈希 #12 引用的
    # 《A Discourse on Dhammacakka Sutta》曾第一次变得可读、但判成伪造(那次跑自己
    # 的审计器根本看不见它,所以是真发现)。2026-09-03 的维护者决定是「合集覆盖
    # 成员」——`Mahasi:DiscoursesOnSuttas` 的 note 早就点了这篇的名 —— 实现之后
    # 这条不再是回归。钉住「零回归」,任何新出现的都会立刻现形。
    regressions = [
        (c["master"], c["index"])
        for c in out["cases"]
        if c["was"] == "PASS" and c["now"] == "FAIL"
    ]
    # Two regressions, and both are findings. master-curriculum #1 recommended
    # X62n1182–1184 as 《印光法师文钞》. They are three other Qing works, and the
    # case passed only while master-yinguang declared the same wrong ids
    # (corrected 2026-09-14). master-fazang #3 asks about 《金师子章》 and its
    # stored answer cites T45n1866, 《华严一乘教义分齐章》, which does not contain
    # that text (checked fascicle by fascicle, 2026-09-15). The fixture had
    # required the same wrong id; it now requires T45n1880, where the text is
    # preserved. master-milarepa #0, #2-#5 and #7-#9 are findings of the same
    # kind. The persona declared BDRC:W22272, which is Tsongkhapa's collected
    # works, for the Life of Milarepa, and BDRC:W1KG14334, which is not a BDRC
    # record at all, for the Songs. The stored answers cite both, so they passed
    # only while the persona carried the wrong ids (corrected 2026-09-15). The
    # fixtures now require W1GS56158 and W1KG1252. The boundary cases #5, #7 and
    # #8 have no must_cite; they fail because the audit now reads the old ids
    # as undeclared.
    #
    # master-debate #0 and #2 fail since the teaching-mode contracts were
    # graded (2026-09-23), and both were read before being listed here. #0
    # answers as two side-by-side views with no R1–R4 at all, where the
    # template requires 「### R1｜…」 rounds. In #2, rounds R1, R2 and R4 name
    # no source of any kind — no id, no title; only R3 cites. Any other
    # regression still fails here.
    assert regressions == [
        ("master-curriculum", 1),
        ("master-debate", 0),
        ("master-debate", 2),
        ("master-fazang", 3),
        ("master-milarepa", 0),
        ("master-milarepa", 2),
        ("master-milarepa", 3),
        ("master-milarepa", 4),
        ("master-milarepa", 5),
        ("master-milarepa", 7),
        ("master-milarepa", 8),
        ("master-milarepa", 9),
    ], regressions
    assert out["mentions"]["mention_coverage"].endswith("%")
    # Asked without the L0–L3 level their skill requires (「缺则反问」), so the
    # right answer was a question back, while the fixture required the full
    # four-stage plan. The questions now state a level; the stored answers
    # were to the old ones and are not graded against the new.
    assert out["unmatched"] == ["master-curriculum #3", "master-curriculum #4"]


def test_api_error_rows_are_not_graded_as_a_hard_fail(mod):
    """Found by an independent code-review pass (2026-09-03): only
    `status == 'truncated'` was excluded, so an api_error row (which by
    design carries no `response` key) fell through to `response or ''` and
    was silently regraded against real must_mention/must_cite requirements —
    an empty answer satisfies none of them, so the row landed in `now: FAIL`
    and corrupted the pass-rate tally with a case that was never actually
    answered.
    """
    fixtures = {
        "master-nagarjuna": [
            {"q": "已答的问题", "must_mention": ["缘起"]},
            {"q": "问", "must_mention": ["缘起"]},
        ]
    }
    report = {
        "meta": {"commit_short": "abc1234", "model": "test-model"},
        "suites": [
            {
                "master": "master-nagarjuna",
                "results": [
                    {
                        "index": 0,
                        "question": "已答的问题",
                        "test_type": "fidelity",
                        "status": "PASS",
                        "response": "因缘所生法。",
                    },
                    {
                        "index": 1,
                        "question": "问",
                        "test_type": "fidelity",
                        "status": "api_error",
                        "error": "boom",
                    },
                ],
            }
        ],
    }
    out = mod.regrade(report, fixtures)
    # index 0(真答案)照常判;index 1(api_error,没答)完全不计入 cases。
    assert [(c["master"], c["index"]) for c in out["cases"]] == [
        ("master-nagarjuna", 0)
    ]
    assert out["by_test_type"]["fidelity"]["graded"] == 1
