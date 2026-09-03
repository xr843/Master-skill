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


def test_a_master_without_meta_json_is_unavailable_not_zero(mod):
    out = mod.reaudit(_report("master-curriculum", "【《坛经》，T48n2008】"))
    assert out["suites"][0]["status"] == "unavailable"


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
# The committed run, re-audited. This pins what the compiled-teaching family
# actually bought: `master-ajahn-chah` could not read a single one of its own
# citations before it, and `master-mahasi-sayadaw` could read 12 of 52.
# --------------------------------------------------------------------------


def test_the_committed_deepseek_run_reaudits_to_the_documented_numbers(mod):
    report = json.loads(
        (ROOT / "eval/reports/0.11.0-06b8142-deepseek.json").read_text()
    )
    out = mod.reaudit(report)
    by_master = {s["master"]: s for s in out["suites"]}

    ajahn = by_master["master-ajahn-chah"]
    assert ajahn["recorded"] == {"checked": 0, "unparsed": 48}
    assert ajahn["recomputed"] == {"checked": 30, "unparsed": 18}
    # 《Stillness Flowing》 was a genuine undeclared source (ajahn-chah #12) until
    # the maintainer declared it 2026-09-03. Coverage doesn't move — a
    # fabricated citation was already counted as "checked" — but it stops
    # being fabricated.
    assert ajahn["fabricated"] == []

    mahasi = by_master["master-mahasi-sayadaw"]
    assert mahasi["recorded"] == {"checked": 12, "unparsed": 40}
    assert mahasi["recomputed"] == {"checked": 42, "unparsed": 10}
    # 《A Discourse on Dhammacakka Sutta》 (mahasi #12) resolves via
    # collection-covers-member: Mahasi:DiscoursesOnSuttas' own note names it.
    assert mahasi["fabricated"] == []

    # Everything else must be untouched — a citation-family change that moves a
    # master it does not concern is a bug, not an improvement.
    for master, suite in by_master.items():
        if master in ("master-ajahn-chah", "master-mahasi-sayadaw"):
            continue
        if suite["status"] != "audited":
            continue
        assert suite["recorded"] == suite["recomputed"], master

    assert out["totals"]["recorded"]["checked"] == 386
    assert out["totals"]["recomputed"]["checked"] == 446
