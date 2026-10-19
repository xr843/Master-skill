"""plugin/ is what Claude Code and Codex install, and what the directory scans.

Two gates hold it: `build-plugin-bundle.py --check` (plugin/ matches its
sources) and `check-directory-readiness.py` (it meets the directory's file
rules). Each is driven here with a broken copy to prove it goes red — a gate
that has only ever been seen green has not been shown to check anything.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "plugin"


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load("build_plugin_bundle", "scripts/build-plugin-bundle.py")
readiness = _load("check_directory_readiness", "scripts/check-directory-readiness.py")
manifest_tests = _load("claude_plugin_manifest_tests", "scripts/tests/test_claude_plugin_manifest.py")


def _statuses(base: Path) -> dict:
    return {name: status for status, name, _ in readiness.run(base)}


@pytest.fixture()
def fresh(tmp_path: Path) -> Path:
    dest = tmp_path / "plugin"
    builder.build(dest)
    shutil.copyfile(BUNDLE / "README.md", dest / "README.md")
    return dest


def test_marketplace_installs_the_bundle():
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    (entry,) = market["plugins"]
    assert entry["source"] == "./plugin"
    assert (ROOT / entry["source"] / ".claude-plugin" / "plugin.json").is_file()


def test_bundle_exposes_every_catalog_skill():
    manifest = json.loads((BUNDLE / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    found = manifest_tests.discovered_skills(BUNDLE, manifest)
    assert found == manifest_tests._catalog_slugs()
    assert len(found) == 21


def test_committed_bundle_is_in_sync():
    assert builder.main(["--check"]) == 0


@pytest.mark.parametrize("damage", ["edit", "delete", "add"])
def test_sync_check_goes_red(fresh: Path, tmp_path: Path, damage: str):
    expected = tmp_path / "expected"
    builder.build(expected)
    target = fresh / "skills" / "master-huineng" / "SKILL.md"
    if damage == "edit":
        target.write_text(target.read_text(encoding="utf-8") + "\nlocal edit\n", encoding="utf-8")
    elif damage == "delete":
        target.unlink()
    else:
        (fresh / "skills" / "master-huineng" / "stray.md").write_text("x", encoding="utf-8")
    problems = builder.diff(expected, fresh)
    assert problems and all("plugin/skills/master-huineng/" in p for p in problems)


def test_sync_check_ignores_personas_create_master_generated(fresh: Path, tmp_path: Path):
    expected = tmp_path / "expected"
    builder.build(expected)
    generated = fresh / "skills" / "create-master" / "masters" / "master-someone"
    generated.mkdir(parents=True)
    (generated / "SKILL.md").write_text("draft", encoding="utf-8")
    assert builder.diff(expected, fresh) == []


def test_bundle_carries_no_eval_fixtures():
    assert not list((BUNDLE / "skills").glob("*/tests"))


def test_committed_bundle_is_ready():
    results = readiness.run(BUNDLE)
    assert not [r for r in results if r[0] == "FAIL"], results


def test_readiness_goes_red_on_an_oversized_file(fresh: Path):
    (fresh / "skills" / "master-huineng" / "big.md").write_text("a" * (256 * 1024), encoding="utf-8")
    assert _statuses(fresh)["file-size"] == "FAIL"


def test_readiness_goes_red_on_too_many_files(fresh: Path):
    have = len(readiness._files(fresh))
    extra = fresh / "skills" / "master-help" / "extra"
    extra.mkdir()
    for i in range(513 - have):
        (extra / f"{i}.md").write_text("x", encoding="utf-8")
    assert _statuses(fresh)["file-count"] == "FAIL"


@pytest.mark.skipif(os.name == "nt", reason="creating symlinks needs privileges on Windows")
def test_readiness_goes_red_on_a_symlink(fresh: Path):
    os.symlink(fresh / "LICENSE", fresh / "skills" / "master-help" / "LICENSE-link")
    assert _statuses(fresh)["symlinks"] == "FAIL"


def test_readiness_goes_red_on_an_unpinned_hook_launcher(fresh: Path):
    hooks = json.loads((fresh / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"] = "npx master-skill doctor"
    (fresh / "hooks" / "hooks.json").write_text(json.dumps(hooks), encoding="utf-8")
    assert _statuses(fresh)["launchers-pinned"] == "FAIL"
    hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"] = "npx master-skill@0.13.0 doctor"
    (fresh / "hooks" / "hooks.json").write_text(json.dumps(hooks), encoding="utf-8")
    assert _statuses(fresh)["launchers-pinned"] == "PASS"


def test_readiness_goes_red_on_a_variable_in_a_hook(fresh: Path):
    hooks = json.loads((fresh / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"] = 'bash "$HOME/x.sh"'
    (fresh / "hooks" / "hooks.json").write_text(json.dumps(hooks), encoding="utf-8")
    assert _statuses(fresh)["hook-commands"] == "FAIL"


def test_readiness_goes_red_on_a_short_readme_and_no_license(fresh: Path):
    (fresh / "README.md").write_text("Too short.\n\n```\n" + "word " * 100 + "\n```\n", encoding="utf-8")
    (fresh / "LICENSE").unlink()
    manifest_path = fresh / ".claude-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("license")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    statuses = _statuses(fresh)
    assert statuses["readme"] == "FAIL"
    assert statuses["license"] == "FAIL"


def test_readiness_goes_red_on_a_reserved_name(fresh: Path):
    manifest_path = fresh / ".claude-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["name"] = "claude-master-skill"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert _statuses(fresh)["name-reserved"] == "FAIL"


def test_readiness_goes_red_on_a_credential(fresh: Path):
    (fresh / "skills" / "master-help" / "note.md").write_text(
        "token: ghp_" + "a" * 36 + "\n", encoding="utf-8")
    assert _statuses(fresh)["credentials"] == "FAIL"


@pytest.mark.skipif(shutil.which("bash") is None or os.name == "nt",
                    reason="runs the repository hook through bash")
def test_bundle_hook_says_what_the_repository_hook_says_to_claude_code():
    """The bundle replaces run-hook.cmd -> session-start with one echo; Claude
    Code must receive the same JSON either way."""
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(ROOT)}
    env.pop("COPILOT_CLI", None)
    env.pop("CURSOR_PLUGIN_ROOT", None)
    repo = subprocess.run(["bash", str(ROOT / "hooks" / "session-start")], env=env,
                          capture_output=True, text=True, check=True).stdout
    hooks = json.loads((BUNDLE / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    command = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    bundled = subprocess.run(["sh", "-c", command], capture_output=True, text=True, check=True).stdout
    assert json.loads(bundled) == json.loads(repo)


def test_bundled_query_script_finds_masters_under_skills(fresh: Path):
    out = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, sys.argv[1]); import _masterpaths as m; "
         "print(m.resolve_master_dir('huineng'))",
         str(fresh / "scripts")],
        capture_output=True, text=True, check=True).stdout.strip()
    assert Path(out) == fresh / "skills" / "master-huineng"
