"""master-debate's rounds run in fresh subagents during the eval, as in Claude Code.

The protocol dispatches every round through the Task tool so that neither side
sees the other's text. The eval had no Task tool, so one context wrote all four
rounds — and the model said as much at the top of its answer. These drive
`run_tests` with a stand-in SDK and check what each request actually carried.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NS = types.SimpleNamespace


@pytest.fixture
def fidelity():
    scripts_dir = ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location("tf_subagents", scripts_dir / "test-fidelity.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["tf_subagents"] = module
    spec.loader.exec_module(module)
    return module


def _text(text):
    return NS(content=[NS(type="text", text=text)], stop_reason="end_turn", usage=None)


def _tool(name, **args):
    return NS(content=[NS(type="tool_use", id=f"t-{name}-{len(args)}", name=name, input=args)],
              stop_reason="tool_use", usage=None)


def _has_tool_result(body):
    return any(isinstance(m["content"], list) and m["content"][0].get("type") == "tool_result"
               for m in body["messages"])


def _run(fidelity, monkeypatch, master, subagent_reply):
    """One fixture of ``master``; returns (suite, every request body sent)."""
    sent, lock = [], threading.Lock()

    def create(**body):
        with lock:
            sent.append(json.loads(json.dumps(body, default=str)))
        system = body["system"][0]["text"] if isinstance(body.get("system"), list) else ""
        if system == fidelity.SUBAGENT_SYSTEM_PROMPT:
            if not _has_tool_result(body):
                return _tool("read_file", path="../master-huineng/meta.json")
            return subagent_reply()
        if not _has_tool_result(body):
            if any(t["name"] == "Task" for t in body.get("tools", [])):
                return _tool("Task", description="R1 慧能立论", prompt="你扮演慧能大师。第 1 轮。立论。")
            return _tool("list_dir", path="..")
        return _text("### R1｜慧能大师 立论\n见性【T48n2008】")

    client = NS(messages=NS(create=create))
    monkeypatch.setitem(sys.modules, "anthropic", NS(Anthropic=lambda **_: client))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    suite = fidelity.run_tests(master, quiet=True, concurrency=1, max_tests=1)
    assert "error" not in suite, suite.get("error")
    return suite, sent


def test_only_the_skill_that_dispatches_subagents_gets_the_task_tool(fidelity, monkeypatch):
    assert fidelity.uses_subagents(fidelity.PREBUILT_DIR / "master-debate")
    assert not fidelity.uses_subagents(fidelity.PREBUILT_DIR / "compare-masters")
    assert not fidelity.uses_subagents(fidelity.PREBUILT_DIR / "master-huineng")
    suite, sent = _run(fidelity, monkeypatch, "compare-masters", lambda: _text("-"))
    assert suite["skill_tools"] == ["read_file", "list_dir"]
    assert all("Task" not in [t["name"] for t in b.get("tools", [])] for b in sent)


def test_a_round_runs_in_a_fresh_context(fidelity, monkeypatch):
    suite, sent = _run(fidelity, monkeypatch, "master-debate", lambda: _text("慧能立论正文【T48n2008】"))
    assert suite["skill_tools"] == ["read_file", "list_dir", "Task"]
    orchestrator = sent[0]
    subagent = [b for b in sent if b["system"][0]["text"] == fidelity.SUBAGENT_SYSTEM_PROMPT]
    assert subagent, "no request went out as a subagent"
    first = subagent[0]
    # Fresh: the orchestrator's prompt, skill and question are all absent.
    assert first["messages"] == [{"role": "user", "content": "你扮演慧能大师。第 1 轮。立论。"}]
    assert orchestrator["messages"][0]["content"] not in json.dumps(first, ensure_ascii=False)
    # And it cannot dispatch another.
    assert "Task" not in [t["name"] for t in first["tools"]]
    # Its reply came back to the orchestrator as the tool result.
    final_main = [b for b in sent if b is not orchestrator and b["system"][0]["text"] != fidelity.SUBAGENT_SYSTEM_PROMPT]
    assert "慧能立论正文" in json.dumps(final_main[-1], ensure_ascii=False)


def test_the_report_says_who_read_what(fidelity, monkeypatch):
    suite, _ = _run(fidelity, monkeypatch, "master-debate", lambda: _text("正文"))
    log = suite["results"][0]["tool_calls"]
    assert {"tool": "read_file", "path": "../master-huineng/meta.json", "ok": True,
            "agent": "subagent-1"} in log
    task = [e for e in log if e["tool"] == "Task"]
    assert task == [{"tool": "Task", "description": "R1 慧能立论", "ok": True, "reply_chars": 2}]
    assert suite["results"][0]["tool_rounds"] == 2  # one orchestrator round, one subagent round


def test_a_failed_subagent_is_the_orchestrators_to_handle(fidelity, monkeypatch):
    def boom():
        raise RuntimeError("upstream 529")

    suite, sent = _run(fidelity, monkeypatch, "master-debate", boom)
    result = suite["results"][0]
    assert result["status"] in ("PASS", "FAIL"), result.get("error")
    assert "error: subagent failed: upstream 529" in json.dumps(sent[-1], ensure_ascii=False)
    assert [e["ok"] for e in result["tool_calls"] if e["tool"] == "Task"] == [False]


def test_subagents_widen_the_budget_and_the_report_says_so(fidelity):
    assert fidelity.tool_budget(180, 1) == 360
    assert fidelity.tool_budget(180, 1, subagents=True) == 1080
    assert fidelity.per_fixture_ceiling(180, 1, tools=True) == 720
    assert fidelity.per_fixture_ceiling(180, 1, tools=True, subagents=True) == 1440
    assert fidelity.per_fixture_ceiling(180, 1) == 360


def test_no_request_starts_after_the_deadline(fidelity, monkeypatch):
    # Found by review: the orchestrator checked its budget only before running
    # tools, so the request carrying four subagents' replies back went out at
    # 1430 s and the fixture ran 1790 s against a stated 1440.
    now = [0.0]
    starts = []
    monkeypatch.setattr(fidelity.time, "monotonic", lambda: now[0])

    def create(**body):
        starts.append(now[0])
        now[0] += 355
        system = body["system"][0]["text"]
        if system == fidelity.SUBAGENT_SYSTEM_PROMPT:
            return _text("一轮")
        if not _has_tool_result(body):
            return NS(content=[NS(type="tool_use", id=f"t{i}", name="Task",
                                  input={"description": f"R{i}", "prompt": f"第 {i} 轮"})
                               for i in range(1, 5)],
                      stop_reason="tool_use", usage=None)
        return _text("### R1｜慧能大师 立论\n见性【T48n2008】")

    client = NS(messages=NS(create=create))
    monkeypatch.setitem(sys.modules, "anthropic", NS(Anthropic=lambda **_: client))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    suite = fidelity.run_tests("master-debate", quiet=True, concurrency=1, max_tests=1)

    budget = fidelity.tool_budget(180, 1, subagents=True)
    assert max(starts) <= budget, starts
    assert now[0] <= suite["per_fixture_ceiling_s"] == 1440, now[0]
    result = suite["results"][0]
    assert result["status"] == "api_error" and "exceeded" in result["error"]
    assert [e["ok"] for e in result["tool_calls"] if e["tool"] == "Task"] == [True, True, True, False]


def test_a_graded_debate_missing_a_round_is_flagged(fidelity, monkeypatch):
    def boom():
        raise RuntimeError("upstream 529")

    suite, _ = _run(fidelity, monkeypatch, "master-debate", boom)
    result = suite["results"][0]
    assert result["subagent_failures"] == 1 and result["needs_review"] is True
    assert result["tool_rounds_max"] == 1
