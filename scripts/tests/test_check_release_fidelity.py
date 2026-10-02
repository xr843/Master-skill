"""The v1 gate reads committed, adjudicated runs — and a real run can pass it.

The first version required a fresh sweep to have no `needs_review` case. Every
`must_convey` requirement goes to review by design, so no sweep could pass;
its own test used a report with none. These build runs that carry reviews, as
real ones do, and check both directions.
"""

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from _fixture_identity import fixture_sha256  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "check_release_fidelity", ROOT / "scripts" / "check-release-fidelity.py"
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

TYPES = {"master-demo": ["fidelity", "boundary", "pressure"]}
QUESTIONS = {"master-demo": ["q0", "q1", "q2"]}
FIXTURES = [
    {"q": "q0", "test_type": "fidelity", "must_convey": ["缘起"]},
    {"q": "q1", "test_type": "boundary", "must_not_contain": ["排名"]},
    {"q": "q2", "test_type": "pressure", "must_cite": ["T48n2008"]},
]
IDENTITIES = {"master-demo": {"skill_sha256": "runtime", "grader_sha256": "grader"}}
DIGESTS = {"master-demo": [fixture_sha256(case) for case in FIXTURES]}


def _case(index, kind, **changes):
    case = {
        "index": index, "question": f"q{index}", "status": "PASS", "test_type": kind,
        "fixture_sha256": DIGESTS["master-demo"][index],
        "response": f"answer {index} 此句可引", "fabricated_cites": [], "missing_mentions": [],
        "needs_review": False, "audit_unavailable": False,
        "citation_audit_ready": True, "unparsed_citations": [],
        "unverified_live_citations": [], "unverified_quotes": [],
    }
    case.update(changes)
    return case


def _run():
    report = {"suites": [{
        "master": "master-demo", "mode": "graded", "provider": "anthropic",
        "evaluation_identity": IDENTITIES["master-demo"],
        "model": "claude-sonnet-4-6", "total": 3,
        "results": [
            # A must_convey requirement: PASS as graded, held for a ruling.
            _case(0, "fidelity", needs_review=True, unverified_mentions=["缘起"]),
            _case(1, "boundary"),
            _case(2, "pressure"),
        ],
    }]}
    adjudication = {"summary": {"failures_not_ruled_on": []}, "cases": [{
        "master": "master-demo", "index": 0, "test_type": "fidelity", "question": "q0",
        "graded_status": "PASS", "mention_verdicts": [], "mention_case_verdict": None,
        "cite_verdicts": [], "cite_case_verdict": None, "forbidden_verdicts": [],
        "forbidden_case_verdict": None, "review_verdict": "cleared",
        "review_evidence": "此句可引", "review_note": "conveyed",
    }]}
    return report, adjudication


def _finish(report, adjudication):
    """Fill in the summary figures the verifier recomputes."""
    va = checker._adjudication_module()
    adjudication["summary"]["by_test_type"] = va.recount(adjudication, report)
    return report, adjudication


def _problems(report, adjudication):
    return checker.validate([_finish(report, adjudication)], TYPES, QUESTIONS, expected_identities=IDENTITIES, expected_digests=DIGESTS)[0]


def test_a_run_with_reviews_passes_once_they_are_ruled_on():
    assert _problems(*_run()) == []


def test_an_unruled_review_blocks_release():
    report, adjudication = _run()
    adjudication["cases"] = []
    assert any("needs_review is not ruled on" in p for p in _problems(report, adjudication))


def test_a_violation_ruling_can_take_a_category_below_its_threshold():
    report, adjudication = _run()
    adjudication["cases"][0]["review_verdict"] = "violation"
    assert any("fidelity: 0/1" in p for p in _problems(report, adjudication))


def test_a_fabricated_citation_blocks_release():
    report, adjudication = _run()
    report["suites"][0]["results"][1]["fabricated_cites"] = ["T99n9999"]
    assert any("fabricated" in p for p in _problems(report, adjudication))


@pytest.mark.parametrize("bad_value", [None, {}, "", "missing"])
def test_missing_or_invalid_fabrication_result_is_not_zero(bad_value):
    report, adjudication = _run()
    result = report["suites"][0]["results"][1]
    if bad_value == "missing":
        result.pop("fabricated_cites")
    else:
        result["fabricated_cites"] = bad_value
    assert any("fabrication result missing or invalid" in p for p in _problems(report, adjudication))


def test_audit_unavailable_cannot_be_cleared_by_an_answer_review():
    report, adjudication = _run()
    # #0 has a valid review ruling. It does not turn an unperformed citation
    # audit into an audit with zero fabrications.
    report["suites"][0]["results"][0]["audit_unavailable"] = True
    assert any("citation audit unavailable" in p for p in _problems(report, adjudication))

    report["suites"][0]["results"][0].pop("audit_unavailable")
    assert any("citation audit unavailable" in p for p in _problems(report, adjudication))


def test_missing_source_set_cannot_look_like_a_clean_audit():
    report, adjudication = _run()
    report["suites"][0]["results"][1]["citation_audit_ready"] = False
    assert any("citation audit had no declared sources" in p for p in _problems(report, adjudication))

    report["suites"][0]["results"][1].pop("citation_audit_ready")
    assert any("citation audit had no declared sources" in p for p in _problems(report, adjudication))


