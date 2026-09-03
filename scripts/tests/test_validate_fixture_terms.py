"""Gate tests: a requirement may only be declared undecidable with evidence.

`must_convey` says "the matcher cannot decide this". That is an honest thing for
an instrument to say and a very easy thing to abuse — moving an inconvenient
`must_mention` there turns a red build green and looks like rigour. So a term
may only sit in `must_convey` if a committed adjudication ruled it an instrument
artifact, on a quote verified against a real answer.

This is the same ratchet as `KNOWN_UNDECLARED` in validate-citation-references.py.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]


@pytest.fixture
def mod():
    spec = importlib.util.spec_from_file_location(
        "validate_fixture_terms", SCRIPTS / "validate-fixture-terms.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_fixture_terms"] = module
    spec.loader.exec_module(module)
    return module


def _adjudication(master: str, term: str, verdict: str = "instrument") -> dict:
    return {
        "cases": [
            {
                "master": master,
                "index": 0,
                "mention_verdicts": [
                    {"term": term, "verdict": verdict, "evidence": "…", "note": ""}
                ],
            }
        ]
    }


def test_an_adjudicated_term_may_be_declared_undecidable(mod):
    problems = mod.verify(
        {"master-fazang": [{"q": "问", "must_convey": ["方便"]}]},
        [_adjudication("master-fazang", "方便")],
    )
    assert problems == []


def test_an_unadjudicated_term_may_not_be(mod):
    problems = mod.verify(
        {"master-fazang": [{"q": "问", "must_convey": ["判教"]}]},
        [_adjudication("master-fazang", "方便")],
    )
    assert any("判教" in p for p in problems)


def test_a_verdict_for_a_different_master_does_not_transfer(mod):
    problems = mod.verify(
        {"master-huineng": [{"q": "问", "must_convey": ["方便"]}]},
        [_adjudication("master-fazang", "方便")],
    )
    assert any("master-huineng" in p for p in problems)


def test_an_upheld_verdict_is_not_permission(mod):
    """裁定说「这条是真失败」的词,更不能改判为「判不了」。"""
    problems = mod.verify(
        {"master-fazang": [{"q": "问", "must_convey": ["方便"]}]},
        [_adjudication("master-fazang", "方便", verdict="upheld")],
    )
    assert any("upheld" in p or "方便" in p for p in problems)


def test_a_term_may_not_be_both_graded_and_undecidable(mod):
    problems = mod.verify(
        {
            "master-fazang": [
                {"q": "问", "must_mention": ["方便"], "must_convey": ["方便"]}
            ]
        },
        [_adjudication("master-fazang", "方便")],
    )
    assert any("both" in p for p in problems)


def test_declaring_things_undecidable_with_no_adjudication_loaded_is_refused(mod):
    problems = mod.verify(
        {"master-fazang": [{"q": "问", "must_convey": ["方便"]}]}, []
    )
    assert any("no adjudication" in p for p in problems)


def test_fixtures_without_must_convey_need_no_adjudication(mod):
    assert mod.verify({"master-fazang": [{"q": "问", "must_mention": ["方便"]}]}, []) == []


def test_the_repository_as_committed_passes(mod):
    assert mod.verify(mod.load_fixtures(), mod.load_adjudications()) == []
