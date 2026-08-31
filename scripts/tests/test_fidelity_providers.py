"""Behaviour tests for multi-provider fidelity runs.

This project ships one `prebuilt/` to five hosts — Claude Code, Cursor, Codex
CLI, OpenCode, and Gemini CLI — and the README calls that a unified plugin. But
every fidelity number it has ever produced came from one Anthropic model. A
fixture measures whether the *prompt* induces the right behaviour, and that is a
property of the prompt-and-model pair, not of the prompt alone. The Gemini CLI
path in particular ships its own extension manifest and has zero evidence
behind it.

So provider is an axis of the eval matrix, not a cost workaround. The rule that
comes with it: a run records which provider and model produced it, and numbers
from different models are never averaged together.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture
def fidelity():
    scripts_dir = Path(__file__).resolve().parents[1]
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location(
        "test_fidelity_providers_mod", scripts_dir / "test-fidelity.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["test_fidelity_providers_mod"] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# Provider registry
# --------------------------------------------------------------------------


def test_anthropic_is_the_default_provider(fidelity):
    assert fidelity.DEFAULT_PROVIDER == "anthropic"


def test_every_provider_declares_its_key_and_api_style(fidelity):
    for name, spec in fidelity.PROVIDERS.items():
        assert spec["env"].endswith("_API_KEY"), name
        assert spec["api"] in {"anthropic", "openai"}, name
        if spec["api"] == "openai":
            assert spec["base_url"], f"{name} needs a base_url"


def test_the_three_shipped_hosts_are_covered(fidelity):
    assert {"anthropic", "deepseek", "gemini"} <= set(fidelity.PROVIDERS)


def test_unknown_provider_is_rejected_by_name(fidelity):
    with pytest.raises(ValueError) as excinfo:
        fidelity.resolve_provider("llama-at-home")
    assert "llama-at-home" in str(excinfo.value)


# --------------------------------------------------------------------------
# Model resolution.
#
# Anthropic keeps its default so nothing that exists today changes. Every other
# provider must be told explicitly: shipping a guessed model id would rot, and
# a run that cannot name its model is not reproducible.
# --------------------------------------------------------------------------


def test_anthropic_keeps_its_default_model(fidelity):
    assert fidelity.resolve_model("anthropic", None) == "claude-sonnet-4-6"


def test_explicit_model_always_wins(fidelity):
    assert fidelity.resolve_model("anthropic", "claude-opus-4-8") == "claude-opus-4-8"
    assert fidelity.resolve_model("deepseek", "deepseek-chat") == "deepseek-chat"


def test_non_anthropic_provider_without_a_model_is_an_error(fidelity):
    for provider in ("deepseek", "gemini"):
        with pytest.raises(ValueError) as excinfo:
            fidelity.resolve_model(provider, None)
        message = str(excinfo.value)
        assert provider in message
        assert "--model" in message


# --------------------------------------------------------------------------
# Request shape differs per API style; both must carry the same system prompt
# and the same question.
# --------------------------------------------------------------------------


def test_anthropic_request_keeps_system_at_the_top_level(fidelity):
    req = fidelity.build_request("anthropic", "claude-sonnet-4-6", "SYS", "Q?", 2048)
    assert req["model"] == "claude-sonnet-4-6"
    assert req["system"] == "SYS"
    assert req["max_tokens"] == 2048
    assert req["messages"] == [{"role": "user", "content": "Q?"}]


def test_openai_style_request_moves_system_into_messages(fidelity):
    req = fidelity.build_request("deepseek", "deepseek-chat", "SYS", "Q?", 2048)
    assert req["model"] == "deepseek-chat"
    assert "system" not in req
    assert req["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "Q?"},
    ]


def test_openai_style_uses_max_tokens_key_the_sdk_expects(fidelity):
    req = fidelity.build_request("gemini", "gemini-x", "SYS", "Q?", 1024)
    assert req.get("max_tokens") == 1024


# --------------------------------------------------------------------------
# Response extraction differs per API style.
# --------------------------------------------------------------------------


def _anthropic_response(text):
    block = types.SimpleNamespace(type="text", text=text)
    return types.SimpleNamespace(content=[block])


def _openai_response(text):
    message = types.SimpleNamespace(content=text)
    return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])


def test_extracts_text_from_an_anthropic_response(fidelity):
    assert fidelity.extract_text("anthropic", _anthropic_response("无念者…")) == "无念者…"


def test_extracts_text_from_an_openai_style_response(fidelity):
    assert fidelity.extract_text("deepseek", _openai_response("自性本清净")) == "自性本清净"


def test_empty_response_content_raises_rather_than_scoring_a_blank(fidelity):
    """A blank answer must not be silently graded — it would fail every
    must_mention and be recorded as a persona defect."""
    with pytest.raises(ValueError):
        fidelity.extract_text("deepseek", types.SimpleNamespace(choices=[]))


# --------------------------------------------------------------------------
# Provenance: a suite has to name the instrument that produced it.
# --------------------------------------------------------------------------


def test_suite_records_the_provider(fidelity):
    suite = fidelity.suite_common("master-zhiyi", False, "completed", provider="deepseek")
    assert suite["provider"] == "deepseek"


def test_suite_defaults_to_anthropic_for_older_callers(fidelity):
    assert fidelity.suite_common("master-zhiyi", True, "completed")["provider"] == "anthropic"


def test_error_suite_also_records_the_provider(fidelity):
    suite = fidelity.suite_error("master-zhiyi", False, "boom", provider="gemini")
    assert suite["provider"] == "gemini"


# --------------------------------------------------------------------------
# Cross-model aggregation is the mistake this axis makes easy. Refuse it.
# --------------------------------------------------------------------------


def test_aggregating_one_model_is_fine(fidelity):
    suites = [
        {"provider": "anthropic", "model": "claude-sonnet-4-6", "results": []},
        {"provider": "anthropic", "model": "claude-sonnet-4-6", "results": []},
    ]
    assert fidelity.aggregation_conflicts(suites) == []


def test_aggregating_two_models_is_refused_by_name(fidelity):
    suites = [
        {"provider": "anthropic", "model": "claude-sonnet-4-6", "results": []},
        {"provider": "deepseek", "model": "deepseek-chat", "results": []},
    ]
    conflicts = fidelity.aggregation_conflicts(suites)
    assert conflicts
    joined = " ".join(conflicts)
    assert "claude-sonnet-4-6" in joined and "deepseek-chat" in joined


def test_same_provider_different_model_is_still_refused(fidelity):
    """Sonnet and Opus are different instruments too."""
    suites = [
        {"provider": "anthropic", "model": "claude-sonnet-4-6", "results": []},
        {"provider": "anthropic", "model": "claude-opus-4-8", "results": []},
    ]
    assert fidelity.aggregation_conflicts(suites)


# --------------------------------------------------------------------------
# Truncation is an instrument condition, not a fidelity failure.
#
# DeepSeek V4 and other reasoning models spend the output budget on reasoning
# before writing anything. Measured on `deepseek-v4-pro` with the harness's
# hardcoded max_tokens=2048: finish_reason="length", 1,860 reasoning tokens,
# 250 characters of answer. Four of six smoke responses came back empty and the
# judge scored them as "missing citation / missing keyword" — a persona failure
# that never happened. Grading a cut-off answer measures the budget, not the
# prompt.
# --------------------------------------------------------------------------


def _openai_finish(finish_reason):
    return types.SimpleNamespace(
        choices=[types.SimpleNamespace(finish_reason=finish_reason)]
    )


def test_openai_style_truncation_is_detected(fidelity):
    assert fidelity.extract_finish_reason(
        "deepseek", _openai_finish("length")
    ) == "length"


def test_openai_style_normal_stop_is_not_truncation(fidelity):
    assert fidelity.extract_finish_reason("deepseek", _openai_finish("stop")) == "stop"


def test_anthropic_max_tokens_stop_reason_normalises_to_length(fidelity):
    """Anthropic calls it `stop_reason: max_tokens`; one vocabulary downstream."""
    resp = types.SimpleNamespace(stop_reason="max_tokens")
    assert fidelity.extract_finish_reason("anthropic", resp) == "length"


def test_truncated_result_is_not_graded_as_a_fidelity_failure(fidelity):
    entry = fidelity.truncated_result_entry(
        index=2, test={"q": "什么是禅七？"}, response_text="虚云老和尚答……",
        max_output_tokens=2048,
    )
    assert entry["status"] == "truncated"
    assert "missing_cites" not in entry
    assert entry["max_output_tokens"] == 2048


def test_truncated_cases_fail_the_run_like_an_api_error(fidelity):
    suites = [{"failed": 0, "results": [{"status": "truncated"}]}]
    assert fidelity.results_failed(suites, dry_run=False) is True


def test_request_honours_an_explicit_output_budget(fidelity):
    body = fidelity.build_request("deepseek", "deepseek-v4-pro", "sys", "q", 8192)
    assert body["max_tokens"] == 8192


def test_output_budget_is_a_named_default_not_a_literal(fidelity):
    assert fidelity.DEFAULT_MAX_OUTPUT_TOKENS == 2048


def test_cli_exposes_the_output_budget(fidelity):
    import subprocess, sys as _sys
    from pathlib import Path as _P
    runner = _P(__file__).resolve().parents[1] / "test-fidelity.py"
    out = subprocess.run(
        [_sys.executable, str(runner), "--help"], capture_output=True, text=True
    ).stdout
    assert "--max-output-tokens" in out
