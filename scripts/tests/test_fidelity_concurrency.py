"""Fixtures are graded in parallel — and the report must not be able to tell.

Grading ran one fixture at a time for no reason but inertia. The cost is on
record: `eval/reports/0.10.1-c697d5d.json` spent 04:06:00Z → 04:50:39Z to grade
84 fixtures (~31s each), and a full 211-fixture DeepSeek sweep took 1h55m. A
sweep that takes two hours is a sweep you run twice a year.

Parallelism is only safe here because each fixture is one stateless request
graded against its own expectations. These assert the two things that could
still go wrong: that completion order never leaks into the output, and that one
bad fixture cannot take the pool down with it.
"""

from __future__ import annotations

import importlib.util
import sys
import threading
import time
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def fidelity():
    scripts_dir = ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location(
        "test_fidelity_concurrency_mod", scripts_dir / "test-fidelity.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["test_fidelity_concurrency_mod"] = module
    spec.loader.exec_module(module)
    return module


def _answer(text: str):
    block = types.SimpleNamespace(type="text", text=text)
    return types.SimpleNamespace(content=[block], stop_reason="end_turn")


def _install_fake_anthropic(monkeypatch, *, on_create):
    """Stand in for the anthropic SDK so no network or key is involved."""
    messages = types.SimpleNamespace(create=on_create)
    client = types.SimpleNamespace(messages=messages)
    module = types.SimpleNamespace(Anthropic=lambda **_: client)
    monkeypatch.setitem(sys.modules, "anthropic", module)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")


def test_results_come_back_in_fixture_order_regardless_of_completion_order(
    fidelity, monkeypatch
):
    """Reports are diffed across runs — completion order must not leak in.

    The stub finishes the *last* question first and the first question last, so
    a run that appended results as they arrived would come back reversed.
    """
    seen: list[str] = []
    order_lock = threading.Lock()

    def create(**body):
        question = body["messages"][0]["content"]
        with order_lock:
            seen.append(question)
        # Later questions return sooner.
        time.sleep(0.02 * (len(body["messages"][0]["content"]) % 3))
        return _answer(f"echo::{question}")

    _install_fake_anthropic(monkeypatch, on_create=create)
    suite = fidelity.run_tests("yinguang", quiet=True, concurrency=4)

    assert "error" not in suite, suite.get("error")
    indices = [r["index"] for r in suite["results"]]
    assert indices == sorted(indices), "results must be ordered by fixture index"
    assert len(indices) == len(set(indices)), "no fixture graded twice"
    assert suite["total"] == len(indices)


def test_a_failing_fixture_does_not_take_the_pool_down(fidelity, monkeypatch):
    """One provider exception is one api_error, not a lost run."""
    calls = {"n": 0}
    lock = threading.Lock()

    def create(**body):
        with lock:
            calls["n"] += 1
            mine = calls["n"]
        if mine == 2:
            raise RuntimeError("simulated provider blowup")
        return _answer("回答：南无阿弥陀佛。【《印光法师文钞》，T00n0000】")

    _install_fake_anthropic(monkeypatch, on_create=create)
    suite = fidelity.run_tests("yinguang", quiet=True, concurrency=4)

    assert "error" not in suite
    statuses = [r["status"] for r in suite["results"]]
    assert statuses.count("api_error") == 1
    # Every other fixture still produced an entry.
    assert len(suite["results"]) == suite["total"]


def test_concurrency_actually_overlaps_requests(fidelity, monkeypatch):
    """Guards against a 'concurrent' path that quietly serialises.

    Counts peak simultaneous in-flight calls rather than wall-clock, so a slow
    or loaded machine cannot make this flaky.
    """
    state = {"in_flight": 0, "peak": 0}
    lock = threading.Lock()

    def create(**_body):
        with lock:
            state["in_flight"] += 1
            state["peak"] = max(state["peak"], state["in_flight"])
        time.sleep(0.05)
        with lock:
            state["in_flight"] -= 1
        return _answer("回答")

    _install_fake_anthropic(monkeypatch, on_create=create)
    suite = fidelity.run_tests("yinguang", quiet=True, concurrency=4)
    assert suite["total"] >= 2, "this master needs >1 fixture for the test to mean anything"
    assert state["peak"] > 1, "requests never overlapped — the pool is not running"


def test_concurrency_one_is_still_serial(fidelity, monkeypatch):
    """--concurrency 1 must reproduce the old behaviour exactly."""
    state = {"in_flight": 0, "peak": 0}
    lock = threading.Lock()

    def create(**_body):
        with lock:
            state["in_flight"] += 1
            state["peak"] = max(state["peak"], state["in_flight"])
        time.sleep(0.01)
        with lock:
            state["in_flight"] -= 1
        return _answer("回答")

    _install_fake_anthropic(monkeypatch, on_create=create)
    suite = fidelity.run_tests("yinguang", quiet=True, concurrency=1)
    assert state["peak"] == 1
    assert suite["concurrency"] == 1


def test_the_run_records_its_own_concurrency(fidelity, monkeypatch):
    """A concurrent run can meet rate limits a serial one never would.

    That arrives as api_errors indistinguishable from real provider failures,
    so the setting is part of the instrument and belongs in the reading.
    """
    _install_fake_anthropic(monkeypatch, on_create=lambda **_: _answer("回答"))
    suite = fidelity.run_tests("yinguang", quiet=True, concurrency=3)
    # Clamped to the fixture count when there are fewer fixtures than workers.
    assert suite["concurrency"] == min(3, suite["total"])


# --------------------------------------------------------------------------
# Provider error strings are written to reports that get committed.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "401 unauthorized for sk-ant-api03-AAAAAAAAAAAAAAAAAAAA",
        "bad key AIzaSyDdIdontexistdontexist12345",
        "header was Bearer abcdefghijklmnop.qrstuv",
        'body {"api_key": "supersecretvalue123"}',
    ],
)
def test_credential_shapes_are_stripped_from_error_text(fidelity, raw):
    assert "[REDACTED]" in fidelity.redact_secrets(raw)
    for token in ("sk-ant-api03-AAAAAAAAAAAAAAAAAAAA", "AIzaSyDdIdontexistdontexist12345",
                  "abcdefghijklmnop.qrstuv", "supersecretvalue123"):
        if token in raw:
            assert token not in fidelity.redact_secrets(raw)


