"""Re-auditing a committed run's stored answers, offline and for free.

The citation audit is a mechanical string-resolution test, so every change to
`verify_citations.py` changes what an already-paid-for run would have seen. The
¥3.89 DeepSeek sweep stored every answer; re-running the audit over those costs
nothing and turns "coverage" into something measurable after each auditor change
instead of a number frozen at run time.
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
        "reaudit_report", SCRIPTS / "reaudit-report.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["reaudit_report"] = module
    spec.loader.exec_module(module)
    return module


def _report(master: str, response: str, recorded: dict | None = None) -> dict:
    return {
        "meta": {"commit_short": "abc1234", "model": "test-model"},
        "suites": [
            {
                "master": master,
                "audit": recorded
                or {"citations_checked": 0, "citations_unparsed": 0},
                "results": [
                    {"index": 0, "status": "FAIL", "response": response}
                ],
            }
        ],
    }


def test_a_resolvable_citation_counts_as_checked(mod):
    out = mod.reaudit(_report("master-huineng", "【《坛经》，T48n2008】"))
    suite = out["suites"][0]
    assert suite["recomputed"]["checked"] == 1
    assert suite["recomputed"]["unparsed"] == 0


def test_a_master_with_no_declared_set_is_unavailable_not_zero(mod):
    """没有声明集就必须说"查不了"，不能报 0 —— 0 会被读成"查过了，没问题"。

    这条原来用的是 `master-curriculum`，因为它没有 meta.json。那是 2026-09-13
    修掉的缺陷本身：它是元技能，引的是别人的经论，声明集应当是各 persona 的
    并集，而不是"不可用"。原则没变，只是不能再拿它当例子。
    """
    out = mod.reaudit(_report("master-nobody-at-all", "【《坛经》，T48n2008】"))
    assert out["suites"][0]["status"] == "unavailable"


def test_a_meta_skill_is_audited_against_the_union(mod):
    """元技能引任一 persona 声明过的经号，算 checked。"""
    out = mod.reaudit(_report("master-curriculum", "【《坛经》，T48n2008】"))
    suite = out["suites"][0]
    assert suite["status"] == "audited"
    assert suite["recomputed"]["checked"] == 1


def test_truncated_results_are_not_audited(mod):
    report = _report("master-huineng", "【《坛经》，T48n2008】")
    report["suites"][0]["results"][0]["status"] = "truncated"
    out = mod.reaudit(report)
    assert out["suites"][0]["recomputed"]["checked"] == 0


def test_a_report_whose_answers_were_not_stored_is_refused(mod):
    report = _report("master-huineng", "")
    del report["suites"][0]["results"][0]["response"]
    with pytest.raises(ValueError, match="no stored answers"):
        mod.reaudit(report)


def test_the_delta_against_the_recorded_audit_is_reported(mod):
    report = _report(
        "master-huineng",
        "【《坛经》，T48n2008】",
        recorded={"citations_checked": 0, "citations_unparsed": 1},
    )
    suite = mod.reaudit(report)["suites"][0]
    assert suite["recorded"]["checked"] == 0
    assert suite["recomputed"]["checked"] == 1


def test_fabricated_citations_are_named_not_just_counted(mod):
    out = mod.reaudit(_report("master-huineng", "【《楞严经》，T19n0945】"))
    assert out["suites"][0]["fabricated"] == ["T19n0945"]


# --------------------------------------------------------------------------
# The committed run, re-audited. This pins what each auditor fix actually
# bought. Two rounds are folded in:
#
#   compiled_teaching (2026-09-03) — `master-ajahn-chah` could not read a
#   single one of its own citations before it; `master-mahasi-sayadaw` 12/52.
#
#   meta-skill declared sets (2026-09-13) — compare-masters and
#   master-curriculum have no meta.json at all and master-debate's carries
#   only its protocol, so all three read as "nothing declared" and their
#   citations were never audited. They quote other personas, so their declared
#   set is the union over personas. That union is strictly weaker than a
#   per-persona check — it cannot see a sutra attributed to the wrong master —
#   and strictly stronger than auditing nothing.
#
#   declared titles (2026-09-13) — `master-tsongkhapa` declares bare Wylie
#   titles (`Lam-rim-chen-mo`) and cites them in Chinese (《菩提道次第广论》)
#   or with spaces (`Lam gtso rnam gsum`); nothing matched, so 50 of its 53
#   citations sat in `unparsed`, which reads as neutral rather than as a miss.
#
# Measure with a cleared __pycache__. Four consecutive readings during this
# work were off by 4-7 citations because a stale .pyc survived a same-second
# rewrite of verify_citations.py.
# --------------------------------------------------------------------------


def test_the_committed_deepseek_run_reaudits_to_the_documented_numbers(mod):
    report = json.loads(
        (ROOT / "eval/reports/0.11.0-06b8142-deepseek.json").read_text()
    )
    out = mod.reaudit(report)
    by_master = {s["master"]: s for s in out["suites"]}

    ajahn = by_master["master-ajahn-chah"]
    assert ajahn["recorded"] == {"checked": 0, "unparsed": 48}
    assert ajahn["recomputed"] == {"checked": 43, "unparsed": 6}
    # 《Stillness Flowing》 was a genuine undeclared source (ajahn-chah #12) until
    # the maintainer declared it 2026-09-03. Coverage doesn't move — a
    # fabricated citation was already counted as "checked" — but it stops
    # being fabricated.
    assert ajahn["fabricated"] == []

    mahasi = by_master["master-mahasi-sayadaw"]
    assert mahasi["recorded"] == {"checked": 12, "unparsed": 40}
    assert mahasi["recomputed"] == {"checked": 49, "unparsed": 3}
    # 《A Discourse on Dhammacakka Sutta》 (mahasi #12) resolves via
    # collection-covers-member: Mahasi:DiscoursesOnSuttas' own note names it.
    assert mahasi["fabricated"] == []

    # Had no meta.json, so `load_declared_ids` raised and the audit was
    # skipped entirely — 47 citations served, none checked. The remaining 40
    # unparsed are the id-less 【《中论》卷四】 the output template asked for;
    # that template was fixed the same day, which this stored run predates.
    compare = by_master["compare-masters"]
    assert compare["recorded"] == {"checked": 0, "unparsed": 47}
    assert compare["recomputed"] == {"checked": 7, "unparsed": 35}
    # 5 个块是人格拿【…】当小标题或复述问题，不是引文。
    assert len(compare["noncitation"]) == 5
    assert compare["fabricated"] == []

    curriculum = by_master["master-curriculum"]
    assert curriculum["recorded"] == {"checked": 0, "unparsed": 6}
    assert curriculum["recomputed"] == {"checked": 32, "unparsed": 0}
    assert curriculum["fabricated"] == []

    buddhaghosa = by_master["master-buddhaghosa"]
    assert buddhaghosa["recorded"] == {"checked": 44, "unparsed": 16}
    assert buddhaghosa["recomputed"] == {"checked": 61, "unparsed": 0}
    assert buddhaghosa["fabricated"] == []

    # 《菩提道次第广论》 is the declared title of `Lam-rim-chen-mo`; 《三主要道》
    # of `Lam-gtso-rnam-gsum`. Both were `unparsed` — correct citations of
    # declared sources that no pattern could read.
    tsongkhapa = by_master["master-tsongkhapa"]
    assert tsongkhapa["recorded"] == {"checked": 3, "unparsed": 50}
    assert tsongkhapa["recomputed"] == {"checked": 46, "unparsed": 2}
    assert sorted(tsongkhapa["noncitation"]) == ["出据", "总结", "破异说", "立宗", "辨名义"]
    assert tsongkhapa["fabricated"] == []

    # 《父法》《子法》 — the declared title of `BDRC:Pha-chos-Bu-chos`, two
    # characters each. They are the whole reason the alias floor is 2 and not
    # 3: 4 → 523, 3 → 526, 2 → 530, 1 → 530 on this run.
    atisha = by_master["master-atisha"]
    assert atisha["recorded"] == {"checked": 25, "unparsed": 7}
    assert atisha["recomputed"] == {"checked": 29, "unparsed": 3}
    assert atisha["fabricated"] == []

    # Everything else must be untouched — a citation-family change that moves a
    # master it does not concern is a bug, not an improvement. In particular no
    # CBETA master may move: `load_title_aliases` refuses to build an alias for
    # a source whose id is a sutra number, so 【《六祖坛经》】 with no id is still
    # unparsed. That is the contract, not an oversight.
    moved = (
        "master-ajahn-chah",
        "master-mahasi-sayadaw",
        "master-buddhaghosa",
        "master-tsongkhapa",
        "master-atisha",
        "compare-masters",
        "master-curriculum",
    )
    for master, suite in by_master.items():
        if master in moved:
            continue
        if suite["status"] != "audited":
            continue
        assert suite["recorded"] == suite["recomputed"], master

    assert out["totals"]["recorded"]["checked"] == 386
    assert out["totals"]["recomputed"]["checked"] == 569


def test_api_error_rows_do_not_pollute_reaudit_totals(mod):
    """Found by an independent code-review pass (2026-09-03): only `status ==
    'truncated'` was excluded here (and in regrade-report.py, where the same
    row gets graded as a hard FAIL against real must_mention/must_cite
    requirements — an empty answer satisfies none of them). reaudit-report.py
    itself is numerically inert against an empty string (an empty answer has
    no citation blocks to find either way), but the row must still not be
    silently treated as a real, checkable answer.
    """
    report = _report("master-huineng", "【《坛经》，T48n2008】")
    report["suites"][0]["results"].append(
        {"index": 1, "status": "api_error", "question": "问", "error": "boom"}
    )
    out = mod.reaudit(report)
    assert out["suites"][0]["recomputed"]["checked"] == 1
    assert out["suites"][0]["recomputed"]["unparsed"] == 0
