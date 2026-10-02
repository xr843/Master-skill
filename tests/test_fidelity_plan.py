"""Evaluation planning must inspect real inputs without importing model SDKs."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "test-fidelity.py"


def run_plan(*args):
    return subprocess.run([sys.executable, "-S", str(RUNNER), "--plan", "--json", *args],
                          capture_output=True, text=True, timeout=30)


def test_plan_all_uses_real_suite_scope_and_cannot_claim_grading():
    result = run_plan("--all")
    assert result.returncode == 0, result.stderr
    suites = json.loads(result.stdout)
    assert sum(suite["total"] for suite in suites) == 211
    for suite in suites:
        assert suite["mode"] == "plan"
        assert suite["results"] == []
        assert "passed" not in suite and "pass_rate" not in suite
        assert suite["model"] == "claude-sonnet-4-6"
        assert len(suite["fixtures"]) == suite["total"]
        assert len(suite["evaluation_identity"]["skill_sha256"]) == 64
        assert all(len(case["fixture_sha256"]) == 64 for case in suite["fixtures"])


def test_persona_plan_applies_selection_and_request_parameters():
    result = run_plan("--master", "huineng", "--max-tests", "2", "--max-retries", "3",
                      "--max-output-tokens", "512", "--concurrency", "9", "--request-timeout", "10")
    assert result.returncode == 0, result.stderr
    suite, = json.loads(result.stdout)
    assert suite["total"] == 2
    assert suite["concurrency"] == 2
    assert suite["max_output_tokens"] == 512
    assert suite["request_plan"]["initial_requests"] == 2
    assert suite["request_plan"]["maximum_sdk_attempts"] == 8
    assert suite["request_plan"]["initial_output_token_limits_sum"] == 1024
    assert suite["initial_system_utf8_bytes"] > 1000
    assert suite["configured_per_fixture_ceiling_s"] == 40


def test_subagent_plan_does_not_invent_a_total_request_or_money_bound():
    result = run_plan("--master", "master-debate", "--max-tests", "1")
    assert result.returncode == 0, result.stderr
    suite, = json.loads(result.stdout)
    assert "Task" in suite["skill_tools"]
    assert suite["request_plan"]["maximum_sdk_attempts"] is None
    assert suite["request_plan"]["additional_calls"] == "model-dependent subagent fanout"
    assert "cost" not in suite


def test_file_tool_plan_includes_followup_requests_and_explicit_model():
    result = run_plan("--master", "compare-masters", "--max-tests", "1",
                      "--provider", "deepseek", "--model", "specified-model", "--max-retries", "2")
    assert result.returncode == 0, result.stderr
    suite, = json.loads(result.stdout)
    assert suite["model"] == "specified-model"
    assert suite["request_plan"]["maximum_sdk_attempts"] == 63
    assert suite["max_output_tokens"] == 32768


def test_plan_selection_is_identical_to_execution_preview():
    plan = run_plan("--master", "huineng", "--max-tests", "3")
    preview = subprocess.run([sys.executable, "-S", str(RUNNER), "--dry-run", "--json",
                             "--master", "huineng", "--max-tests", "3"],
                             capture_output=True, text=True, timeout=30)
    assert plan.returncode == preview.returncode == 0
    assert [case["question"] for case in json.loads(plan.stdout)[0]["fixtures"]] == [
        case["question"] for case in json.loads(preview.stdout)[0]["results"]]


def test_plan_text_does_not_present_an_ungraded_pass_rate():
    result = subprocess.run([sys.executable, "-S", str(RUNNER), "--plan", "--all", "--max-tests", "1"],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "planned fixtures" in result.stdout
    assert "passed" not in result.stdout and "pass_rate" not in result.stdout


@pytest.mark.parametrize("args,reason", [
    (["--master", "huineng", "--provider", "deepseek"], "pass --model explicitly"),
    (["--master", "huineng", "--max-output-tokens", "0"], "must be positive"),
    (["--master", "missing-persona"], "not found"),
    (["--all", "--dry-run"], "not allowed with argument"),
])
def test_invalid_plan_fails_before_any_paid_call(args, reason):
    result = run_plan(*args)
    assert result.returncode != 0
    assert reason in result.stdout + result.stderr
