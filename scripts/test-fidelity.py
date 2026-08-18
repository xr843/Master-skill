#!/usr/bin/env python3
"""Master-skill fidelity test runner.

Loads fidelity.jsonl for a master, sends each question through the Claude API
with the master's SKILL.md loaded as system prompt, and checks responses for
expected citations and keywords.

Usage:
    python scripts/test-fidelity.py --master master-zhiyi              # test one master
    python scripts/test-fidelity.py --master master-zhiyi --dry-run    # show test cases without calling API
    python scripts/test-fidelity.py --all                              # test all masters
    python scripts/test-fidelity.py --master master-zhiyi --model claude-sonnet-4-6  # specific model

Requires:
    - ANTHROPIC_API_KEY environment variable
    - pip install anthropic
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# verify_citations lives in this same scripts/ dir; reused so the
# `must_cite_only_existing_sources` assertion is actually enforced during graded
# runs (it was previously schema-validated but never evaluated).
from verify_citations import audit_answer, load_declared_ids

PREBUILT_DIR = Path(__file__).resolve().parent.parent / "prebuilt"
SCHEMA_VERSION = 1

# This project ships one prebuilt/ to five hosts (Claude Code, Cursor, Codex
# CLI, OpenCode, Gemini CLI), but every fidelity number it has produced came
# from one Anthropic model. A fixture measures whether the prompt induces the
# right behaviour, and that is a property of the prompt-and-model pair — so
# provider is an axis of the eval matrix, not a way to spend less.
#
# `api` selects the request/response shape. DeepSeek and Gemini both expose
# OpenAI-compatible endpoints, so one adapter covers them.
PROVIDERS: dict[str, dict] = {
    "anthropic": {
        "env": "ANTHROPIC_API_KEY",
        "api": "anthropic",
        "base_url": None,
        "default_model": "claude-sonnet-4-6",
        "models_url": "https://docs.claude.com/en/docs/about-claude/models",
    },
    "deepseek": {
        "env": "DEEPSEEK_API_KEY",
        "api": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": None,
        "models_url": "https://api-docs.deepseek.com/quick_start/pricing",
    },
    "gemini": {
        "env": "GEMINI_API_KEY",
        "api": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": None,
        "models_url": "https://ai.google.dev/gemini-api/docs/models",
    },
}

DEFAULT_PROVIDER = "anthropic"


def resolve_provider(name: str) -> dict:
    """Look up a provider spec, failing with the list of what is available."""
    try:
        return PROVIDERS[name]
    except KeyError:
        known = ", ".join(sorted(PROVIDERS))
        raise ValueError(f"unknown provider {name!r} — known providers: {known}") from None


def resolve_model(provider: str, explicit: str | None) -> str:
    """Pick the model id for a run.

    Anthropic keeps a default so existing invocations are unchanged. Every other
    provider must be named explicitly: a guessed model id committed to this repo
    would rot silently, and a run that cannot say which model produced it is not
    a reproducible measurement.
    """
    if explicit:
        return explicit
    spec = resolve_provider(provider)
    if spec["default_model"]:
        return spec["default_model"]
    raise ValueError(
        f"provider {provider!r} has no default model — pass --model explicitly. "
        f"Current model ids: {spec['models_url']}"
    )


def build_request(
    provider: str, model: str, system_prompt: str, question: str, max_tokens: int
) -> dict:
    """Build the request body for this provider's API shape."""
    spec = resolve_provider(provider)
    if spec["api"] == "anthropic":
        return {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": question}],
        }
    return {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    }


def extract_text(provider: str, response: object) -> str:
    """Pull the answer text out of this provider's response object.

    Raises rather than returning "" on an empty response: a blank answer scored
    as a normal case fails every must_mention and would be recorded as a persona
    defect when it is really a transport problem.
    """
    spec = resolve_provider(provider)
    if spec["api"] == "anthropic":
        blocks = getattr(response, "content", None) or []
        for block in blocks:
            if getattr(block, "type", None) == "text":
                return block.text
        raise ValueError(f"{provider}: response carried no text block")

    choices = getattr(response, "choices", None) or []
    if not choices:
        raise ValueError(f"{provider}: response carried no choices")
    content = getattr(choices[0].message, "content", None)
    if content is None:
        raise ValueError(f"{provider}: response message had no content")
    return content


def aggregation_conflicts(suites: list[dict]) -> list[str]:
    """Report why a set of suites must not be pooled into one number.

    Two models are two instruments. Averaging a Sonnet run with a DeepSeek run
    — or a Sonnet run with an Opus run — produces a figure that describes
    neither. Report per model instead.
    """
    seen = {
        (s.get("provider", DEFAULT_PROVIDER), s.get("model"))
        for s in suites
        if s.get("model")
    }
    if len(seen) <= 1:
        return []
    listed = ", ".join(f"{p}/{m}" for p, m in sorted(seen))
    return [
        "refusing to aggregate across instruments — these suites came from "
        f"different models ({listed}). Report a row per model."
    ]