def test_redaction_keeps_the_diagnosable_part_of_an_error(fidelity):
    """The 2026-08-18 run was diagnosed from these strings — don't gut them."""
    raw = ("Error code: 400 - {'type': 'error', 'error': {'type': "
           "'invalid_request_error', 'message': 'Your credit balance is too low'}}")
    assert fidelity.redact_secrets(raw) == raw


def test_an_api_error_entry_is_redacted_on_the_way_into_the_report(
    fidelity, monkeypatch
):
    def create(**_body):
        raise RuntimeError("401 from provider, key sk-ant-api03-LEAKEDLEAKEDLEAKED")

    _install_fake_anthropic(monkeypatch, on_create=create)
    suite = fidelity.run_tests("yinguang", quiet=True, concurrency=2)
    errors = [r["error"] for r in suite["results"] if r["status"] == "api_error"]
    assert errors, "expected api_error entries"
    assert all("sk-ant-api03-LEAKED" not in e for e in errors)
    assert all("[REDACTED]" in e for e in errors)


# --------------------------------------------------------------------------
# A paid sweep has to be stoppable, and one bad fixture must not end it.
#
# Both are regressions the parallel rewrite introduced against the serial loop
# it replaced, and both were found by review rather than by these tests.
# --------------------------------------------------------------------------


def test_ctrl_c_cancels_the_calls_that_have_not_been_made_yet(fidelity, monkeypatch):
    """`with ThreadPoolExecutor(...)` drains every queued call on the way out.

    All fixtures are submitted up front, so an interrupt used to bill the whole
    sweep anyway — 211 calls on the 1h55m run — and then discard the verdicts
    already paid for. The serial loop stopped at the next iteration.
    """
    made = []
    lock = threading.Lock()

    def create(**body):
        with lock:
            made.append(body["messages"][0]["content"])
            n = len(made)
        if n == 1:
            raise KeyboardInterrupt
        time.sleep(0.01)
        return _answer("回答")

    _install_fake_anthropic(monkeypatch, on_create=create)
    suite = fidelity.run_tests("yinguang", quiet=True, concurrency=2)

    assert suite["interrupted"] is True
    assert len(made) < suite["total"], (
        f"every one of {suite['total']} calls was still made after the interrupt"
    )


def test_an_interrupted_run_says_so(fidelity, monkeypatch):
    """A partial result set must not read like a complete one."""
    _install_fake_anthropic(monkeypatch, on_create=lambda **_: _answer("回答"))
    suite = fidelity.run_tests("yinguang", quiet=True, concurrency=2)
    assert suite["interrupted"] is False


def test_a_grader_exception_is_one_entry_not_a_dead_run(fidelity, monkeypatch):
    """`check_response` sat OUTSIDE grade_one's try.

    So a grader crash — e.g. `int()` on an absurd citation number, which raises
    past 4300 digits — came back through `future.result()` in the main thread
    and killed `run_tests` after every API call had already been billed, while
    grade_one's docstring promised one bad fixture could not take the pool down.
    """
    original = fidelity.check_response
    calls = {"n": 0}

    def exploding(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("Exceeds the limit (4300 digits)")
        return original(*args, **kwargs)

    monkeypatch.setattr(fidelity, "check_response", exploding)
    _install_fake_anthropic(monkeypatch, on_create=lambda **_: _answer("回答"))
    suite = fidelity.run_tests("yinguang", quiet=True, concurrency=1)

    assert "error" not in suite
    statuses = [r["status"] for r in suite["results"]]
    assert statuses.count("grader_error") == 1
    assert len(suite["results"]) == suite["total"], "every other fixture still graded"
