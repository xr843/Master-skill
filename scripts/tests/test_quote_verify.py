"""`fojin_verify_trace`: the opt-in eval tool behind 「引号前先核验」.

r7 (claude-sonnet-4-6): 29 of 34 failures were quotations only — text in
quotation marks that is not the source's wording, sits under the wrong work,
or exists nowhere. The HARD-GATE now asks a host that can make HTTP requests
to check a recalled sentence with FoJin before quoting it; the eval gives no
persona a tool, so this module is how a run can measure that rule. No test
here touches the network.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import threading
import types
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path

import pytest

import _quote_verify as qv

ROOT = Path(__file__).resolve().parents[2]
NS = types.SimpleNamespace

SAMPLE = {
    "items": [
        {
            "text": "应无所住而生其心", "prefix": "", "skipped": False,
            "result": {
                "verdict": "sutra", "source_class": "sutra",
                "segments": [{
                    "text": "应无所住而生其心", "found": True, "close": False,
                    "similarity": 1.0, "weak": False,
                    "sources": [
                        {"text_id": 7, "cbeta_id": "T0235", "title_zh": "金剛般若波羅蜜經",
                         "juan_num": 1, "canon_class": "sutra",
                         "reader_url": "https://fojin.app/texts/7/read?juan=1&anchor=p0749c22&hl=1949-1957"},
                        {"text_id": 7, "cbeta_id": "T0235", "title_zh": "金剛般若波羅蜜經",
                         "juan_num": 1, "reader_url": "https://fojin.app/texts/7/read?juan=1"},
                    ],
                }],
            },
        },
        {"text": "自性须自悟", "result": {"verdict": "absent", "segments": [
            {"text": "自性须自悟", "found": False, "sources": []}]}},
    ],
    "dominant": "sutra",
}


@pytest.fixture(autouse=True)
def no_network_no_waiting(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise AssertionError("a test tried to reach the network")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    monkeypatch.setattr(qv, "MIN_INTERVAL_S", 0.0)


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _http_429(retry_after):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError(qv.ENDPOINT, 429, "Too Many Requests", headers, io.BytesIO(b""))


# --- the HTTP call ---------------------------------------------------------

def test_post_sends_the_sentences_as_json_with_the_eval_user_agent():
    seen = []

    def opener(request, timeout):
        seen.append(request)
        return _Response(json.dumps(SAMPLE).encode())

    payload, retries = qv.post(["应无所住而生其心"], opener=opener, sleep=lambda _s: None)
    assert payload == SAMPLE and retries == 0
    request = seen[0]
    assert request.full_url == "https://fojin.app/api/verify/trace"
    assert request.get_method() == "POST"
    assert request.get_header("User-agent") == "master-skill-eval"
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data.decode()) == {"sentences": ["应无所住而生其心"]}


def test_a_429_waits_for_retry_after_and_tries_again():
    calls, slept = [], []

    def opener(request, timeout):
        calls.append(1)
        if len(calls) < 3:
            raise _http_429("7")
        return _Response(json.dumps(SAMPLE).encode())

    payload, retries = qv.post(["x"], opener=opener, sleep=slept.append)
    assert payload == SAMPLE
    assert retries == 2
    assert slept == [7.0, 7.0]


def test_retry_after_is_bounded_and_defaults_when_missing():
    slept = []
    attempts = iter([_http_429("3600"), _http_429(None), None])

    def opener(request, timeout):
        error = next(attempts)
        if error:
            raise error
        return _Response(b'{"items": []}')

    qv.post(["x"], opener=opener, sleep=slept.append)
    assert slept == [qv.MAX_RETRY_AFTER_S, qv.DEFAULT_RETRY_AFTER_S]


def test_it_gives_up_after_three_retries():
    calls = []

    def opener(request, timeout):
        calls.append(1)
        raise _http_429("1")

    with pytest.raises(urllib.error.HTTPError):
        qv.post(["x"], opener=opener, sleep=lambda _s: None)
    assert len(calls) == 1 + qv.MAX_RETRIES == 4


def test_other_http_errors_are_not_retried():
    calls = []

    def opener(request, timeout):
        calls.append(1)
        raise urllib.error.HTTPError(qv.ENDPOINT, 500, "boom", Message(), io.BytesIO(b""))

    with pytest.raises(urllib.error.HTTPError):
        qv.post(["x"], opener=opener, sleep=lambda _s: None)
    assert calls == [1]


def test_calls_are_spaced_process_wide_for_the_rate_limit(monkeypatch):
    monkeypatch.setattr(qv, "MIN_INTERVAL_S", 5.0)
    now = [100.0]
    slept = []
    monkeypatch.setattr(qv, "_last_request", [98.0])

    def sleep(seconds):
        slept.append(seconds)
        now[0] += seconds

    qv.post(["x"], opener=lambda r, timeout: _Response(b"{}"), sleep=sleep, clock=lambda: now[0])
    assert slept == [3.0]


# --- trimming --------------------------------------------------------------

def test_trim_keeps_what_the_rule_reads_and_nothing_else():
    trimmed = qv.trim(SAMPLE)
    first, second = trimmed["items"]
    assert first == {
        "text": "应无所住而生其心", "verdict": "sutra",
        "segments": [{"text": "应无所住而生其心", "found": True, "sources": [
            {"cbeta_id": "T0235", "title_zh": "金剛般若波羅蜜經", "juan_num": 1,
             "reader_url": "https://fojin.app/texts/7/read?juan=1&anchor=p0749c22&hl=1949-1957"},
        ]}],
    }
    assert second["segments"] == [{"text": "自性须自悟", "found": False, "sources": []}]
    assert len(json.dumps(trimmed, ensure_ascii=False)) < len(json.dumps(SAMPLE, ensure_ascii=False))


def test_trim_survives_malformed_payloads():
    assert qv.trim({}) == {"items": []}
    assert qv.trim({"items": [None, {"text": "a", "result": None}]}) == {
        "items": [{"text": "a", "verdict": None, "segments": []}]
    }


# --- the tool ----------------------------------------------------------------

def _tool(payload=SAMPLE):
    sent = []

    def poster(sentences):
        sent.append(list(sentences))
        return payload, 0

    return qv.QuoteVerify(poster=poster), sent


def test_the_tool_sends_at_most_eight_sentences_and_says_which_it_dropped():
    tool, sent = _tool({"items": []})
    sentences = [f"第{i}句经文" for i in range(11)]
    result = json.loads(tool.call(qv.TOOL_NAME, {"sentences": sentences}))
    assert sent == [sentences[:8]]
    assert result["not_checked"] == sentences[8:]
    assert "first 8" in result["note"]


def test_overlong_sentences_are_marked_not_checked_rather_than_cut():
    tool, sent = _tool({"items": []})
    long = "如" * 201
    result = json.loads(tool.call(qv.TOOL_NAME, {"sentences": ["短句", long]}))
    assert sent == [["短句"]]
    assert result["items"] == [{"text": long, "skipped": "longer than 200 characters — not checked"}]


def test_every_call_is_logged_like_skillfiles():
    tool, _ = _tool()
    out = json.loads(tool.call(qv.TOOL_NAME, {"sentences": ["应无所住而生其心", "自性须自悟"]}))
    assert [i["verdict"] for i in out["items"]] == ["sutra", "absent"]
    tool.agent = "subagent-1"
    tool.call(qv.TOOL_NAME, {"sentences": []})
    assert tool.log == [
        {"tool": qv.TOOL_NAME, "ok": True, "sentences": ["应无所住而生其心", "自性须自悟"],
         "retries": 0, "verdicts": ["sutra", "absent"]},
        {"tool": qv.TOOL_NAME, "ok": False, "error": "no sentences given", "agent": "subagent-1"},
    ]
    assert (tool.rounds, tool.max_rounds) == (0, 0)


def test_a_failed_request_is_returned_to_the_model_not_raised():
    def poster(_sentences):
        raise urllib.error.URLError("unreachable")

    tool = qv.QuoteVerify(poster=poster)
    assert tool.call(qv.TOOL_NAME, {"sentences": ["x"]}).startswith("error:")
    assert tool.log[0]["ok"] is False
    assert tool.call("read_file", {"path": "x"}).startswith("error: unknown tool")


# --- the harness -------------------------------------------------------------

@pytest.fixture
def fidelity():
    scripts_dir = ROOT / "scripts"
    spec = importlib.util.spec_from_file_location("tf_quote_verify", scripts_dir / "test-fidelity.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["tf_quote_verify"] = module
    spec.loader.exec_module(module)
    return module


def test_tool_lists_with_and_without_the_option(fidelity):
    names = fidelity.eval_tool_names
    assert names(False, False) == []
    assert names(False, False, True) == ["fojin_verify_trace"]
    assert names(True, False) == ["read_file", "list_dir"]
    assert names(True, False, True) == ["read_file", "list_dir", "fojin_verify_trace"]
    assert names(True, True, True) == ["read_file", "list_dir", "fojin_verify_trace", "Task"]
    definition = fidelity.tool_definitions("anthropic", ("fojin_verify_trace",))[0]
    assert definition["input_schema"]["properties"]["sentences"]["maxItems"] == 8
    assert "https://fojin.app/api/verify/trace" in definition["description"]


def test_the_env_var_turns_it_on(fidelity, monkeypatch):
    monkeypatch.delenv("FIDELITY_QUOTE_VERIFY", raising=False)
    assert fidelity.quote_verify_from_env() is False
    monkeypatch.setenv("FIDELITY_QUOTE_VERIFY", "1")
    assert fidelity.quote_verify_from_env() is True


def test_skillfiles_delegates_and_shares_one_log(fidelity):
    tool, _ = _tool()
    files = fidelity.SkillFiles(fidelity.PREBUILT_DIR / "compare-masters", verifier=tool)
    files.call("list_dir", {"path": ".."})
    files.agent = "subagent-2"
    files.call("fojin_verify_trace", {"sentences": ["应无所住而生其心"]})
    assert [e["tool"] for e in files.log] == ["list_dir", "fojin_verify_trace"]
    assert files.log[1]["agent"] == "subagent-2"
    assert tool.log is files.log


def _text(text):
    return NS(content=[NS(type="text", text=text)], stop_reason="end_turn", usage=None)


def _tool_use(name, **args):
    return NS(content=[NS(type="tool_use", id=f"t-{name}", name=name, input=args)],
              stop_reason="tool_use", usage=None)


def _run(fidelity, monkeypatch, master, **kwargs):
    sent, lock = [], threading.Lock()

    def create(**body):
        with lock:
            sent.append(json.loads(json.dumps(body, default=str)))
        declared = [t["name"] for t in body.get("tools", [])]
        answered = any(isinstance(m["content"], list) and m["content"][0].get("type") == "tool_result"
                       for m in body["messages"])
        if "fojin_verify_trace" in declared and not answered:
            return _tool_use("fojin_verify_trace", sentences=["应无所住而生其心"])
        return _text("「应无所住而生其心」【《金剛般若波羅蜜經》，T0235】")

    client = NS(messages=NS(create=create))
    monkeypatch.setitem(sys.modules, "anthropic", NS(Anthropic=lambda **_: client))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    monkeypatch.setattr(qv, "post", lambda sentences: (SAMPLE, 0))
    suite = fidelity.run_tests(master, quiet=True, concurrency=1, max_tests=1, **kwargs)
    assert "error" not in suite, suite.get("error")
    return suite, sent


def test_a_persona_gets_the_tool_only_when_enabled(fidelity, monkeypatch):
    monkeypatch.delenv("FIDELITY_QUOTE_VERIFY", raising=False)
    suite, sent = _run(fidelity, monkeypatch, "master-huineng")
    assert suite["skill_tools"] == [] and suite["quote_verify_tool"] is False
    assert len(sent) == 1 and "tools" not in sent[0]

    suite, sent = _run(fidelity, monkeypatch, "master-huineng", quote_verify=True)
    assert suite["skill_tools"] == ["fojin_verify_trace"]
    assert suite["quote_verify_tool"] is True
    assert [t["name"] for t in sent[0]["tools"]] == ["fojin_verify_trace"]
    result = suite["results"][0]
    assert result["tool_calls"][0]["tool"] == "fojin_verify_trace"
    assert result["tool_calls"][0]["verdicts"] == ["sutra", "absent"]
    assert result["tool_rounds"] == 1
    # The trimmed JSON went back to the model as the tool result.
    assert "reader_url" in json.dumps(sent[-1]["messages"][-1], ensure_ascii=False)


def test_a_teaching_mode_gets_it_beside_the_file_tools(fidelity, monkeypatch):
    monkeypatch.setenv("FIDELITY_QUOTE_VERIFY", "1")
    suite, sent = _run(fidelity, monkeypatch, "compare-masters")
    assert suite["skill_tools"] == ["read_file", "list_dir", "fojin_verify_trace"]
    assert suite["quote_verify_tool"] is True
    assert [t["name"] for t in sent[0]["tools"]] == ["read_file", "list_dir", "fojin_verify_trace"]


def test_the_plan_records_the_instrument(fidelity):
    plan = fidelity.run_tests("master-huineng", plan=True, quote_verify=True, max_tests=1)
    assert plan["skill_tools"] == ["fojin_verify_trace"] and plan["quote_verify_tool"] is True
    assert plan["request_plan"]["additional_calls"] == "bounded tool rounds"


def test_runs_with_and_without_the_tool_are_not_pooled(fidelity):
    base = {"provider": "anthropic", "model": "claude-sonnet-4-6"}
    assert fidelity.aggregation_conflicts([{**base, "quote_verify_tool": False}, base]) == []
    conflicts = fidelity.aggregation_conflicts([{**base, "quote_verify_tool": True}, base])
    assert len(conflicts) == 1 and "fojin_verify_trace" in conflicts[0]