def suite_common(
    master_name: str, dry_run: bool, outcome: str, provider: str = DEFAULT_PROVIDER
) -> dict:
    """Return fields shared by every fidelity JSON v1 suite."""
    return {
        "schema_version": SCHEMA_VERSION,
        "master": master_name,
        "provider": provider,
        "mode": "dry_run" if dry_run else "graded",
        "outcome": outcome,
    }


def suite_error(
    master_name: str, dry_run: bool, message: str, provider: str = DEFAULT_PROVIDER
) -> dict:
    """Return a fidelity JSON v1 suite for a precondition or execution error."""
    return {
        **suite_common(master_name, dry_run, "error", provider),
        "total": 0,
        "results": [],
        "error": message,
    }


def load_skill_context(master_dir: Path) -> str:
    """Load SKILL.md + references as a combined system prompt."""
    parts: list[str] = []

    skill = master_dir / "SKILL.md"
    if skill.exists():
        parts.append(skill.read_text(encoding="utf-8"))

    # Load references (voice.md, teaching.md)
    refs_dir = master_dir / "references"
    if refs_dir.exists():
        for f in sorted(refs_dir.glob("*.md")):
            parts.append(f"\n\n---\n# {f.stem}\n\n{f.read_text(encoding='utf-8')}")

    # Load source excerpts
    sources_dir = master_dir / "sources"
    if sources_dir.exists():
        for f in sorted(sources_dir.glob("*.md")):
            if f.name == "INDEX.md":
                continue
            parts.append(f"\n\n---\n# Source: {f.stem}\n\n{f.read_text(encoding='utf-8')}")

    return "\n".join(parts)


def load_tests(master_dir: Path) -> list[dict]:
    """Load fidelity.jsonl test cases."""
    fidelity_path = master_dir / "tests" / "fidelity.jsonl"
    if not fidelity_path.exists():
        return []
    tests = []
    for line_number, line in enumerate(
        fidelity_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if line.strip():
            try:
                test = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid fidelity.jsonl line {line_number}: {error.msg}"
                ) from error
            if not isinstance(test, dict):
                raise ValueError(
                    f"Invalid fidelity.jsonl line {line_number}: expected a JSON object"
                )
            question = test.get("q")
            if not isinstance(question, str) or not question.strip():
                raise ValueError(
                    f"Invalid fidelity.jsonl line {line_number}: "
                    "expected a non-empty string q"
                )
            tests.append(test)
    return tests


def _split_echoes(
    terms: list[str], response: str, question: str
) -> tuple[list[str], list[str]]:
    """Split forbidden-term hits into genuine violations and question echoes.

    ``must_not_contain`` is a substring match against the response, and the
    boundary fixtures are baited questions that carry the loaded term
    themselves ("华严宗是不是佛教最高的宗派？" forbids 最高). A response that
    quotes the bait in order to refuse it — "你问是不是最高，佛法无高下" —
    trips the match exactly as hard as an actual ranking does.

    Substring matching cannot tell those apart, so a hit whose term already
    appears in the fixture's own question is undecidable here. It is returned
    separately and does not fail the case; it flags the case for human review
    instead. A hit on a term the question never used is a real violation.
    """
    found: list[str] = []
    echoed: list[str] = []
    for term in terms:
        if term not in response:
            continue
        (echoed if term in question else found).append(term)
    return found, echoed