def test_unparsed_citations_are_reported_not_gated():
    report, adjudication = _run()
    report["suites"][0]["results"][2]["unparsed_citations"] = ["《无可核对》"]
    problems, _, unparsed = checker.validate([_finish(report, adjudication)], TYPES, QUESTIONS, expected_identities=IDENTITIES, expected_digests=DIGESTS)
    assert problems == [] and unparsed == 1


def test_coverage_model_and_categories_are_checked():
    report, adjudication = _run()
    bad = copy.deepcopy(report)
    bad["suites"][0]["results"].pop()
    assert any("exactly once" in p for p in _problems(bad, copy.deepcopy(adjudication)))
    bad = copy.deepcopy(report)
    bad["suites"][0]["model"] = "deepseek-v4-flash"
    assert any("release model" in p for p in _problems(bad, copy.deepcopy(adjudication)))
    bad = copy.deepcopy(report)
    bad["suites"][0]["results"][1]["test_type"] = "fidelity"
    assert any("test_type" in p for p in _problems(bad, copy.deepcopy(adjudication)))
    assert any("missing suite" in p for p in checker.validate(
        [_finish(*_run())], {**TYPES, "master-other": ["fidelity"]}, QUESTIONS, expected_identities=IDENTITIES, expected_digests=DIGESTS)[0])


def test_replaced_question_cannot_reuse_an_old_run():
    report, adjudication = _run()
    report["suites"][0]["results"][1]["question"] = "an older question"
    problems = checker.validate(
        [_finish(report, adjudication)], TYPES, QUESTIONS, expected_identities=IDENTITIES, expected_digests=DIGESTS,
    )[0]
    assert any("master-demo #1: question differs from its fixture" in p for p in problems)


def test_changed_assertion_or_missing_digest_cannot_reuse_an_old_run():
    report, adjudication = _run()
    changed = {**FIXTURES[1], "must_not_contain": ["排名", "最高"]}
    current = {"master-demo": [DIGESTS["master-demo"][0], fixture_sha256(changed), DIGESTS["master-demo"][2]]}
    problems = checker.validate([_finish(report, adjudication)], TYPES, QUESTIONS, expected_identities=IDENTITIES, expected_digests=current)[0]
    assert any("master-demo #1: fixture digest differs" in p for p in problems)

    report["suites"][0]["results"][1].pop("fixture_sha256")
    problems = checker.validate([_finish(report, adjudication)], TYPES, QUESTIONS, expected_identities=IDENTITIES, expected_digests=DIGESTS)[0]
    assert any("master-demo #1: fixture digest differs" in p for p in problems)


def test_an_adjudication_that_does_not_verify_blocks_release():
    report, adjudication = _run()
    adjudication["cases"][0]["review_evidence"] = "not in the answer"
    assert any("adjudication:" in p for p in _problems(report, adjudication))


def test_it_reads_the_committed_runs_as_they_are_stored():
    # Old real pairs still recount, but cannot qualify for v1: wrong model and
    # no fixture digests, so their answers are not tied to their full fixtures.
    pairs = []
    for report, adj in [
        ("0.12.15-0e7d97e-deepseek-personas.json", "adjudication-0e7d97e-deepseek-personas.json"),
    ]:
        pairs.append((
            json.loads((ROOT / "eval/reports" / report).read_text(encoding="utf-8")),
            json.loads((ROOT / "eval/reports" / adj).read_text(encoding="utf-8")),
        ))
    problems, tally, _ = checker.validate(
        pairs, checker.fixture_types(), checker.fixture_questions(), expected_identities=checker.runtime_identities(), expected_digests=checker.fixture_digests()
    )
    assert tally["fidelity"]["graded"] == 83
    assert any("release model" in p for p in problems)
    assert any("fixture digest differs" in p for p in problems)
    assert not any(p.startswith("adjudication:") for p in problems)


def test_the_publish_workflow_checks_committed_runs_and_spends_nothing():
    import yaml

    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/npm-publish.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["gate"]["steps"]
    gate = next(step for step in steps if step.get("name") == "v1 fidelity gate (committed runs)")
    assert "check-release-fidelity.py --manifest eval/reports/v1-release.json" in gate["run"]
    assert "test-fidelity.py" not in json.dumps(workflow)
    assert "ANTHROPIC_API_KEY" not in json.dumps(workflow["jobs"]["gate"])


def test_runtime_or_grader_change_requires_new_measurement():
    report, adjudication = _run()
    changed = {"master-demo": {**IDENTITIES["master-demo"], "skill_sha256": "new runtime"}}
    problems = checker.validate([_finish(report, adjudication)], TYPES, QUESTIONS,
        expected_digests=DIGESTS, expected_identities=changed)[0]
    assert any("evaluation identity differs" in p for p in problems)
    report["suites"][0].pop("evaluation_identity")
    assert any("evaluation identity differs" in p for p in _problems(report, adjudication))


def test_link_and_quote_evidence_cannot_be_silently_dropped():
    report, adjudication = _run()
    report["suites"][0]["results"][1].pop("unverified_live_citations")
    assert any("citation evidence result missing" in p for p in _problems(report, adjudication))
