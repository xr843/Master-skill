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


# ── Found by independent review (2026-09-24) ───────────────────────────────


class _Dumpable(NS):
    """A fake SDK object whose model_dump carries a field this file never names."""

    def model_dump(self, exclude_none=False):  # recursive, as pydantic's is
        return {
            k: v.model_dump(exclude_none=exclude_none) if isinstance(v, _Dumpable) else v
            for k, v in vars(self).items()
            if not (exclude_none and v is None)
        }


def test_a_gemini_thought_signature_goes_back_with_its_tool_call(tf, files):
    call = _Dumpable(id="c1", type="function",
                     function=NS(name="read_file", arguments='{"path": "SKILL.md"}'),
                     extra_content={"google": {"thought_signature": "SIG"}})
    call.function = _Dumpable(name="read_file", arguments='{"path": "SKILL.md"}')
    replies = iter([
        NS(choices=[NS(finish_reason="tool_calls", message=NS(content=None, tool_calls=[call]))]),
        NS(choices=[NS(finish_reason="stop", message=NS(content="答", tool_calls=None))]),
    ])
    sent = []
    tf.converse(lambda b: (sent.append(json.loads(json.dumps(b))), next(replies))[1],
                "gemini", tf.build_request("gemini", "m", "s", "q", 10), files)
    echoed = sent[1]["messages"][2]["tool_calls"][0]
    assert echoed["extra_content"] == {"google": {"thought_signature": "SIG"}}


def test_an_anthropic_thinking_block_goes_back_in_the_tool_turn(tf, files):
    thinking = _Dumpable(type="thinking", thinking="…", signature="SIG")
    use = _Dumpable(type="tool_use", id="t1", name="read_file", input={"path": "SKILL.md"})
    replies = iter([
        NS(content=[thinking, use], stop_reason="tool_use", usage=None),
        NS(content=[NS(type="text", text="答")], stop_reason="end_turn", usage=None),
    ])
    sent = []
    tf.converse(lambda b: (sent.append(json.loads(json.dumps(b))), next(replies))[1],
                "anthropic", tf.build_request("anthropic", "m", "s", "q", 10), files)
    assert sent[1]["messages"][1]["content"][0] == {
        "type": "thinking", "thinking": "…", "signature": "SIG"}


@pytest.mark.parametrize("path", ["TESTS/fidelity.jsonl", "../master-huineng/Tests/fidelity.jsonl"])
def test_the_answer_key_check_ignores_case(tf, tmp_path, path):
    # On macOS / Windows these open the real file; refuse them everywhere.
    files = tf.SkillFiles(tf.PREBUILT_DIR / "compare-masters")
    assert files.call("read_file", {"path": path}).startswith("error: tests/")


def test_a_tool_call_cut_off_by_the_output_budget_is_not_run(tf, files):
    cut = NS(content=[NS(type="tool_use", id="t1", name="read_file", input={})],
             stop_reason="max_tokens", usage=None)
    final = tf.converse(lambda b: cut, "anthropic",
                        tf.build_request("anthropic", "m", "s", "q", 10), files)
    assert final is cut and files.log == []
    assert tf.extract_finish_reason("anthropic", final) == "length"


def test_twelve_rounds_run_and_a_thirteenth_request_for_tools_raises(tf, files):
    looping = NS(content=[NS(type="tool_use", id="t", name="list_dir", input={"path": "."})],
                 stop_reason="tool_use", usage=None)
    with pytest.raises(ValueError, match="after 12 rounds"):
        tf.converse(lambda b: looping, "anthropic",
                    tf.build_request("anthropic", "m", "s", "q", 10), files)
    assert len(files.log) == tf.MAX_TOOL_ROUNDS


def test_the_loop_stops_starting_rounds_after_its_budget(tf, files):
    ticks = iter(range(0, 10_000, 100))
    looping = NS(content=[NS(type="tool_use", id="t", name="list_dir", input={"path": "."})],
                 stop_reason="tool_use", usage=None)
    with pytest.raises(ValueError, match="exceeded 250s"):
        tf.converse(lambda b: looping, "anthropic",
                    tf.build_request("anthropic", "m", "s", "q", 10), files,
                    budget_s=250, clock=lambda: next(ticks))
    assert tf.per_fixture_ceiling(180, 1, tools=True) == 720
    assert tf.per_fixture_ceiling(180, 1) == 360


def test_arguments_that_are_not_an_object_are_an_error_not_a_crash(tf, files):
    assert files.call("read_file", {"path": ["a"]}).startswith("error:")
    call = NS(id="c", function=NS(name="read_file", arguments='["x"]'))
    reply = NS(choices=[NS(message=NS(tool_calls=[call]))])
    assert tf._tool_calls("deepseek", reply) == [("c", "read_file", {})]
