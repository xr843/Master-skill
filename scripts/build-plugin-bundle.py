#!/usr/bin/env python3
"""Build plugin/ — the self-contained plugin folder Claude Code and Codex install.

Why a separate folder. The marketplace entry used to point at the repository
root ("source": "./"), so every install copied the whole repository: 447 files,
eight of them over 256 KiB (eval reports, CHANGELOG.md), plus the eval
harness, desktop app and CI scripts. Anthropic's plugin directory holds a
version for a reviewer when the plugin folder has a non-image file of 256 KiB or
more, or more than 512 files, and installs "only the plugin folder", which must
therefore hold everything the plugin runs
(https://claude.com/docs/plugins/pre-submission-checklist). plugin/ is that
folder: the 21 skills from skill-catalog.json, the files they read at run time,
the SessionStart hook, README.md and LICENSE.

plugin/ is generated and committed. It is never edited by hand except
plugin/README.md, which this script leaves alone. The sources stay where they
are — prebuilt/, the root SKILL.md and the generator bundle the catalog
declares — and `--check` (a content gate) rebuilds into a temporary folder and
fails on any difference, so plugin/ cannot drift from them.

Layout:
    plugin/.claude-plugin/plugin.json   root manifest minus `skills` (default skills/)
    plugin/skills/<name>/               every catalog skill; personas without tests/
    plugin/scripts/                     the offline helpers personas name (cite.py, query.py)
    plugin/routing.json                 master-help says the plugin install can read it
    plugin/hooks/hooks.json             SessionStart: the static Claude Code pointer
    plugin/LICENSE                      copy of the root LICENSE
    plugin/PRIVACY.md                   copy of the root PRIVACY.md
    plugin/README.md                    hand-written listing text (not generated)

The hook. In the repository the hook goes through hooks/run-hook.cmd, a
cmd/bash polyglot that runs a bash script that may run python. Under Claude
Code that chain always ends in one static line (CLAUDE_POINTER in
hooks/session_start.py). The directory holds a version for a reviewer when a
hook in a subfolder plugin runs scripts with shell variables or calls to other
files, so the bundle emits the same JSON with a single `echo '<json>'`, which
sh, Git Bash and PowerShell all print verbatim — Claude Code runs command
hooks in Git Bash on Windows, or PowerShell when Git Bash is absent.

Usage:
    python3 scripts/build-plugin-bundle.py           # (re)write plugin/
    python3 scripts/build-plugin-bundle.py --check   # exit 1 if plugin/ is stale

Stdlib only, Python 3.9 compatible, ASCII output.
"""

from __future__ import annotations

import argparse
import filecmp
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "plugin"

# Hand-written files inside plugin/ that the build neither writes nor deletes.
HAND_WRITTEN = ("README.md",)

# Offline helpers the persona SKILL.md files tell the model to run
# (`scripts/cite.py`, `scripts/query.py`) and the two modules they import.
# Written without ".py": check-gate-liveness.py counts a string constant equal
# to a script's filename as a call to it, and this file copies these scripts,
# it does not run them (cite.py and query.py are declared NOT_A_PR_GATE).
RUNTIME_SCRIPTS = tuple(f"{stem}.py" for stem in ("cite", "query", "_masterpaths", "_skill_io"))

# Repository-root files the bundle carries at its own root.
ROOT_FILES = ("routing.json", "LICENSE", "PRIVACY.md")

# Never copied: eval fixtures, bytecode, OS litter.
SKIP_NAMES = {"__pycache__", ".DS_Store", "Thumbs.db", "desktop.ini"}
SKIP_SUFFIXES = (".pyc",)

# Manifest fields carried over from .claude-plugin/plugin.json. `skills` is
# dropped: the bundle uses the default skills/ directory.
MANIFEST_FIELDS = (
    "name", "description", "version", "author", "homepage", "repository",
    "license", "keywords",
)


def _skip(path: Path) -> bool:
    return path.name in SKIP_NAMES or path.name.endswith(SKIP_SUFFIXES)


def _copy_tree(src: Path, dest: Path, skip_top: tuple = ()) -> None:
    for entry in sorted(src.iterdir()):
        if _skip(entry) or entry.is_symlink():
            continue
        if entry.name in skip_top:
            continue
        target = dest / entry.name
        if entry.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            _copy_tree(entry, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(entry, target)


def _copy_generator(skill: dict, dest: Path) -> None:
    src = ROOT / skill["source"]
    dest.mkdir(parents=True, exist_ok=True)
    for rel in skill["bundle_paths"]:
        s = src / rel
        if rel == "masters":
            # User-generated personas live here; ship only the placeholder.
            (dest / "masters").mkdir(parents=True, exist_ok=True)
            keep = s / ".gitkeep"
            if keep.is_file():
                shutil.copyfile(keep, dest / "masters" / ".gitkeep")
            continue
        if s.is_dir():
            (dest / rel).mkdir(parents=True, exist_ok=True)
            _copy_tree(s, dest / rel)
        else:
            shutil.copyfile(s, dest / rel)


def claude_pointer() -> str:
    spec = importlib.util.spec_from_file_location(
        "session_start_for_bundle", ROOT / "hooks" / "session_start.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CLAUDE_POINTER


def hook_payload() -> str:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": claude_pointer(),
        }
    }
    text = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    # Single-quoted for sh and PowerShell alike: neither may appear inside.
    for bad in ("'", "\\", "$", "`"):
        if bad in text:
            raise SystemExit(f"hook payload contains {bad!r}; cannot single-quote it")
    return text


