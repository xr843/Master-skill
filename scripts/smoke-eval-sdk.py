#!/usr/bin/env python3
"""Keyless end-to-end smoke for the pinned eval SDKs.

`check-eval-sdk-surface.py` reads signatures. That catches a renamed keyword,
not a changed wire format, a response model that parses differently, or a
client that stops honouring its base URL. And the real path —
`scripts/test-fidelity.py` — never runs in CI, because grading needs an API
key and there is none. So every Dependabot bump of `anthropic` or `openai`
arrived green having exercised nothing, which `requirements-eval.txt` says in
as many words.

This runs that real path without a key or a network. A local HTTP server
answers in each provider's own wire format; `test-fidelity.py` builds its
request, the pinned SDK sends and parses it, and the answer goes through
grading and the citation audit exactly as in a sweep. Then it checks what
arrived at the server and what came back.

    python3 scripts/smoke-eval-sdk.py           # must exit 0
    python3 scripts/smoke-eval-sdk.py --break   # must exit 1

`--break` makes the server return a reply with no answer text while every
assertion stays the same. CI runs both: a smoke that cannot fail is a green
tick, not a check.

First written 2026-09-14 to verify anthropic 1.4.0 → 1.5.0 and openai
3.10.0 → 3.13.0 (#174, #175).
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ANSWER = "菩提自性，本来清净，但用此心，直了成佛。【《六祖大师法宝坛经》行由品，T48n2008】"
CACHE_CREATED = 6700
# The teaching-mode run's first reply asks for this file; the second request
# must carry it back. See SkillFiles in test-fidelity.py.
TOOL_PATH = "../master-huineng/meta.json"
# master-debate also gets the Task tool; its first reply dispatches a subagent,
# whose request must arrive as a fresh conversation.
SUBAGENT_PROMPT = "你扮演慧能大师。第 1 轮。立论。"
SUBAGENT_REPLY = "慧能立论：菩提自性，本来清净。【T48n2008】"


def _is_subagent(body: dict) -> bool:
    system = body.get("system")
    text = system[0].get("text", "") if isinstance(system, list) else (
        body.get("messages", [{}])[0].get("content", "")
        if body.get("messages", [{}])[0].get("role") == "system" else "")
    return str(text).startswith("You are a subagent")


def _has_tool_result(body: dict) -> bool:
    for message in body.get("messages", []):
        if message.get("role") == "tool":
            return True
        content = message.get("content")
        if isinstance(content, list) and any(
            isinstance(part, dict) and part.get("type") == "tool_result" for part in content
        ):
            return True
    return False


def _server(broken: bool, received: list) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep CI logs quiet
            pass

        def do_POST(self):
            length = int(self.headers.get("content-length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            headers = {k.lower(): v for k, v in self.headers.items()}
            received.append((self.path, body, headers))
            wants_tool = bool(body.get("tools")) and not _has_tool_result(body)
            tool_names = [t.get("name") or t.get("function", {}).get("name") for t in body.get("tools", [])]
            call = ("Task", {"description": "R1", "prompt": SUBAGENT_PROMPT}) \
                if "Task" in tool_names else ("read_file", {"path": TOOL_PATH})
            if _is_subagent(body):
                if self.path.endswith("/messages"):
                    reply = {"id": "msg_sub", "type": "message", "role": "assistant",
                             "model": body.get("model"),
                             "content": [{"type": "text", "text": SUBAGENT_REPLY}],
                             "stop_reason": "end_turn", "stop_sequence": None,
                             "usage": {"input_tokens": 5, "output_tokens": 5}}
                else:
                    reply = {"id": "chatcmpl-sub", "object": "chat.completion", "created": 1,
                             "model": body.get("model"),
                             "choices": [{"index": 0, "finish_reason": "stop",
                                          "message": {"role": "assistant", "content": SUBAGENT_REPLY}}],
                             "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}}
            elif self.path.endswith("/messages") and wants_tool:
                reply = {
                    "id": "msg_tool", "type": "message", "role": "assistant",
                    "model": body.get("model"),
                    "content": [{"type": "tool_use", "id": "toolu_smoke", "name": call[0],
                                 "input": call[1]}],
                    "stop_reason": "tool_use", "stop_sequence": None,
                    "usage": {"input_tokens": 21, "output_tokens": 10},
                }
            elif wants_tool:
                reply = {
                    "id": "chatcmpl-tool", "object": "chat.completion", "created": 1,
                    "model": body.get("model"),
                    "choices": [{
                        "index": 0, "finish_reason": "tool_calls",
                        "message": {"role": "assistant", "content": None, "tool_calls": [{
                            "id": "call_smoke", "type": "function",
                            "function": {"name": call[0],
                                         "arguments": json.dumps(call[1])},
                        }]},
                    }],
                    "usage": {"prompt_tokens": 21, "completion_tokens": 10, "total_tokens": 31},
                }
            elif self.path.endswith("/messages"):
                reply = {
                    "id": "msg_smoke", "type": "message", "role": "assistant",
                    "model": body.get("model"),
                    "content": [] if broken else [{"type": "text", "text": ANSWER}],
                    "stop_reason": "end_turn", "stop_sequence": None,
                    "usage": {
                        "input_tokens": 21, "output_tokens": 40,
                        "cache_creation_input_tokens": CACHE_CREATED,
                        "cache_read_input_tokens": 0,
                    },
                }
            else:
                reply = {
                    "id": "chatcmpl-smoke", "object": "chat.completion", "created": 1,
                    "model": body.get("model"),
                    "choices": [{
                        "index": 0, "finish_reason": "stop",
                        "message": {"role": "assistant", "content": None if broken else ANSWER},
                    }],
                    "usage": {"prompt_tokens": 21, "completion_tokens": 40, "total_tokens": 61},
                }
            data = json.dumps(reply).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)


def main(argv: list[str]) -> int:
    broken = "--break" in argv
    try:
        import anthropic
        import openai
    except ImportError as error:
        # Missing is a failure, not a skip: this only runs where
        # requirements-eval.txt is installed, and silence here is how a bump
        # used to pass.
        print(f"✗ eval SDK not importable: {error} (pip install -r requirements-eval.txt)")
        return 1

    received: list = []
    server = _server(broken, received)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    # A proxy variable would send 127.0.0.1 somewhere else; a real key must
    # never be read by a smoke that is supposed to cost nothing.
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(key, None)
    os.environ.update({
        "ANTHROPIC_API_KEY": "sk-ant-smoke",
        "DEEPSEEK_API_KEY": "sk-smoke",
        "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{port}",
        "NO_PROXY": "127.0.0.1,localhost",
    })
    os.chdir(REPO)
    sys.path.insert(0, str(REPO / "scripts"))
    spec = importlib.util.spec_from_file_location("test_fidelity", REPO / "scripts" / "test-fidelity.py")
    fidelity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fidelity)
    fidelity.PROVIDERS["deepseek"]["base_url"] = f"http://127.0.0.1:{port}/v1"

    print(f"eval SDK smoke — anthropic {anthropic.__version__}, openai {openai.__version__}"
          f"{' (--break: server returns no answer text)' if broken else ''}")
    failures = 0

    def check(label: str, ok: bool) -> None:
        nonlocal failures
        print(f"  {'✓' if ok else '✗'} {label}")
        failures += 0 if ok else 1

    for provider, extra in (("anthropic", []), ("deepseek", ["--model", "deepseek-v4-flash"])):
        received.clear()
        sys.argv = ["test-fidelity.py", "--master", "master-huineng", "--provider", provider,
                    "--max-tests", "1", "--concurrency", "1", "--json", *extra]
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            fidelity.main()
        suite = json.loads(out.getvalue())[0]
        result = suite["results"][0]
        print(f"── {provider}: {result.get('status')}")

        check("the request reached the local server, not the internet", bool(received))
        if not received:
            continue
        path, body, headers = received[0]
        check("the reply was graded, not recorded as api_error",
              result.get("status") in ("PASS", "FAIL"))
        check("the answer text survived SDK parsing intact", result.get("response") == ANSWER)
        check("the citation audit ran on it",
              (suite.get("audit") or {}).get("citations_checked", 0) >= 1)
        check("model, max_tokens and messages were sent",
              {"model", "max_tokens", "messages"} <= set(body))
        check(f"a persona gets the default budget (sent {body.get('max_tokens')})",
              body.get("max_tokens") == fidelity.DEFAULT_MAX_OUTPUT_TOKENS)
        if provider == "anthropic":
            check(f"sent to /v1/messages (got {path})", path == "/v1/messages")
            check("the persona prompt carries cache_control",
                  (body.get("system") or [{}])[0].get("cache_control") == {"type": "ephemeral"})
            check("cache token usage was read back",
                  (suite.get("cache") or {}).get("created") == CACHE_CREATED)
            check("the pinned SDK is the one that sent it",
                  anthropic.__version__ in headers.get("user-agent", ""))
        else:
            check(f"sent to /v1/chat/completions (got {path})", path == "/v1/chat/completions")
            check("the key went in the Authorization header",
                  headers.get("authorization") == "Bearer sk-smoke")
            check("the pinned SDK is the one that sent it",
                  openai.__version__ in headers.get("user-agent", ""))

    # A teaching mode reads its sibling skills through the tool loop: the first
    # reply asks for a file, the second request must carry it back, the answer
    # after that is graded.
    for provider, extra in (("anthropic", []), ("deepseek", ["--model", "deepseek-v4-flash"])):
        received.clear()
        sys.argv = ["test-fidelity.py", "--master", "compare-masters", "--provider", provider,
                    "--max-tests", "1", "--concurrency", "1", "--json", *extra]
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            fidelity.main()
        suite = json.loads(out.getvalue())[0]
        result = suite["results"][0]
        print(f"── {provider} (teaching mode, file tools): {result.get('status')}")
        check("two requests: the tool call, then the answer", len(received) == 2)
        if len(received) < 2:
            continue
        first, second = received[0][1], received[1][1]
        tool_names = sorted(
            (tool.get("name") or tool.get("function", {}).get("name")) for tool in first.get("tools", [])
        )
        check("the tools were declared", tool_names == ["list_dir", "read_file"])
        check(f"a teaching mode gets its own budget (sent {first.get('max_tokens')})",
              first.get("max_tokens") == fidelity.TEACHING_MODE_MAX_OUTPUT_TOKENS)
        system = (first.get("system") or [{}])[0].get("text") if provider == "anthropic" \
            else first["messages"][0]["content"]
        check("the prompt names the skill's base directory",
              system.startswith("Base directory for this skill: ~/.claude/skills/compare-masters"))
        check("the file went back to the model", "慧能大师" in json.dumps(second, ensure_ascii=False))
        check("the reply was graded, not recorded as api_error",
              result.get("status") in ("PASS", "FAIL"))
        check("the answer text survived the loop intact", result.get("response") == ANSWER)
        check("the report says what was read",
              result.get("tool_calls") == [{"tool": "read_file", "path": TOOL_PATH, "ok": True}])
        check("and in how many rounds", result.get("tool_rounds") == 1)
        check("the suite says which instrument", suite.get("skill_tools") == ["read_file", "list_dir"])

    # master-debate dispatches each round to a fresh subagent (Task tool).
    for provider, extra in (("anthropic", []), ("deepseek", ["--model", "deepseek-v4-flash"])):
        received.clear()
        sys.argv = ["test-fidelity.py", "--master", "master-debate", "--provider", provider,
                    "--max-tests", "1", "--concurrency", "1", "--json", *extra]
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            fidelity.main()
        suite = json.loads(out.getvalue())[0]
        result = suite["results"][0]
        print(f"── {provider} (debate, subagent): {result.get('status')}")
        check("three requests: dispatch, the subagent, the answer", len(received) == 3)
        if len(received) < 3:
            continue
        sub = received[1][1]
        user_turns = [m for m in sub.get("messages", []) if m.get("role") == "user"]
        check("the subagent got a fresh context: only the orchestrator's prompt",
              _is_subagent(sub) and [m.get("content") for m in user_turns] == [SUBAGENT_PROMPT])
        check("the subagent cannot dispatch another",
              "Task" not in json.dumps(sub.get("tools", [])))
        check("its reply went back to the orchestrator",
              SUBAGENT_REPLY in json.dumps(received[2][1], ensure_ascii=False))
        check("the answer after it was graded", result.get("status") in ("PASS", "FAIL")
              and result.get("response") == ANSWER)
        check("the suite says which instrument",
              suite.get("skill_tools") == ["read_file", "list_dir", "Task"])

    server.shutdown()
    print(f"{'✓ eval SDK path intact' if not failures else f'✗ {failures} check(s) failed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
