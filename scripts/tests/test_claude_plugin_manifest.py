"""The Claude Code plugin must expose the skills its own hook announces.

Installed as a plugin (`claude plugin marketplace add xr843/Master-skill` then
`claude plugin install master-skill@master-skill`), the repository gave Claude
Code **one** skill. Measured 2026-09-16 with Claude Code 2.1.273 in an isolated
config dir, `claude plugin details master-skill` reported:

    Skills (1)  create-master
    Hooks (1)   SessionStart

and that SessionStart hook injects "Available Buddhist masters:" followed by
nineteen `/master-*` and mode commands. The model was told about commands the
plugin never registered.

`.claude-plugin/plugin.json` had no `skills` field. Claude Code scans the
plugin's `skills/` directory — this repository has none; its skills live in
`prebuilt/` — and loads a root `SKILL.md` only when there is neither a `skills/`
directory nor a `skills` field. `.cursor-plugin/plugin.json` had declared
`"skills": "./prebuilt/"` all along; the Claude manifest never did.

Declaring `"./prebuilt/"` alone was measured too: 19 skills, and `create-master`
disappeared, because a `skills` field switches off the root-`SKILL.md` fallback.
`["./", "./prebuilt/"]` gave all 20, identical to skill-catalog.json.

`discovered_skills` below encodes those measured rules, and
`test_the_model_reproduces_the_measurement` pins it to what Claude Code actually
did, so the model cannot drift into agreeing with a broken manifest.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / ".claude-plugin" / "plugin.json"
_NAME = re.compile(r"^name:[ \t]*(\S+)[ \t]*$", re.MULTILINE)


def _skill_name(skill_md: Path) -> str | None:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    frontmatter = text.split("---", 2)[1]
    match = _NAME.search(frontmatter)
    return match.group(1) if match else None


def discovered_skills(root: Path, manifest: dict) -> set[str]:
    """Skill names Claude Code registers for a plugin at `root`."""
    declared = manifest.get("skills")
    paths = [declared] if isinstance(declared, str) else list(declared or [])
    found: set[str] = set()
    for rel in ["skills/", *paths]:
        base = (root / rel).resolve()
        if not base.is_dir():
            continue
        candidates = sorted(base.glob("*/SKILL.md"))
        if rel != "skills/" and (base / "SKILL.md").is_file():
            candidates.append(base / "SKILL.md")
        found.update(n for n in map(_skill_name, candidates) if n)
    if declared is None and not (root / "skills").is_dir() and (root / "SKILL.md").is_file():
        name = _skill_name(root / "SKILL.md")
        if name:
            found.add(name)
    return found


def _catalog_slugs() -> set[str]:
    catalog = json.loads((ROOT / "skill-catalog.json").read_text(encoding="utf-8"))
    items = catalog["skills"] if isinstance(catalog, dict) else catalog
    return {item.get("slug") or item.get("name") for item in items}


def _hook_commands() -> set[str]:
    spec = importlib.util.spec_from_file_location("session_start", ROOT / "hooks" / "session_start.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    context = module.build_context(module.collect_masters(ROOT))
    return set(re.findall(r"^\s*/([a-z][a-z-]*) —", context, re.MULTILINE))


def test_the_model_reproduces_the_measurement():
    """Without a skills field, only the root SKILL.md — what `plugin details` showed."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest.pop("skills", None)
    assert discovered_skills(ROOT, manifest) == {"create-master"}

    manifest["skills"] = "./prebuilt/"
    only_prebuilt = discovered_skills(ROOT, manifest)
    assert "create-master" not in only_prebuilt
    assert len(only_prebuilt) == len(_catalog_slugs()) - 1


def test_the_plugin_exposes_every_catalog_skill():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert discovered_skills(ROOT, manifest) == _catalog_slugs()


def test_every_command_the_hook_announces_is_a_registered_skill():
    """The hook tells the model these exist; the manifest must make them exist."""
    announced = _hook_commands()
    assert len(announced) >= 20, f"hook context parse returned {len(announced)} commands — check the parser"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    missing = announced - discovered_skills(ROOT, manifest)
    assert not missing, f"hook announces commands the plugin does not register: {sorted(missing)}"