def check_response(
    response: str,
    test_case: dict,
    is_first_turn: bool = True,
    declared_ids: set[str] | None = None,
) -> dict:
    """Check a response against expected citations, mentions, and boundaries.

    Returns {passed: bool, missing_cites: [...], missing_mentions: [...],
             forbidden_found: [...], forbidden_echoed: [...],
             boundary_violations: [...], boundary_echoed: [...],
             needs_review: bool, fabricated_cites: [...]}.

    ``*_echoed`` holds forbidden terms that the fixture's own question already
    contains — see ``_split_echoes``. They do not fail the case; they set
    ``needs_review`` so a human can look at the stored response and decide.

    When the test sets ``must_cite_only_existing_sources`` and ``declared_ids``
    is supplied, every citation in the response must be either a declared
    offline source or carry a real ``fojin.app/texts/{id}`` link (B1 rule);
    anything else is a fabricated citation and fails the case.
    """
    missing_cites = []
    for cite in test_case.get("must_cite", []):
        if cite not in response:
            missing_cites.append(cite)

    missing_mentions = []
    for mention in test_case.get("must_mention", []):
        if mention not in response:
            missing_mentions.append(mention)

    question = test_case.get("q", "")

    # Boundary tests: must_not_contain
    forbidden_found, forbidden_echoed = _split_echoes(
        test_case.get("must_not_contain", []), response, question
    )

    # First-turn boundary: must_not_contain_first_turn
    boundary_violations: list[str] = []
    boundary_echoed: list[str] = []
    if is_first_turn:
        boundary_violations, boundary_echoed = _split_echoes(
            test_case.get("must_not_contain_first_turn", []), response, question
        )

    # B1: must_cite_only_existing_sources — no hallucinated citations
    fabricated_cites = []
    if test_case.get("must_cite_only_existing_sources") and declared_ids is not None:
        fabricated_cites = audit_answer(declared_ids, response)["fabricated"]

    passed = (
        len(missing_cites) == 0
        and len(missing_mentions) == 0
        and len(forbidden_found) == 0
        and len(boundary_violations) == 0
        and len(fabricated_cites) == 0
    )

    return {
        "passed": passed,
        "missing_cites": missing_cites,
        "missing_mentions": missing_mentions,
        "forbidden_found": forbidden_found,
        "forbidden_echoed": forbidden_echoed,
        "boundary_violations": boundary_violations,
        "boundary_echoed": boundary_echoed,
        "needs_review": bool(forbidden_echoed or boundary_echoed),
        "fabricated_cites": fabricated_cites,
    }


def result_entry(
    index: int, test: dict, check: dict, response_text: str
) -> dict:
    """Build one graded result record.

    Carries the response itself, not just its length. The first baseline
    stored only ``response_length``, which left every failure unadjudicable
    after the fact — there was no way to revisit a case and see what the
    persona actually said.
    """
    return {
        "index": index,
        "question": test["q"],
        "difficulty": test.get("difficulty", "unknown"),
        "test_type": test.get("test_type", "fidelity"),
        "status": "PASS" if check["passed"] else "FAIL",
        "missing_cites": check["missing_cites"],
        "missing_mentions": check["missing_mentions"],
        "forbidden_found": check["forbidden_found"],
        "forbidden_echoed": check["forbidden_echoed"],
        "boundary_violations": check["boundary_violations"],
        "boundary_echoed": check["boundary_echoed"],
        "fabricated_cites": check["fabricated_cites"],
        "needs_review": check["needs_review"],
        "response": response_text,
        "response_length": len(response_text),
    }


def run_tests(
    master_name: str,
    dry_run: bool = False,
    model: str | None = None,
    max_tests: int | None = None,
    quiet: bool = False,
    provider: str = DEFAULT_PROVIDER,
) -> dict:
    """Run fidelity tests for a master. Returns summary."""
    master_dir = PREBUILT_DIR / master_name
    if not master_dir.exists():
        return suite_error(
            master_name, dry_run, f"Master '{master_name}' not found", provider
        )

    try:
        tests = load_tests(master_dir)
    except (OSError, ValueError) as error:
        return suite_error(
            master_name, dry_run, f"Unable to load fidelity suite: {error}", provider
        )
    if not tests:
        return suite_error(
            master_name, dry_run, f"No fidelity.jsonl found for '{master_name}'", provider
        )

    if max_tests is not None and max_tests > 0:
        # Prefer easier/basic tests when capping — smoke suite should hit
        # the reliable floor, not the advanced stress cases.
        tests = sorted(
            tests,
            key=lambda t: {"basic": 0, "intermediate": 1, "advanced": 2}.get(
                t.get("difficulty", "intermediate"), 1
            ),
        )[:max_tests]

    results: list[dict] = []

    if dry_run:
        for i, test in enumerate(tests):
            results.append({
                "index": i,
                "question": test["q"],
                "must_cite": test.get("must_cite", []),
                "must_mention": test.get("must_mention", []),
                "difficulty": test.get("difficulty", "unknown"),
                "status": "dry_run",
            })
        return {
            **suite_common(master_name, dry_run, "completed", provider),
            "total": len(tests),
            "results": results,
        }

    # Load skill context
    system_prompt = load_skill_context(master_dir)

    try:
        spec = resolve_provider(provider)
        model = resolve_model(provider, model)
    except ValueError as error:
        return suite_error(master_name, dry_run, str(error), provider)

    api_key = os.environ.get(spec["env"])
    if not api_key:
        return suite_error(
            master_name, dry_run, f"{spec['env']} environment variable not set", provider
        )

    if spec["api"] == "anthropic":
        try:
            import anthropic
        except ImportError:
            return suite_error(
                master_name, dry_run,
                "anthropic package not installed. Run: pip install anthropic",
                provider,
            )
        client = anthropic.Anthropic(api_key=api_key)
        send = lambda body: client.messages.create(**body)  # noqa: E731
    else:
        try:
            import openai
        except ImportError:
            return suite_error(
                master_name, dry_run,
                "openai package not installed. Run: pip install openai",
                provider,
            )
        client = openai.OpenAI(api_key=api_key, base_url=spec["base_url"])
        send = lambda body: client.chat.completions.create(**body)  # noqa: E731

    # Declared offline sources, for the must_cite_only_existing_sources B1 check.
    try:
        declared_ids = load_declared_ids(master_name)
    except (ValueError, FileNotFoundError):
        declared_ids = None

    passed = 0
    failed = 0

    for i, test in enumerate(tests):
        if not quiet:
            print(f"  [{i+1}/{len(tests)}] {test['q'][:50]}...", end=" ", flush=True)

        try:
            response = send(
                build_request(provider, model, system_prompt, test["q"], 2048)
            )
            response_text = extract_text(provider, response)
        except Exception as e:
            results.append({
                "index": i,
                "question": test["q"],
                "status": "api_error",
                "error": str(e),
            })
            failed += 1
            if not quiet:
                print("API ERROR")
            continue

        check = check_response(
            response_text, test, is_first_turn=True, declared_ids=declared_ids
        )
        results.append(result_entry(i, test, check, response_text))

        if check["passed"]:
            passed += 1
            if not quiet:
                print("PASS (review)" if check["needs_review"] else "PASS")
        else:
            failed += 1
            failures = (check["missing_cites"] + check["missing_mentions"]
                        + check["forbidden_found"] + check["boundary_violations"])
            if not quiet:
                print(f"FAIL ({failures})")

    return {
        **suite_common(master_name, dry_run, "completed", provider),
        "model": model,
        "total": len(tests),
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed / len(tests) * 100:.0f}%" if tests else "N/A",
        "results": results,
    }


