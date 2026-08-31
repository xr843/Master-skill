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
        # provider is additive within schema_version 1: the desktop reader
        # rejects any version != 1 outright, so a new optional field is the
        # backward-compatible way to record which instrument produced a run.
        "provider": "anthropic",
        "mode": "graded",
        "outcome": "error",
        "total": 0,
        "results": [],
        "error": "Master 'master-does-not-exist' not found",
    }


def test_invalid_fidelity_file_emits_versioned_error_suite(runner, monkeypatch, tmp_path):
    master_dir = tmp_path / "master-broken"
    (master_dir / "tests").mkdir(parents=True)
    (master_dir / "tests" / "fidelity.jsonl").write_text(
        '{"q":"valid"}\n{"q":\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "PREBUILT_DIR", tmp_path)

    suite = runner.run_tests("master-broken", dry_run=True, quiet=True)

    assert suite["schema_version"] == 1
    assert suite["master"] == "master-broken"
    assert suite["mode"] == "dry_run"
    assert suite["outcome"] == "error"
    assert suite["total"] == 0
    assert suite["results"] == []
    assert "line 2" in suite["error"]


def test_fidelity_case_without_question_emits_versioned_error_suite(
    runner, monkeypatch, tmp_path
):
    master_dir = tmp_path / "master-broken"
    (master_dir / "tests").mkdir(parents=True)
    (master_dir / "tests" / "fidelity.jsonl").write_text(
        '{"difficulty":"basic"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "PREBUILT_DIR", tmp_path)

    suite = runner.run_tests("master-broken", dry_run=True, quiet=True)

    assert suite["outcome"] == "error"
    assert suite["total"] == 0
    assert suite["results"] == []
    assert "line 1" in suite["error"]
    assert "non-empty string q" in suite["error"]


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
            "provider": "anthropic",
            "mode": "graded",
            "outcome": "error",
            "total": 0,
            "results": [],
            "error": "Master 'master-does-not-exist' not found",
        }
    ]


def test_documented_short_slug_resolves_to_the_prebuilt_dir(runner):
    """`--master yinguang` 是 README/package.json 里公开写的调用形式,而 prebuilt
    目录叫 `master-yinguang`。运行器一直只认字面值,没用 `_masterpaths` 里为此存在
    的 `resolve_master_dir` —— 于是 `npm run test:smoke` 从来没跑通过。"""
    suite = runner.run_tests("yinguang", dry_run=True, quiet=True)
    assert "error" not in suite, suite.get("error")
    assert suite["total"] > 0


def test_full_directory_name_still_resolves(runner):
    suite = runner.run_tests("master-yinguang", dry_run=True, quiet=True)
    assert "error" not in suite
    assert suite["total"] > 0


def test_error_suite_says_why_in_human_readable_mode(capsys):
    """出错时人读模式只印一行标题就没了 —— 操作者看到的是沉默,不是失败原因。"""
    proc = subprocess.run(
        [sys.executable, str(RUNNER_PATH), "--master", "no-such-master", "--dry-run"],
        capture_output=True, text=True,
    )
    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert "no-such-master" in combined
    assert "not found" in combined.lower()
