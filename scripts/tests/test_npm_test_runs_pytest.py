"""Gate test: `npm test` has to run this repo's own Python test suite.

CI ran `python -m pytest tests/ scripts/tests/ -v` as a separate step
(validate-and-test.yml), but `npm test` — the command CONTRIBUTING.md's own
health-check section tells a contributor to run locally — never did. Every
Python unit test this repo has (the fidelity judge, the citation auditor, the
adjudication gate, the fixture-terms gate — 539 tests as of 2026-09-03) only
got checked in CI, never before a local push. That is the exact defect class
this repo keeps finding in itself: a check that looks like it covers something
and does not.

Since 2026-10 both `npm test` and CI run scripts/run-gates.py, so the contract
is read from its registry: a pytest gate over both suite directories that a
bare run (= `npm test`) includes, and that CI selects.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _registry():
    spec = importlib.util.spec_from_file_location(
        "_run_gates_for_pytest_test", ROOT / "scripts" / "run-gates.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_npm_test_runs_the_gate_registry():
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["scripts"]["test"].split() == ["python3", "scripts/run-gates.py"], (
        "npm test must be a bare run of scripts/run-gates.py — anything else is a "
        "second gate list, and the two drift"
    )


def test_npm_test_invokes_pytest_over_both_suite_directories():
    module = _registry()
    pytest_gates = [
        g for g in module.select([]) if "pytest" in g.argv and "-m" in g.argv
    ]
    assert len(pytest_gates) == 1, (
        "npm test does not run the Python test suite — a change to "
        "check_response, verify_citations, or any gate script can break the "
        "unit tests without `npm test` noticing"
    )
    argv = pytest_gates[0].argv
    assert "tests/" in argv and "scripts/tests/" in argv, (
        "the pytest gate must cover both suite directories"
    )


def test_ci_runs_the_same_pytest_gate():
    module = _registry()
    gate = next(g for g in module.GATES if "pytest" in g.argv)
    workflow = (ROOT / ".github" / "workflows" / "validate-and-test.yml").read_text(
        encoding="utf-8"
    )
    assert f"python scripts/run-gates.py --only {gate.group}" in workflow


def test_contributing_doc_tells_people_to_run_it_locally():
    doc = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    section = doc.split("基本健康检查", 1)[1][:600]
    assert "pytest" in section, (
        "the local health-check section still does not mention pytest — a "
        "contributor following it would never run the Python test suite"
    )
