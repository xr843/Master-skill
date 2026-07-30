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


def test_dry_run_emits_versioned_completed_suite(runner):
    suite = runner.run_tests(
        "master-huineng",
        dry_run=True,
        max_tests=1,
        quiet=True,
    )

    assert suite["schema_version"] == 1
    assert suite["master"] == "master-huineng"
    assert suite["mode"] == "dry_run"
    assert suite["outcome"] == "completed"
    assert suite["total"] == 1
    assert len(suite["results"]) == 1
    assert "passed" not in suite
    assert "failed" not in suite


def test_missing_master_emits_versioned_error_suite(runner):
    assert runner.run_tests(
        "master-does-not-exist",
        dry_run=False,
        quiet=True,
    ) == {
        "schema_version": 1,
        "master": "master-does-not-exist",
        "mode": "graded",
        "outcome": "error",
        "total": 0,
        "results": [],
        "error": "Master 'master-does-not-exist' not found",
    }


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
    assert payload == [
        {
            "schema_version": 1,
            "master": "master-does-not-exist",
            "mode": "graded",
            "outcome": "error",
            "total": 0,
            "results": [],
            "error": "Master 'master-does-not-exist' not found",
        }
    ]
