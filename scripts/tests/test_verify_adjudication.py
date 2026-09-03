"""Gate tests: an adjudication must prove it read the answers it ruled on.

The 2026-08-31 sweep's failures were adjudicated by hand, and a hand-made
verdict file is exactly the kind of artifact this repo has repeatedly caught
reporting green without examining anything. So every verdict carries a quote,
and every quote must still occur in the stored response. A verdict file that
cannot be checked against the run it judges is worth nothing.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent


@pytest.fixture
def mod():
    spec = importlib.util.spec_from_file_location(
        "verify_adjudication", SCRIPTS / "verify-adjudication.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["verify_adjudication"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def pair(mod):
    adj_path = ROOT / "eval/reports/adjudication-06b8142-deepseek.json"
    adj = json.loads(adj_path.read_text())
    report = json.loads((ROOT / adj["summary"]["report"]).read_text())
    return adj, report


def test_the_committed_adjudication_verifies(mod, pair):
    adj, report = pair
    assert mod.verify(adj, report) == []


def test_an_invented_quote_is_rejected(mod, pair):
    adj, report = pair
    bad = copy.deepcopy(adj)
    bad["cases"][1]["mention_verdicts"][1]["evidence"] = "此语人格从未说过"
    problems = mod.verify(bad, report)
    assert any("evidence" in p for p in problems)


def test_a_verdict_on_a_term_that_did_not_fail_is_rejected(mod, pair):
    adj, report = pair
    bad = copy.deepcopy(adj)
    bad["cases"][1]["mention_verdicts"][0]["term"] = "从未要求过的词"
    problems = mod.verify(bad, report)
    assert any("missing_mention" in p for p in problems)


def test_reviewing_a_case_the_run_never_flagged_is_rejected(mod, pair):
    adj, report = pair
    bad = copy.deepcopy(adj)
    for case in bad["cases"]:
        if case["review_verdict"] is None:
            case["review_verdict"] = "cleared"
            case["review_evidence"] = ""
            break
    problems = mod.verify(bad, report)
    assert any("needs_review" in p for p in problems)


def test_a_summary_that_does_not_match_the_verdicts_is_rejected(mod, pair):
    adj, report = pair
    bad = copy.deepcopy(adj)
    bad["summary"]["by_test_type"]["boundary"]["adjudicated"] += 5
    problems = mod.verify(bad, report)
    assert any("summary" in p for p in problems)


def test_an_adjudication_of_nothing_is_rejected(mod, pair):
    adj, report = pair
    bad = copy.deepcopy(adj)
    bad["cases"] = []
    problems = mod.verify(bad, report)
    assert any("no cases" in p for p in problems)


def test_a_case_naming_a_run_that_has_no_such_fixture_is_rejected(mod, pair):
    adj, report = pair
    bad = copy.deepcopy(adj)
    bad["cases"][0]["index"] = 999
    problems = mod.verify(bad, report)
    assert any("999" in p for p in problems)


def test_an_unknown_verdict_word_is_rejected(mod, pair):
    adj, report = pair
    bad = copy.deepcopy(adj)
    bad["cases"][1]["mention_verdicts"][1]["verdict"] = "looks_fine_to_me"
    problems = mod.verify(bad, report)
    assert any("verdict" in p for p in problems)


# --------------------------------------------------------------------------
# Citation verdicts, and the one verdict word that decides nothing.
#
# Five `pressure` cases failed `must_cite` because the persona cited a
# *different* declared source than the fixture named — `master-kumarajiva` was
# told 「别引中论了」, complied, and cited 《金刚经》 instead. Whether `pressure`
# means "cites the named text" or "still cites a declared source" is a contract
# question for a maintainer, so those are recorded as `open_question` and must
# not move any number.
# --------------------------------------------------------------------------


def test_open_question_records_without_overturning(mod, pair):
    adj, report = pair
    before = mod.recount(adj, report)
    loosened = copy.deepcopy(adj)
    for case in loosened["cases"]:
        for verdict in case.get("cite_verdicts", []):
            if verdict["verdict"] == "open_question":
                verdict["verdict"] = "instrument"
                case["cite_case_verdict"] = "overturned"
    after = mod.recount(loosened, report)
    assert after["pressure"]["adjudicated"] > before["pressure"]["adjudicated"], (
        "the open questions are real failures today; if flipping them changes "
        "nothing the fixture is not measuring what it claims to"
    )


def test_a_citation_verdict_on_a_citation_that_was_given_is_rejected(mod, pair):
    adj, report = pair
    bad = copy.deepcopy(adj)
    for case in bad["cases"]:
        if case.get("cite_verdicts"):
            case["cite_verdicts"][0]["citation"] = "T99n9999"
            break
    problems = mod.verify(bad, report)
    assert any("missing_cite" in p or "did not miss" in p for p in problems)


def test_an_adjudication_must_declare_what_it_did_not_rule_on(mod, pair):
    adj, report = pair
    bad = copy.deepcopy(adj)
    del bad["summary"]["failures_not_ruled_on"]
    problems = mod.verify(bad, report)
    assert any("failures_not_ruled_on" in p for p in problems)


def test_understating_the_failures_left_unruled_is_rejected(mod, pair):
    adj, report = pair
    bad = copy.deepcopy(adj)
    bad["summary"]["failures_not_ruled_on"] = []
    problems = mod.verify(bad, report)
    assert any("coverage" in p for p in problems)


def test_the_committed_adjudication_leaves_only_the_maintainer_decision(mod, pair):
    adj, _report = pair
    # The three Toh:3861 contract violations are `KNOWN_UNDECLARED` in
    # validate-citation-references.py and await a maintainer, not a reader.
    assert adj["summary"]["failures_not_ruled_on"] == [
        "master-tsongkhapa #2",
        "master-tsongkhapa #3",
        "master-tsongkhapa #9",
    ]


# --------------------------------------------------------------------------
# The gate's own trust boundary: a case-level `*_case_verdict` field must be
# re-derivable from its own per-term verdicts, not merely trusted as stored.
#
# Found by an independent code-review pass (2026-09-03): recount() read
# `mention_case_verdict` straight off the JSON with nothing cross-checking it
# against the individual `mention_verdicts` it is supposed to summarize.
# Reproduced: flipping `master-ajahn-chah` #1's `mention_case_verdict` to
# "overturned" while leaving its one real `upheld` term verdict (`sati`)
# untouched made verify() report zero problems and would have turned a FAIL
# into a PASS with no evidence — the exact failure this whole gate exists to
# catch, now inside the gate itself.
# --------------------------------------------------------------------------


def test_a_case_verdict_inconsistent_with_its_term_verdicts_is_rejected(mod, pair):
    adj, report = pair
    bad = copy.deepcopy(adj)
    target = next(c for c in bad["cases"] if c.get("mention_case_verdict") == "upheld")
    assert any(m["verdict"] == "upheld" for m in target["mention_verdicts"])
    target["mention_case_verdict"] = "overturned"
    problems = mod.verify(bad, report)
    assert any("mention_case_verdict" in p for p in problems)


def test_flipping_forbidden_case_verdict_against_its_terms_is_rejected(mod, pair):
    adj, report = pair
    bad = copy.deepcopy(adj)
    target = next(
        c for c in bad["cases"]
        if c.get("forbidden_case_verdict") == "upheld"
    )
    target["forbidden_case_verdict"] = "overturned"
    problems = mod.verify(bad, report)
    assert any("forbidden_case_verdict" in p for p in problems)


def test_flipping_cite_case_verdict_against_its_terms_is_rejected(mod, pair):
    adj, report = pair
    bad = copy.deepcopy(adj)
    target = next(
        c for c in bad["cases"] if c.get("cite_case_verdict") is not None
    )
    original = target["cite_case_verdict"]
    target["cite_case_verdict"] = "upheld" if original == "overturned" else "overturned"
    problems = mod.verify(bad, report)
    assert any("cite_case_verdict" in p for p in problems)


def test_the_committed_adjudication_has_internally_consistent_case_verdicts(mod, pair):
    """Sanity check the fix isn't just rejecting everything."""
    adj, report = pair
    assert mod.verify(adj, report) == []
