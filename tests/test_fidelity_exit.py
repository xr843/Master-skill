"""Regression tests for fidelity runner process exit semantics."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "test-fidelity.py"


@pytest.fixture
def runner(monkeypatch):
    monkeypatch.syspath_prepend(str(RUNNER_PATH.parent))
    spec = importlib.util.spec_from_file_location("test_fidelity_runner", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dry_run_results_do_not_fail(runner):
    data = [{"master": "m", "total": 1, "results": [{"status": "dry_run"}]}]
    assert runner.results_failed(data, True) is False


def test_failed_count_fails(runner):
    assert runner.results_failed([{"master": "m", "failed": 1, "results": []}], False) is True


def test_api_error_case_fails(runner):
    data = [{"master": "m", "failed": 0, "results": [{"status": "api_error"}]}]
    assert runner.results_failed(data, False) is True


def test_top_level_error_fails(runner):
    assert runner.results_failed([{"error": "missing key"}], False) is True


def test_missing_master_exits_nonzero_with_clean_json_stdout():
    result = subprocess.run(
        [
            sys.executable,
            str(RUNNER_PATH),
            "--master",
            "master-does-not-exist",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert len(payload) == 1
    assert "error" in payload[0]
