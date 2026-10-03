"""Behaviour tests for scripts/run-gates.py, the one gate list.

The runner replaced two hand-maintained copies of the same list (package.json's
`&&` chain and the CI validate job), so the properties that matter are the ones
an `&&` chain had for free or never had at all: a failing gate makes the run
fail; later gates still run so one run reports every failure; a gate that could
not start is a failure, not a skip; and a typo in `--only` cannot select
nothing and pass.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "run-gates.py"


@pytest.fixture(scope="module")
def rg():
    spec = importlib.util.spec_from_file_location("_run_gates_under_test", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _py(rg, code: str):
    return (rg.PY, "-c", code)


def test_a_failure_fails_the_run_and_later_gates_still_run(rg, tmp_path, capsys):
    marker = tmp_path / "ran"
    gates = [
        rg.Gate("first", "g", _py(rg, "raise SystemExit(3)")),
        rg.Gate("second", "g", _py(rg, f"open({str(marker)!r}, 'w').close()")),
    ]
    results = rg.run(gates, cwd=tmp_path)
    assert [r.ok for r in results] == [False, True]
    assert marker.exists(), "the gate after a failure never ran"
    assert results[0].detail == "exit 3"
    summary = rg.summarize(results)
    assert "1 passed, 1 failed" in summary
    assert "FAILED: first" in summary


def test_a_must_fail_gate_that_exits_zero_is_a_failure(rg, tmp_path):
    """`smoke-eval-sdk.py --break` exiting 0 means the smoke cannot detect a
    broken reply — that has to turn the run red, not green."""
    passes = rg.run_gate(rg.Gate("selftest", "g", _py(rg, "pass"), expect_failure=True), tmp_path)
    assert not passes.ok and "must fail" in passes.detail
    fails = rg.run_gate(
        rg.Gate("selftest", "g", _py(rg, "raise SystemExit(1)"), expect_failure=True), tmp_path
    )
    assert fails.ok


def test_a_gate_whose_program_is_missing_fails_rather_than_skips(rg, tmp_path):
    result = rg.run_gate(rg.Gate("ghost", "g", ("no-such-program-xyz", "--help")), tmp_path)
    assert not result.ok
    assert "not found" in result.detail


def test_select_bare_run_excludes_only_not_default_gates(rg):
    default = rg.select([])
    assert default, "a bare run selects nothing"
    assert all(g.not_default is None for g in default)
    assert {g.name for g in rg.GATES} - {g.name for g in default} == {
        g.name for g in rg.GATES if g.not_default is not None
    }


def test_select_by_group_and_name_keeps_registry_order(rg):
    picked = rg.select(["cli", "content"])
    names = [g.name for g in picked]
    assert names[-1] == "cli"
    assert "validate" in names and "check-gate-liveness" in names
    order = [g.name for g in rg.GATES if g.name in set(names)]
    assert names == order


def test_explicitly_naming_a_not_default_gate_runs_it(rg):
    assert [g.name for g in rg.select(["eval-sdk"])] == [
        "check-eval-sdk-surface", "smoke-eval-sdk", "smoke-eval-sdk-break",
    ]


def test_an_unknown_selector_is_an_error_not_an_empty_pass(rg):
    with pytest.raises(ValueError, match="contnet"):
        rg.select(["contnet"])


def test_registry_invariants(rg):
    names = [g.name for g in rg.GATES]
    assert len(names) == len(set(names)), "duplicate gate names"
    # A token must mean one thing: a gate may share its group's name only if it
    # is that group's sole member.
    for group in rg.groups():
        members = [g for g in rg.GATES if g.group == group]
        assert members, group
        if group in names:
            assert [g.name for g in members] == [group], group
    for gate in rg.GATES:
        if gate.not_default is not None:
            assert gate.not_default.strip(), f"{gate.name}: empty not_default reason"
        for arg in gate.argv:
            if arg.startswith(("scripts/", "hooks/", "tests/")) and "." in Path(arg).name:
                assert (ROOT / arg).is_file(), f"{gate.name}: {arg} does not exist"


def test_cli_list_and_bad_selector_exit_codes():
    listed = subprocess.run(
        [sys.executable, str(RUNNER), "--list"], capture_output=True, text=True, timeout=60
    )
    assert listed.returncode == 0
    assert "validate-promptfoo-configs" in listed.stdout
    assert listed.stdout.isascii(), "Windows runners print through cp1252"

    bad = subprocess.run(
        [sys.executable, str(RUNNER), "--only", "contnet"],
        capture_output=True, text=True, timeout=60,
    )
    assert bad.returncode == 2
    assert "unknown gate or group" in bad.stderr


def test_cli_runs_a_selected_gate_with_its_real_exit_code(tmp_path):
    """End to end through main(): a selected passing gate exits 0."""
    ok = subprocess.run(
        [sys.executable, str(RUNNER), "--only", "validate-routing"],
        capture_output=True, text=True, timeout=120, cwd=tmp_path,
    )
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert "1 passed, 0 failed" in ok.stdout
