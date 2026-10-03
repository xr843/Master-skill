#!/usr/bin/env python3
"""Run this repo's gates from one declarative list.

`npm test` used to be a twenty-command `&&` chain in package.json, and the CI
validate job a second, hand-written copy of the same list. The two drifted the
way two copies always do: `validate-promptfoo-configs.py` ran only in
`npm test`, the hook tests only in CI. `GATES` below is now the only list.
`npm test` runs every gate not marked `not_default`; each CI step runs one
group with `--only`. `check-gate-liveness.py` holds both ends to it: every
entry script under scripts/ must be registered here (or declared exempt
there), and every gate here must be selected by some workflow that runs on
`pull_request`.

Every gate runs even after one fails, so a single run reports every failure;
the exit code is non-zero if any gate failed. A gate whose executable cannot
be found counts as failed, not skipped — a gate that did not run has not
passed.

Usage:
    python3 scripts/run-gates.py                    # every default gate (= npm test)
    python3 scripts/run-gates.py --only content     # one group, or one gate by name
    python3 scripts/run-gates.py --only hooks --only cli-tests
    python3 scripts/run-gates.py --list             # print the registry

Stdlib only and Python 3.9 compatible: the Python 3.9 CI job compiles every
script, and the gate list must be readable before any requirement is installed.
Output is ASCII only — Windows runners write stdout as cp1252.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, NamedTuple, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent

# Replaced at run time by the interpreter running this script, so a venv's
# python is the one every Python gate sees (`python3` on PATH may not be it).
PY = "{python}"


class Gate(NamedTuple):
    name: str
    group: str
    argv: Tuple[str, ...]
    # The gate passes only if the command exits non-zero: a self-test proving a
    # check can go red (`smoke-eval-sdk.py --break`).
    expect_failure: bool = False
    # Why a bare run (`npm test`) leaves this gate out. None = runs by default.
    # CI still runs it: every gate must be selected by a PR workflow.
    not_default: Optional[str] = None


_EVAL_ONLY = (
    "needs requirements-eval.txt (the pinned anthropic / openai SDKs), which a "
    "content contributor has no reason to install; CI's validate job runs it"
)

GATES: Tuple[Gate, ...] = (
    # --- eval-sdk: the grading path never runs in CI without a key, so these
    # read the SDK surface and push a real request through test-fidelity.py to
    # a local server. `--break` makes the server drop the answer text and must
    # fail: a smoke that cannot go red is a green tick, not a check.
    Gate("check-eval-sdk-surface", "eval-sdk",
         (PY, "scripts/check-eval-sdk-surface.py"), not_default=_EVAL_ONLY),
    Gate("smoke-eval-sdk", "eval-sdk",
         (PY, "scripts/smoke-eval-sdk.py"), not_default=_EVAL_ONLY),
    Gate("smoke-eval-sdk-break", "eval-sdk",
         (PY, "scripts/smoke-eval-sdk.py", "--break"),
         expect_failure=True, not_default=_EVAL_ONLY),

    # --- content: offline structural gates over prebuilt/ and the eval data.
    # The comments are what each gate's CI step used to say about why it exists.
    # validate.py also runs the v0.8 persona-fidelity and curriculum sub-checks.
    Gate("validate", "content", (PY, "scripts/validate.py", "--strict")),
    Gate("validate-fidelity", "content", (PY, "scripts/validate-fidelity.py")),
    Gate("validate-persona-fidelity", "content", (PY, "scripts/validate-persona-fidelity.py")),
    Gate("validate-citation-contract", "content", (PY, "scripts/validate-citation-contract.py")),
    # A persona must not instruct a citation its own contract forbids.
    # validate-citation-contract.py checks meta.json's fields and never reads
    # SKILL.md — which is how master-tsongkhapa shipped an instruction to cite
    # Toh 3861 while declaring five sources that do not include it.
    Gate("validate-citation-references", "content", (PY, "scripts/validate-citation-references.py")),
    # 3h/3i ask whether a quoted line exists in CBETA or in the compiled
    # teachings; neither asks whether the reader is told which book it came
    # from. master-nagarjuna's 「宁起我见积若须弥」 is real text, findable in
    # CBETA, and not his — it is in 《大宝积经》.
    Gate("validate-quote-attribution", "content", (PY, "scripts/validate-quote-attribution.py")),
    # Persona routing says 读 `references/teaching.md` §参话头 and the model
    # follows it literally. 18 of 198 such pointers named a section the file
    # does not have — master-milarepa sent 拙火 questions to a section its
    # excerpt file deliberately omits.
    Gate("validate-section-references", "content", (PY, "scripts/validate-section-references.py")),
    # These two existed, were unit-tested, and until 2026-09-16 ran nowhere on a
    # PR: only inside `npm test`, which only npm-publish.yml ran, on release.
    Gate("validate-citation-templates", "content", (PY, "scripts/validate-citation-templates.py")),
    Gate("validate-self-audit-sources", "content", (PY, "scripts/validate-self-audit-sources.py")),
    # A requirement may only be declared undecidable (`must_convey`) if a
    # committed adjudication ruled it an instrument artifact on real evidence.
    # Otherwise moving an inconvenient check there turns a red build green.
    Gate("validate-fixture-terms", "content", (PY, "scripts/validate-fixture-terms.py")),
    # A committed adjudication must prove it read the answers it ruled on: every
    # verdict carries a quote that must still be in the stored response, and the
    # headline numbers are recomputed from the verdicts rather than trusted.
    Gate("verify-adjudication", "content", (PY, "scripts/verify-adjudication.py")),
    Gate("validate-cross-critique", "content", (PY, "scripts/validate-cross-critique.py")),
    Gate("check-manifest-versions", "content", (PY, "scripts/check-manifest-versions.py")),
    Gate("validate-lore-triggers-content", "content",
         (PY, "scripts/validate-lore-triggers-content.py", "--strict")),
    # routing.json keyword sets stay pairwise disjoint. The pairing table this
    # replaced shipped three collisions (戒律, 道次第, 中观/空性), which made a
    # match depend on iteration order.
    Gate("validate-routing", "content", (PY, "scripts/validate-routing.py")),
    # Until this list existed it ran only in `npm test` and in persona-fidelity.yml,
    # whose paths filter skips most PRs — the validate job never ran it.
    Gate("validate-promptfoo-configs", "content", (PY, "scripts/validate-promptfoo-configs.py")),
    # Three shipped defects were one shape — a gate examined an empty set and
    # reported success. This asserts every gate examined something, and that
    # every gate is wired into this list and into a pull-request workflow.
    Gate("check-gate-liveness", "content", (PY, "scripts/check-gate-liveness.py")),

    # --- hooks
    Gate("test-session-start", "hooks", ("bash", "hooks/tests/test_session_start.sh")),
    Gate("test-run-hook", "hooks", ("bash", "hooks/tests/test_run_hook.sh")),
    # The cmd.exe half of run-hook.cmd. Skips itself where cmd.exe is absent,
    # so it is harmless on Linux; the Windows job is where it means something.
    Gate("test-run-hook-cmd", "hooks-cmd", ("bash", "hooks/tests/test_run_hook_cmd.sh")),

    # --- the rest
    Gate("pytest", "python-tests", (PY, "-m", "pytest", "tests/", "scripts/tests/", "-q")),
    Gate("fidelity-dry-run", "dry-run", (PY, "scripts/test-fidelity.py", "--all", "--dry-run")),
    Gate("cli", "cli-tests", ("node", "--test", "tests/cli.test.mjs")),
)


class Result(NamedTuple):
    gate: Gate
    ok: bool
    seconds: float
    detail: str


def groups(gates: Sequence[Gate] = GATES) -> List[str]:
    seen: List[str] = []
    for gate in gates:
        if gate.group not in seen:
            seen.append(gate.group)
    return seen


def select(tokens: Sequence[str], gates: Sequence[Gate] = GATES) -> List[Gate]:
    """Gates named by `tokens` (group or gate names), in registry order.

    No tokens means a bare run: every gate without `not_default`. Naming a
    gate or group explicitly runs it regardless. An unknown token raises
    ValueError rather than selecting nothing — `--only contnet` running zero
    gates and exiting 0 is the exact defect this repo keeps finding.
    """
    if not tokens:
        return [g for g in gates if g.not_default is None]
    known_groups = set(groups(gates))
    known_names = {g.name for g in gates}
    unknown = [t for t in tokens if t not in known_groups and t not in known_names]
    if unknown:
        raise ValueError(
            f"unknown gate or group: {', '.join(unknown)} "
            f"(groups: {', '.join(groups(gates))})"
        )
    wanted = set(tokens)
    return [g for g in gates if g.group in wanted or g.name in wanted]


def resolve(argv: Sequence[str]) -> List[str]:
    """Concrete argv: PY -> this interpreter, other programs -> a PATH lookup.

    The lookup matters on Windows: CreateProcess searches System32 before PATH,
    so a bare `bash` can start the WSL launcher instead of the Git bash the
    step selected. shutil.which only searches PATH.
    """
    first = argv[0]
    if first == PY:
        program = sys.executable
    else:
        found = shutil.which(first)
        if found is None:
            raise FileNotFoundError(f"{first!r} not found on PATH")
        program = found
    return [program, *argv[1:]]


def display(argv: Sequence[str]) -> str:
    return " ".join("python" if a == PY else a for a in argv)


def run_gate(gate: Gate, cwd: Path = ROOT) -> Result:
    start = time.monotonic()
    try:
        argv = resolve(gate.argv)
    except FileNotFoundError as exc:
        return Result(gate, False, time.monotonic() - start, f"not run: {exc}")
    # Output streams straight to this process's stdout/stderr — nothing is
    # captured, re-encoded or truncated.
    code = subprocess.call(argv, cwd=str(cwd))
    seconds = time.monotonic() - start
    if gate.expect_failure:
        if code == 0:
            return Result(gate, False, seconds, "exited 0, but this self-test must fail")
        return Result(gate, True, seconds, f"failed as required (exit {code})")
    if code != 0:
        return Result(gate, False, seconds, f"exit {code}")
    return Result(gate, True, seconds, "")


def run(gates: Sequence[Gate], cwd: Path = ROOT) -> List[Result]:
    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    results: List[Result] = []
    for index, gate in enumerate(gates, 1):
        print(f"\n==> [{index}/{len(gates)}] {gate.name} ({gate.group}): "
              f"{display(gate.argv)}", flush=True)
        result = run_gate(gate, cwd)
        results.append(result)
        status = "PASS" if result.ok else "FAIL"
        suffix = f" - {result.detail}" if result.detail else ""
        print(f"<== {status} {gate.name} in {result.seconds:.1f}s{suffix}", flush=True)
        if not result.ok and in_actions:
            print(f"::error title=Gate failed::{gate.name}: {result.detail}", flush=True)
    return results


def summarize(results: Sequence[Result]) -> str:
    lines = ["", "Gate summary:"]
    width = max((len(r.gate.name) for r in results), default=0)
    for r in results:
        status = "PASS" if r.ok else "FAIL"
        suffix = f"  {r.detail}" if r.detail and not r.ok else ""
        lines.append(f"  {status}  {r.seconds:7.1f}s  {r.gate.name.ljust(width)}  "
                     f"[{r.gate.group}]{suffix}")
    failed = [r for r in results if not r.ok]
    total = sum(r.seconds for r in results)
    lines.append(f"{len(results) - len(failed)} passed, {len(failed)} failed "
                 f"in {total:.1f}s")
    if failed:
        lines.append("FAILED: " + ", ".join(r.gate.name for r in failed))
    return "\n".join(lines)


def listing(gates: Sequence[Gate] = GATES) -> str:
    lines = []
    for group in groups(gates):
        lines.append(f"{group}:")
        for g in (g for g in gates if g.group == group):
            flags = []
            if g.not_default:
                flags.append("not in default run")
            if g.expect_failure:
                flags.append("must fail")
            note = f"  ({'; '.join(flags)})" if flags else ""
            lines.append(f"  {g.name}: {display(g.argv)}{note}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run this repo's gates from one declarative list."
    )
    parser.add_argument(
        "--only", action="append", default=[], metavar="GROUP|NAME",
        help="run only this group or gate (repeatable, or comma-separated)",
    )
    parser.add_argument("--list", action="store_true", help="print the registry and exit")
    args = parser.parse_args(argv)

    if args.list:
        print(listing())
        return 0

    tokens = [t.strip() for raw in args.only for t in raw.split(",") if t.strip()]
    try:
        chosen = select(tokens)
    except ValueError as exc:
        print(f"run-gates: {exc}", file=sys.stderr)
        return 2
    if not chosen:  # pragma: no cover — select() refuses unknown tokens
        print("run-gates: nothing selected", file=sys.stderr)
        return 2

    results = run(chosen)
    print(summarize(results), flush=True)
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
