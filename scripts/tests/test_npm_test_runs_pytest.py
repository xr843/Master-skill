"""Gate test: `npm test` has to run this repo's own Python test suite.

CI runs `python -m pytest tests/ scripts/tests/ -v` as a separate step
(validate-and-test.yml), but `npm test` — the command CONTRIBUTING.md's own
health-check section tells a contributor to run locally — never did. Every
Python unit test this repo has (the fidelity judge, the citation auditor, the
adjudication gate, the fixture-terms gate — 539 tests as of 2026-09-03) only
gets checked in CI, never before a local push. That is the exact defect class
this repo keeps finding in itself: a check that looks like it covers something
and does not.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_npm_test_invokes_pytest_over_both_suite_directories():
    package = json.loads((ROOT / "package.json").read_text())
    test_script = package["scripts"]["test"]
    assert "pytest" in test_script, (
        "npm test does not run the Python test suite — a change to "
        "check_response, verify_citations, or any gate script can break 539 "
        "tests without `npm test` noticing"
    )
    assert "tests/" in test_script and "scripts/tests/" in test_script, (
        "pytest invocation must cover both suite directories, matching CI's "
        "`python -m pytest tests/ scripts/tests/ -v`"
    )


def test_contributing_doc_tells_people_to_run_it_locally():
    doc = (ROOT / "CONTRIBUTING.md").read_text()
    section = doc.split("基本健康检查", 1)[1][:600]
    assert "pytest" in section, (
        "the local health-check section still does not mention pytest — a "
        "contributor following it would never run the Python test suite"
    )
