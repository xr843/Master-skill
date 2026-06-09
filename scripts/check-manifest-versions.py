#!/usr/bin/env python3
"""Check that the version field is consistent across all platform manifests.

Master-skill ships to 5 ecosystems and each carries its own manifest with a
`version` field. PR #26 (post-mortem) showed that the manifests can drift
silently when only some are bumped — users on Cursor would get a stale
version while npm users got the new one. This script is a hard CI gate to
catch drift before a release goes out.

Files checked (all relative to repo root):

  - package.json                          (canonical npm version)
  - .claude-plugin/plugin.json            (Claude Code plugin)
  - .claude-plugin/marketplace.json       (Claude Code marketplace — nested
                                          `plugins[*].version`)
  - .cursor-plugin/plugin.json            (Cursor)
  - gemini-extension.json                 (Gemini CLI)

Any *.json under .codex/ or .opencode/ that carries a `version` field is
also picked up (currently those directories ship INSTALL.md only, but
this future-proofs the check).

Files without a `version` field are skipped.

Usage
-----
    python scripts/check-manifest-versions.py            # exit 1 on drift
    python scripts/check-manifest-versions.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def collect_versions(root: Path = ROOT) -> dict[str, str]:
    """Return {relative_path: version_string} for every manifest with one."""
    versions: dict[str, str] = {}

    # Canonical: package.json
    pkg = _read_json(root / "package.json")
    if pkg and "version" in pkg:
        versions["package.json"] = pkg["version"]

    # Flat single-version manifests
    flat_paths = [
        root / ".claude-plugin" / "plugin.json",
        root / ".cursor-plugin" / "plugin.json",
        root / "gemini-extension.json",
    ]
    for p in flat_paths:
        if not p.exists():
            continue
        data = _read_json(p)
        if data is None:
            continue
        v = data.get("version")
        if isinstance(v, str):
            versions[str(p.relative_to(root))] = v

    # Marketplace manifest: nested plugins[*].version
    mp = root / ".claude-plugin" / "marketplace.json"
    if mp.exists():
        data = _read_json(mp)
        if data:
            plugins = data.get("plugins", []) or []
            for i, plugin in enumerate(plugins):
                if isinstance(plugin, dict) and "version" in plugin:
                    rel = f"{mp.relative_to(root)}::plugins[{i}]"
                    versions[rel] = plugin["version"]

    # Codex / OpenCode future-proofing — pick up any *.json with version
    for sub in (".codex", ".opencode"):
        d = root / sub
        if not d.exists():
            continue
        for p in sorted(d.glob("*.json")):
            data = _read_json(p)
            if data is None:
                continue
            v = data.get("version")
            if isinstance(v, str):
                versions[str(p.relative_to(root))] = v

    return versions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check version consistency across platform manifests"
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    versions = collect_versions()
    if not versions:
        print("No version fields found in any manifest — nothing to check.")
        return 0

    unique = set(versions.values())

    if args.json:
        out = {
            "versions": versions,
            "consistent": len(unique) == 1,
            "unique_count": len(unique),
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        if len(unique) > 1:
            print("Manifest version drift detected:")
            for path, v in sorted(versions.items()):
                print(f"  {path}: {v}")
            print()
            print(
                f"Found {len(unique)} distinct versions across "
                f"{len(versions)} manifests — they must all match."
            )
        else:
            v = next(iter(unique))
            print(
                f"All {len(versions)} manifest version fields agree on {v}."
            )
            for path in sorted(versions):
                print(f"  {path}: {versions[path]}")

    return 0 if len(unique) == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
