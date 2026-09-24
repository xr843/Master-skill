"""Teaching-mode evals get read-only file tools over the installed layout.

In Claude Code a teaching mode reads its sibling personas' meta.json and
references. The eval gave the model no tools, so it answered without that data
or wrote the tool call out as text — six graded PASSes in e97ded0 were
leaked tool-call markup. These pin what the tools can and cannot read, and
drive the tool loop with fake responses in both providers' shapes.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]


@pytest.fixture
def tf():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("tf_tools", SCRIPTS / "test-fidelity.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["tf_tools"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def files(tf):
    return tf.SkillFiles(tf.PREBUILT_DIR / "compare-masters")


@pytest.mark.parametrize("path", [
    "../master-huineng/meta.json",
    "master-huineng/meta.json",
    "~/.claude/skills/master-huineng/meta.json",
    "/home/someone/.claude/skills/master-huineng/meta.json",
    "prebuilt/master-huineng/meta.json",
])
def test_every_way_a_skill_names_a_sibling_file_reads_it(files, path):
    assert json.loads(files.call("read_file", {"path": path}))["name"] == "慧能大师"


@pytest.mark.parametrize("path", [
    "tests/fidelity.jsonl",
    "../master-huineng/tests/fidelity.jsonl",
    "~/.claude/skills/master-debate/tests/fidelity.jsonl",
])
def test_the_answer_key_is_never_readable(files, path):
    assert files.call("read_file", {"path": path}).startswith("error: tests/")


@pytest.mark.parametrize("path", ["../../package.json", "/etc/passwd", "../../scripts/test-fidelity.py"])
def test_nothing_outside_the_skills_directory_is_readable(files, path):
    assert files.call("read_file", {"path": path}).startswith("error:")


def test_a_missing_sibling_is_missing_not_outside(files):
    assert files.call("read_file", {"path": "../master-nobody/meta.json"}) == "error: no such file"


def test_listing_hides_tests_and_every_call_is_logged(files):
    assert "tests" not in files.call("list_dir", {"path": "."})
    assert "master-huineng/" in files.call("list_dir", {"path": ".."}).splitlines()
    files.call("read_file", {"path": "tests/fidelity.jsonl"})
    assert [(e["tool"], e["ok"]) for e in files.log] == [
        ("list_dir", True), ("list_dir", True), ("read_file", False),
    ]


def test_only_teaching_modes_get_tools(tf):
    assert tf.uses_skill_tools(tf.PREBUILT_DIR / "compare-masters")
    assert tf.uses_skill_tools(tf.PREBUILT_DIR / "master-help")
    assert not tf.uses_skill_tools(tf.PREBUILT_DIR / "master-huineng")


def _anthropic_reply(*blocks):
    return NS(content=list(blocks), stop_reason="tool_use" if any(
        b.type == "tool_use" for b in blocks) else "end_turn", usage=None)


def test_the_anthropic_loop_answers_tool_calls_and_returns_the_final_reply(tf, files):
    replies = iter([
        _anthropic_reply(NS(type="tool_use", id="t1", name="read_file",
                            input={"path": "../master-huineng/meta.json"})),
        _anthropic_reply(NS(type="text", text="答")),
    ])
    sent = []

    def send(body):
        sent.append(json.loads(json.dumps(body)))
        return next(replies)

    body = tf.build_request("anthropic", "m", "sys", "问", 100)
    final = tf.converse(send, "anthropic", body, files)
    assert tf.extract_text("anthropic", final) == "答"
    assert [t["name"] for t in sent[0]["tools"]] == ["read_file", "list_dir"]
    tool_result = sent[1]["messages"][2]["content"][0]
    assert tool_result["tool_use_id"] == "t1" and "慧能大师" in tool_result["content"]
    assert body["messages"] == [{"role": "user", "content": "问"}]  # caller's body untouched


def test_the_openai_loop_hands_back_tool_results_and_reasoning(tf, files):
    call = NS(id="c1", function=NS(name="list_dir", arguments='{"path": ".."}'))
    replies = iter([
        NS(choices=[NS(finish_reason="tool_calls", message=NS(
            content=None, tool_calls=[call], reasoning_content="想一想"))]),
        NS(choices=[NS(finish_reason="stop", message=NS(content="答", tool_calls=None))]),
    ])
    sent = []

    def send(body):
        sent.append(json.loads(json.dumps(body)))
        return next(replies)

    final = tf.converse(send, "deepseek", tf.build_request("deepseek", "m", "sys", "问", 100), files)
    assert tf.extract_text("deepseek", final) == "答"
    assistant, tool = sent[1]["messages"][2:4]
    assert assistant["reasoning_content"] == "想一想"
    assert tool["tool_call_id"] == "c1" and "master-huineng/" in tool["content"]


def test_a_model_that_never_stops_calling_tools_is_not_graded(tf, files):
    looping = _anthropic_reply(NS(type="tool_use", id="t", name="list_dir", input={"path": "."}))
    with pytest.raises(ValueError, match="still calling tools"):
        tf.converse(lambda body: looping, "anthropic",
                    tf.build_request("anthropic", "m", "s", "q", 10), files)
