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

PREBUILT_DIR = Path(__file__).resolve().parent.parent / "prebuilt"


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
    for line in fidelity_path.read_text(encoding="utf-8").strip().splitlines():
        if line.strip():
            tests.append(json.loads(line))
    return tests


def check_response(response: str, test_case: dict, is_first_turn: bool = True) -> dict:
    """Check a response against expected citations, mentions, and boundaries.

    Returns {passed: bool, missing_cites: [...], missing_mentions: [...],
             forbidden_found: [...], boundary_violations: [...]}.
    """
    missing_cites = []
    for cite in test_case.get("must_cite", []):
        if cite not in response:
            missing_cites.append(cite)

    missing_mentions = []
    for mention in test_case.get("must_mention", []):
        if mention not in response:
            missing_mentions.append(mention)

    # Boundary tests: must_not_contain
    forbidden_found = []
    for forbidden in test_case.get("must_not_contain", []):
        if forbidden in response:
            forbidden_found.append(forbidden)

    # First-turn boundary: must_not_contain_first_turn
    boundary_violations = []
    if is_first_turn:
        for forbidden in test_case.get("must_not_contain_first_turn", []):
            if forbidden in response:
                boundary_violations.append(forbidden)

    passed = (
        len(missing_cites) == 0
        and len(missing_mentions) == 0
        and len(forbidden_found) == 0
        and len(boundary_violations) == 0
    )

    return {
        "passed": passed,
        "missing_cites": missing_cites,
        "missing_mentions": missing_mentions,
        "forbidden_found": forbidden_found,
        "boundary_violations": boundary_violations,
    }


def run_tests(
    master_name: str,
    dry_run: bool = False,
    model: str = "claude-sonnet-4-6",
    max_tests: int | None = None,
) -> dict:
    """Run fidelity tests for a master. Returns summary."""
    master_dir = PREBUILT_DIR / master_name
    if not master_dir.exists():
        return {"error": f"Master '{master_name}' not found"}

    tests = load_tests(master_dir)
    if not tests:
        return {"error": f"No fidelity.jsonl found for '{master_name}'"}

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
        return {"master": master_name, "total": len(tests), "results": results}

    # Load skill context
    system_prompt = load_skill_context(master_dir)

    # Import anthropic
    try:
        import anthropic
    except ImportError:
        return {"error": "anthropic package not installed. Run: pip install anthropic"}

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY environment variable not set"}

    client = anthropic.Anthropic(api_key=api_key)

    passed = 0
    failed = 0

    for i, test in enumerate(tests):
        print(f"  [{i+1}/{len(tests)}] {test['q'][:50]}...", end=" ", flush=True)

        try:
            message = client.messages.create(
                model=model,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": test["q"]}],
            )
            response_text = message.content[0].text
        except Exception as e:
            results.append({
                "index": i,
                "question": test["q"],
                "status": "api_error",
                "error": str(e),
            })
            failed += 1
            print("API ERROR")
            continue

        check = check_response(response_text, test, is_first_turn=True)
        status = "PASS" if check["passed"] else "FAIL"

        result_entry = {
            "index": i,
            "question": test["q"],
            "difficulty": test.get("difficulty", "unknown"),
            "test_type": test.get("test_type", "fidelity"),
            "status": status,
            "missing_cites": check["missing_cites"],
            "missing_mentions": check["missing_mentions"],
            "forbidden_found": check["forbidden_found"],
            "boundary_violations": check["boundary_violations"],
            "response_length": len(response_text),
        }
        results.append(result_entry)

        if check["passed"]:
            passed += 1
            print("PASS")
        else:
            failed += 1
            failures = (check["missing_cites"] + check["missing_mentions"]
                        + check["forbidden_found"] + check["boundary_violations"])
            print(f"FAIL ({failures})")

    return {
        "master": master_name,
        "model": model,
        "total": len(tests),
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed / len(tests) * 100:.0f}%" if tests else "N/A",
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Master-skill fidelity test runner")
    parser.add_argument("--master", type=str, help="Test a specific master")
    parser.add_argument("--all", action="store_true", help="Test all masters with fidelity.jsonl")
    parser.add_argument("--dry-run", action="store_true", help="Show test cases without calling API")
    parser.add_argument("--model", type=str, default="claude-sonnet-4-6", help="Claude model to use")
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

    if args.all:
        masters = sorted(
            d.name for d in PREBUILT_DIR.iterdir()
            if d.is_dir() and (d / "tests" / "fidelity.jsonl").exists()
        )
    else:
        masters = [args.master]

    all_results = []
    for master in masters:
        print(f"\n{'='*50}")
        print(f"Testing: {master}")
        print(f"{'='*50}")
        result = run_tests(
            master, dry_run=args.dry_run, model=args.model, max_tests=args.max_tests
        )
        all_results.append(result)

        if not args.json and "error" not in result:
            print(f"\nResult: {result.get('passed', 0)}/{result['total']} passed "
                  f"({result.get('pass_rate', 'N/A')})")

    if args.json:
        print(json.dumps(all_results, indent=2, ensure_ascii=False))
    elif len(masters) > 1:
        print(f"\n{'='*50}")
        print("Overall Summary:")
        for r in all_results:
            if "error" in r:
                print(f"  {r.get('master', '?')}: {r['error']}")
            else:
                print(f"  {r['master']}: {r.get('passed', 0)}/{r['total']} ({r.get('pass_rate', 'N/A')})")


if __name__ == "__main__":
    main()
