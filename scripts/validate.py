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


def _run_persona_fidelity_subcheck() -> list[str]:
    """Run the persona-fidelity validator as a sub-check.

    Imported lazily so that --master single-target lints stay fast and to
    avoid hard-coupling the two scripts at module load time.
    """
    try:
        import importlib.util

        spec_path = Path(__file__).resolve().parent / "validate-persona-fidelity.py"
        spec = importlib.util.spec_from_file_location("vpf", spec_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.validate(PREBUILT_DIR)
    except Exception as exc:  # pragma: no cover — surfaces to user
        return [f"persona-fidelity sub-check failed to run: {exc}"]


def _run_manifest_versions_subcheck() -> list[str]:
    """Run the platform-manifest version-drift gate as a sub-check.

    Hard gate (not advisory): any mismatch returns a non-empty error list
    and the parent validate.py will exit non-zero. Drift between the
    platform manifests must be fixed before release.
    """
    try:
        import importlib.util

        spec_path = (
            Path(__file__).resolve().parent / "check-manifest-versions.py"
        )
        spec = importlib.util.spec_from_file_location("cmv", spec_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        versions = mod.collect_versions()
        if not versions:
            return []
        unique = set(versions.values())
        if len(unique) <= 1:
            return []
        lines = ["manifest version drift detected:"]
        for path, v in sorted(versions.items()):
            lines.append(f"    {path}: {v}")
        return lines
    except Exception as exc:  # pragma: no cover
        return [f"manifest-versions sub-check failed to run: {exc}"]


def _run_lore_triggers_content_subcheck() -> list[str]:
    """Run the lore_triggers-content advisory validator as a sub-check.

    ADVISORY for v0.8.x: this collects warning lines but never causes
    validate.py to exit non-zero. It will become a hard gate in v0.9.
    Callers receive a list of warning strings to print.
    """
    try:
        import importlib.util

        spec_path = (
            Path(__file__).resolve().parent
            / "validate-lore-triggers-content.py"
        )
        spec = importlib.util.spec_from_file_location("vltc", spec_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        results = mod.validate(PREBUILT_DIR)
        warnings: list[str] = []
        for r in results:
            if not r["passed"]:
                warnings.append(
                    f"{r['master']} entry[{r['entry_idx']}] "
                    f"source_ref={r['source_ref']}: no high-similarity "
                    f"match (best file={r['best_file']}, "
                    f"lcs={r['best_lcs']} need {r['needed_lcs']}, "
                    f"ratio={r['best_ratio']})"
                )
            elif r.get("in_references_only"):
                warnings.append(
                    f"{r['master']} entry[{r['entry_idx']}] "
                    f"source_ref={r['source_ref']}: matched only in "
                    f"references/{r['ref_file']} — consider extending "
                    f"sources/excerpts to cover this quote"
                )
        return warnings
    except Exception as exc:  # pragma: no cover
        return [f"lore-triggers-content sub-check failed to run: {exc}"]


def _run_promptfoo_configs_subcheck() -> list[str]:
    """Run the persona promptfoo-config validator as a sub-check.

    Skips silently if tests/persona/ does not exist (older branch state
    predating v0.8 promptfoo work). Returns a list of error strings.
    """
    persona_dir = (
        Path(__file__).resolve().parent.parent / "tests" / "persona"
    )
    if not persona_dir.exists():
        return []
    try:
        import importlib.util

        spec_path = (
            Path(__file__).resolve().parent / "validate-promptfoo-configs.py"
        )
        spec = importlib.util.spec_from_file_location("vppc", spec_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.validate(persona_dir)
    except Exception as exc:  # pragma: no cover — surfaces to user
        return [f"promptfoo-configs sub-check failed to run: {exc}"]


def main():
    parser = argparse.ArgumentParser(description="Master-skill SKILL.md linter")
    parser.add_argument("--master", type=str, help="Lint a specific master only")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--skip-persona-fidelity",
        action="store_true",
        help="Skip the v0.8 persona-fidelity sub-check",
    )
    parser.add_argument(
        "--skip-promptfoo-configs",
        action="store_true",
        help="Skip the v0.8 promptfoo-configs sub-check",
    )
    parser.add_argument(
        "--skip-manifest-versions",
        action="store_true",
        help="Skip the v0.8 manifest version-drift gate",
    )
    parser.add_argument(
        "--skip-lore-triggers-content",
        action="store_true",
        help="Skip the v0.8 advisory lore_triggers-content validator",
    )
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

    # --- v0.8 persona-fidelity sub-check (runs only on full-tree lints) ---
    persona_errors: list[str] = []
    if not args.master and not args.skip_persona_fidelity:
        persona_errors = _run_persona_fidelity_subcheck()
        if persona_errors:
            has_errors = True

    # --- v0.8 promptfoo-configs sub-check (also full-tree only) ---
    promptfoo_errors: list[str] = []
    if not args.master and not args.skip_promptfoo_configs:
        promptfoo_errors = _run_promptfoo_configs_subcheck()
        if promptfoo_errors:
            has_errors = True

    # --- v0.8 manifest version-drift gate (full-tree only, HARD gate) ---
    manifest_errors: list[str] = []
    if not args.master and not args.skip_manifest_versions:
        manifest_errors = _run_manifest_versions_subcheck()
        if manifest_errors:
            has_errors = True

    # --- v0.8 lore_triggers-content advisory sub-check ---
    # ADVISORY ONLY: warnings printed but never affect has_errors.
    lore_warnings: list[str] = []
    if not args.master and not args.skip_lore_triggers_content:
        lore_warnings = _run_lore_triggers_content_subcheck()

    if args.json:
        out = {"skills": all_issues}
        if persona_errors:
            out["persona_fidelity"] = persona_errors
        if promptfoo_errors:
            out["promptfoo_configs"] = promptfoo_errors
        if manifest_errors:
            out["manifest_versions"] = manifest_errors
        if lore_warnings:
            out["lore_triggers_content_advisory"] = lore_warnings
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        nothing_to_report = (
            not all_issues
            and not persona_errors
            and not promptfoo_errors
            and not manifest_errors
            and not lore_warnings
        )
        if nothing_to_report:
            print(f"✅ All {len(dirs)} skills pass validation.")
        else:
            for name, issues in all_issues.items():
                for issue in issues:
                    print(issue)
            if persona_errors:
                print()
                print("Persona-fidelity sub-check (v0.8):")
                for e in persona_errors:
                    print(f"  [ERROR] {e}")
            if promptfoo_errors:
                print()
                print("Promptfoo-configs sub-check (v0.8):")
                for e in promptfoo_errors:
                    print(f"  [ERROR] {e}")
            if manifest_errors:
                print()
                print("Manifest version-drift gate (v0.8):")
                for e in manifest_errors:
                    print(f"  [ERROR] {e}")
            if lore_warnings:
                print()
                print(
                    "Lore-triggers content sub-check (v0.8, ADVISORY — "
                    "hard gate in v0.9):"
                )
                for w in lore_warnings:
                    print(f"  [WARN]  {w}")
            print()
            total_errors = sum(1 for issues in all_issues.values() for i in issues if "[ERROR]" in i)
            total_warns = sum(1 for issues in all_issues.values() for i in issues if "[WARN]" in i)
            total_errors += (
                len(persona_errors)
                + len(promptfoo_errors)
                + len(manifest_errors)
            )
            total_warns += len(lore_warnings)
            print(
                f"Summary: {total_errors} error(s), {total_warns} warning(s) "
                f"across {len(all_issues)} master(s)"
            )

    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