def hooks_json() -> dict:
    return {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup|clear|compact",
                    "hooks": [
                        {"type": "command", "command": f"echo '{hook_payload()}'"}
                    ],
                }
            ]
        }
    }


def manifest() -> dict:
    source = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    return {k: source[k] for k in MANIFEST_FIELDS if k in source}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(dest: Path) -> None:
    """Write every generated file of the bundle into `dest`."""
    catalog = json.loads((ROOT / "skill-catalog.json").read_text(encoding="utf-8"))
    for skill in catalog["skills"]:
        target = dest / "skills" / skill["name"]
        if skill.get("kind") == "generator":
            _copy_generator(skill, target)
        else:
            target.mkdir(parents=True, exist_ok=True)
            _copy_tree(ROOT / skill["source"], target, skip_top=("tests",))
    for name in RUNTIME_SCRIPTS:
        (dest / "scripts").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "scripts" / name, dest / "scripts" / name)
    for name in ROOT_FILES:
        shutil.copyfile(ROOT / name, dest / name)
    _write_json(dest / ".claude-plugin" / "plugin.json", manifest())
    # The directory reads .claude-plugin/icon.png inside the plugin folder as the
    # listing icon, and only the first time the plugin is saved in the portal.
    shutil.copyfile(ROOT / ".claude-plugin" / "icon.png", dest / ".claude-plugin" / "icon.png")
    _write_json(dest / "hooks" / "hooks.json", hooks_json())


def _files(base: Path) -> Dict[str, Path]:
    out: Dict[str, Path] = {}
    if not base.is_dir():
        return out
    for p in sorted(base.rglob("*")):
        rel = p.relative_to(base).as_posix()
        parts = rel.split("/")
        if any(part in SKIP_NAMES for part in parts) or rel.endswith(SKIP_SUFFIXES):
            continue
        # create-master writes generated personas under masters/<name>/.
        if rel.startswith("skills/create-master/masters/") and rel.count("/") > 3:
            continue
        if rel in HAND_WRITTEN:
            continue
        if p.is_file() or p.is_symlink():
            out[rel] = p
    return out


def diff(expected: Path, actual: Path) -> List[str]:
    want, have = _files(expected), _files(actual)
    problems = []
    for rel in sorted(set(want) - set(have)):
        problems.append(f"missing  plugin/{rel}")
    for rel in sorted(set(have) - set(want)):
        problems.append(f"stale    plugin/{rel}")
    for rel in sorted(set(want) & set(have)):
        if have[rel].is_symlink() or not filecmp.cmp(want[rel], have[rel], shallow=False):
            problems.append(f"differs  plugin/{rel}")
    for name in HAND_WRITTEN:
        if not (actual / name).is_file():
            problems.append(f"missing  plugin/{name} (hand-written; not generated)")
    return problems


def write(dest: Path = BUNDLE) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "plugin"
        build(fresh)
        # Remove every generated file, keep the hand-written ones and any
        # personas a local create-master run generated.
        for path in _files(dest).values():
            path.unlink()
        if dest.is_dir():
            for d in sorted((p for p in dest.rglob("*") if p.is_dir()), reverse=True):
                if not any(d.iterdir()):
                    d.rmdir()
        for rel, path in _files(fresh).items():
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="rebuild into a temp dir and fail if plugin/ differs")
    args = parser.parse_args(argv)
    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / "plugin"
            build(fresh)
            problems = diff(fresh, BUNDLE)
            count = len(_files(fresh))
        if problems:
            print(f"FAIL plugin/ is out of sync with its sources ({len(problems)} difference(s)):")
            for line in problems[:50]:
                print(f"  {line}")
            if len(problems) > 50:
                print(f"  ... and {len(problems) - 50} more")
            print("Run: python3 scripts/build-plugin-bundle.py")
            return 1
        print(f"PASS plugin/ matches its sources ({count} generated files compared)")
        return 0
    write()
    print(f"wrote {BUNDLE.relative_to(ROOT)}/ ({len(_files(BUNDLE))} generated files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
