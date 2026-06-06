#!/usr/bin/env python3
"""Master-skill SKILL.md frontmatter linter.

Walks prebuilt/<master>/SKILL.md, validates required fields and conventions
per the Anthropic Agent Skills spec + Master-skill provenance extensions.

Usage:
    python scripts/validate.py                 # lint all masters
    python scripts/validate.py --master master-zhiyi  # lint one master
    python scripts/validate.py --strict        # fail on warnings too
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PREBUILT_DIR = Path(__file__).resolve().parent.parent / "prebuilt"

# --- Required and recommended fields ---

REQUIRED_FIELDS = {"name", "description"}
RECOMMENDED_FIELDS = {"version", "license", "lineage", "dates", "sources", "citation_format"}
# Fields not applicable to meta-skills (aggregate/comparison skills with no single lineage)
META_SKILL_EXCLUDED = {"lineage", "dates", "sources", "citation_format"}
MAX_DESCRIPTION_CHARS = 500
MAX_SKILL_LINES = 500


def parse_frontmatter(path: Path) -> tuple[dict, str, list[str]]:
    """Parse YAML frontmatter from a SKILL.md file.

    Returns (frontmatter_dict, body, raw_lines).
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text, lines

    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}, text, lines

    # Minimal YAML parse (no pyyaml dependency)
    fm: dict = {}
    current_key = None
    current_list: list | None = None
    for line in lines[1:end]:
        # list item
        if line.startswith("  - ") and current_key:
            if current_list is None:
                current_list = []
            item = line.strip().lstrip("- ").strip()
            # Try inline dict (title: xxx)
            if ":" in item:
                parts = item.split(":", 1)
                if current_list and isinstance(current_list[-1], dict):
                    current_list[-1][parts[0].strip()] = parts[1].strip()
                else:
                    current_list.append({parts[0].strip(): parts[1].strip()})
            else:
                current_list.append(item)
            continue
        # Save accumulated list
        if current_list is not None and current_key:
            fm[current_key] = current_list
            current_list = None
        # key: value
        match = re.match(r"^(\w[\w_-]*):\s*(.*)", line)
        if match:
            current_key = match.group(1)
            value = match.group(2).strip().strip('"').strip("'")
            if value:
                fm[current_key] = value
            # If empty value, might be a list starting next line
    # Flush last list
    if current_list is not None and current_key:
        fm[current_key] = current_list

    body = "\n".join(lines[end + 1 :])
    return fm, body, lines


def lint_master(master_dir: Path, strict: bool = False) -> list[str]:
    """Lint a single master directory. Returns list of issues."""
    issues: list[str] = []
    name = master_dir.name
    skill_path = master_dir / "SKILL.md"

    if not skill_path.exists():
        issues.append(f"[ERROR] {name}: missing SKILL.md")
        return issues

    fm, body, lines = parse_frontmatter(skill_path)

    # --- Required fields ---
    for field in REQUIRED_FIELDS:
        if field not in fm:
            issues.append(f"[ERROR] {name}: missing required field '{field}'")

    # --- Recommended fields ---
    kind = fm.get("kind", "master")
    for field in RECOMMENDED_FIELDS:
        if kind == "meta-skill" and field in META_SKILL_EXCLUDED:
            continue
        if field not in fm:
            issues.append(f"[WARN]  {name}: missing recommended field '{field}'")

    # --- Description length ---
    desc = fm.get("description", "")
    if isinstance(desc, str) and len(desc) > MAX_DESCRIPTION_CHARS:
        issues.append(f"[WARN]  {name}: description exceeds {MAX_DESCRIPTION_CHARS} chars ({len(desc)})")

    # --- SKILL.md line count ---
    if len(lines) > MAX_SKILL_LINES:
        issues.append(f"[WARN]  {name}: SKILL.md exceeds {MAX_SKILL_LINES} lines ({len(lines)})")

    # --- Sources validation ---
    sources = fm.get("sources")
    if isinstance(sources, list):
        for i, src in enumerate(sources):
            if isinstance(src, dict):
                if "title" not in src and "cbeta_id" not in src:
                    issues.append(f"[WARN]  {name}: sources[{i}] missing 'title' or 'cbeta_id'")

    # --- Directory structure checks ---
    # Meta-skills (e.g. compare-masters) borrow from other masters and have no own corpus
    if kind != "meta-skill":
        refs_dir = master_dir / "references"
        sources_dir = master_dir / "sources"

        if not refs_dir.exists():
            issues.append(f"[WARN]  {name}: missing references/ directory")
        else:
            if not (refs_dir / "voice.md").exists():
                issues.append(f"[WARN]  {name}: missing references/voice.md")
            if not (refs_dir / "teaching.md").exists():
                issues.append(f"[WARN]  {name}: missing references/teaching.md")

        if not sources_dir.exists():
            issues.append(f"[WARN]  {name}: missing sources/ directory")
        elif not list(sources_dir.glob("*.md")):
            issues.append(f"[WARN]  {name}: sources/ directory is empty")

    # --- Check for tests ---
    tests_dir = master_dir / "tests"
    if not tests_dir.exists() or not (tests_dir / "fidelity.jsonl").exists():
        issues.append(f"[WARN]  {name}: missing tests/fidelity.jsonl")

    # --- Strict mode: treat warnings as errors ---
    if strict:
        issues = [i.replace("[WARN] ", "[ERROR]") for i in issues]

    return issues


def main():
    parser = argparse.ArgumentParser(description="Master-skill SKILL.md linter")
    parser.add_argument("--master", type=str, help="Lint a specific master only")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.master:
        dirs = [PREBUILT_DIR / args.master]
        if not dirs[0].exists():
            print(f"Master '{args.master}' not found in {PREBUILT_DIR}")
            sys.exit(1)
    else:
        dirs = sorted(d for d in PREBUILT_DIR.iterdir() if d.is_dir())

    all_issues: dict[str, list[str]] = {}
    has_errors = False

    for d in dirs:
        issues = lint_master(d, strict=args.strict)
        if issues:
            all_issues[d.name] = issues
            if any("[ERROR]" in i for i in issues):
                has_errors = True

    if args.json:
        print(json.dumps(all_issues, indent=2, ensure_ascii=False))
    else:
        if not all_issues:
            print(f"✅ All {len(dirs)} skills pass validation.")
        else:
            for name, issues in all_issues.items():
                for issue in issues:
                    print(issue)
            print()
            total_errors = sum(1 for issues in all_issues.values() for i in issues if "[ERROR]" in i)
            total_warns = sum(1 for issues in all_issues.values() for i in issues if "[WARN]" in i)
            print(f"Summary: {total_errors} error(s), {total_warns} warning(s) across {len(all_issues)} master(s)")

    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