def results_failed(results: list[dict], dry_run: bool) -> bool:
    """Return whether collected fidelity results require a failing exit status."""
    if dry_run:
        return any("error" in suite for suite in results)
    return any(
        "error" in suite
        or suite.get("failed", 0) > 0
        or any(
            case.get("status") in {"FAIL", "api_error"}
            for case in suite.get("results", [])
        )
        for suite in results
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Master-skill fidelity test runner")
    parser.add_argument("--master", type=str, help="Test a specific master")
    parser.add_argument("--all", action="store_true", help="Test all masters with fidelity.jsonl")
    parser.add_argument("--dry-run", action="store_true", help="Show test cases without calling API")
    parser.add_argument(
        "--provider", type=str, default=DEFAULT_PROVIDER, choices=sorted(PROVIDERS),
        help="Which API to grade against (default: anthropic). Non-anthropic "
             "providers require --model.",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="Model id. Defaults to claude-sonnet-4-6 for --provider anthropic; "
             "required for every other provider.",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--max-tests",
        type=int,
        default=None,
        help="Cap the number of fixtures per master (smoke runs in CI use 1)",
    )
    args = parser.parse_args()

    if not args.master and not args.all:
        parser.error("Specify --master <name> or --all")

    if args.json and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if args.all:
        masters = sorted(
            d.name for d in PREBUILT_DIR.iterdir()
            if d.is_dir() and (d / "tests" / "fidelity.jsonl").exists()
        )
    else:
        masters = [args.master]

    all_results = []
    for master in masters:
        if not args.json:
            print(f"\n{'='*50}")
            print(f"Testing: {master}")
            print(f"{'='*50}")
        result = run_tests(
            master,
            dry_run=args.dry_run,
            model=args.model,
            provider=args.provider,
            max_tests=args.max_tests,
            quiet=args.json,
        )
        all_results.append(result)

        if not args.json and "error" not in result:
            print(f"\nResult: {result.get('passed', 0)}/{result['total']} passed "
                  f"({result.get('pass_rate', 'N/A')})")

    if args.json:
        print(json.dumps(all_results, indent=2, ensure_ascii=False))
    elif len(masters) > 1:
        conflicts = aggregation_conflicts(all_results)
        for conflict in conflicts:
            print(f"\n::warning:: {conflict}")

        print(f"\n{'='*50}")
        print("Overall Summary:")
        for r in all_results:
            if "error" in r:
                print(f"  {r.get('master', '?')}: {r['error']}")
            else:
                print(f"  {r['master']}: {r.get('passed', 0)}/{r['total']} ({r.get('pass_rate', 'N/A')})")

    return 1 if results_failed(all_results, args.dry_run) else 0


if __name__ == "__main__":
    raise SystemExit(main())
