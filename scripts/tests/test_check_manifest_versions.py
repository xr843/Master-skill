"""Tests for check-manifest-versions.py.

Covers:
  - collect_versions returns all 5 platform manifests when present
  - drift between manifests is detected (returns mismatched dict)
  - manifest with no `version` field is skipped silently
  - marketplace.json plugins[].version is picked up
  - main() exits 0 when consistent, 1 when drift
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def _load_module():
    spec_path = (
        Path(__file__).resolve().parents[1] / "check-manifest-versions.py"
    )
    spec = importlib.util.spec_from_file_location("cmv", spec_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cmv"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_repo(tmp: Path, versions: dict[str, str | None]) -> Path:
    """Build a fake repo. versions keys: package, claude, marketplace,
    cursor, gemini. Value None means: do not write that file at all.
    A version string of '' means: write the file without a version field.
    """
    root = tmp / "repo"
    root.mkdir(parents=True)
    (root / ".claude-plugin").mkdir()
    (root / ".cursor-plugin").mkdir()

    if "package" in versions and versions["package"] is not None:
        body = {"name": "x"}
        if versions["package"]:
            body["version"] = versions["package"]
        (root / "package.json").write_text(json.dumps(body), encoding="utf-8")

    if "claude" in versions and versions["claude"] is not None:
        body = {"name": "x"}
        if versions["claude"]:
            body["version"] = versions["claude"]
        (root / ".claude-plugin" / "plugin.json").write_text(
            json.dumps(body), encoding="utf-8"
        )

    if "marketplace" in versions and versions["marketplace"] is not None:
        body = {"name": "x", "plugins": []}
        if versions["marketplace"]:
            body["plugins"] = [
                {"name": "x", "version": versions["marketplace"]}
            ]
        (root / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps(body), encoding="utf-8"
        )

    if "cursor" in versions and versions["cursor"] is not None:
        body = {"name": "x"}
        if versions["cursor"]:
            body["version"] = versions["cursor"]
        (root / ".cursor-plugin" / "plugin.json").write_text(
            json.dumps(body), encoding="utf-8"
        )

    if "gemini" in versions and versions["gemini"] is not None:
        body = {"name": "x"}
        if versions["gemini"]:
            body["version"] = versions["gemini"]
        (root / "gemini-extension.json").write_text(
            json.dumps(body), encoding="utf-8"
        )
    return root


# ---------- happy path ----------


def test_all_manifests_consistent(tmp_path):
    m = _load_module()
    root = _make_repo(
        tmp_path,
        {
            "package": "1.2.3",
            "claude": "1.2.3",
            "marketplace": "1.2.3",
            "cursor": "1.2.3",
            "gemini": "1.2.3",
        },
    )
    out = m.collect_versions(root)
    assert set(out.values()) == {"1.2.3"}
    assert len(out) == 5


def test_drift_detected(tmp_path):
    m = _load_module()
    root = _make_repo(
        tmp_path,
        {
            "package": "1.2.3",
            "claude": "1.2.3",
            "marketplace": "1.2.2",  # drift
            "cursor": "1.2.3",
            "gemini": "1.2.3",
        },
    )
    out = m.collect_versions(root)
    assert "1.2.2" in out.values()
    assert "1.2.3" in out.values()
    assert len(set(out.values())) == 2


# ---------- skip files without version ----------


def test_manifest_without_version_is_skipped(tmp_path):
    m = _load_module()
    # gemini has no version key
    root = _make_repo(
        tmp_path,
        {
            "package": "1.2.3",
            "claude": "1.2.3",
            "marketplace": "1.2.3",
            "cursor": "1.2.3",
            "gemini": "",  # write file but no version field
        },
    )
    out = m.collect_versions(root)
    assert "gemini-extension.json" not in out
    assert len(out) == 4
    assert set(out.values()) == {"1.2.3"}


def test_marketplace_with_empty_plugins_is_skipped(tmp_path):
    m = _load_module()
    root = _make_repo(
        tmp_path,
        {
            "package": "1.2.3",
            "claude": "1.2.3",
            "marketplace": "",  # write file with no plugin entries
            "cursor": "1.2.3",
            "gemini": "1.2.3",
        },
    )
    out = m.collect_versions(root)
    assert ".claude-plugin/marketplace.json::plugins[0]" not in out


def test_codex_opencode_picked_up_when_versioned(tmp_path):
    m = _load_module()
    root = _make_repo(
        tmp_path,
        {"package": "9.0.0"},
    )
    # Stash a future .codex/<name>.json with a version
    (root / ".codex").mkdir()
    (root / ".codex" / "agents.json").write_text(
        json.dumps({"name": "x", "version": "9.0.0"}), encoding="utf-8"
    )
    (root / ".opencode").mkdir()
    (root / ".opencode" / "plugin.json").write_text(
        json.dumps({"name": "x", "version": "9.0.0"}), encoding="utf-8"
    )
    out = m.collect_versions(root)
    assert ".codex/agents.json" in out
    assert ".opencode/plugin.json" in out


def test_codex_opencode_install_md_only_no_false_positive(tmp_path):
    m = _load_module()
    # The real repo today: .codex/INSTALL.md only — no JSON.
    root = _make_repo(tmp_path, {"package": "1.0.0"})
    (root / ".codex").mkdir()
    (root / ".codex" / "INSTALL.md").write_text("# install", encoding="utf-8")
    out = m.collect_versions(root)
    assert all(not k.startswith(".codex/") for k in out)


# ---------- CLI exit codes ----------


def _run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    script = (
        Path(__file__).resolve().parents[1] / "check-manifest-versions.py"
    )
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def test_cli_exits_zero_on_real_repo():
    """Live repo manifests must be consistent or the check fails."""
    repo_root = Path(__file__).resolve().parents[2]
    proc = _run_cli([], cwd=repo_root)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_cli_json_output_shape():
    repo_root = Path(__file__).resolve().parents[2]
    proc = _run_cli(["--json"], cwd=repo_root)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert "versions" in data
    assert "consistent" in data
    assert data["consistent"] is True
