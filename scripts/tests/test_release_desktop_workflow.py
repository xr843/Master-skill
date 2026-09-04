"""Contracts for packaging and publishing native desktop release assets."""

from __future__ import annotations

import subprocess
import tarfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "release-desktop.yml"
WORKFLOW = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _job(name: str) -> dict:
    job = WORKFLOW["jobs"].get(name)
    assert isinstance(job, dict), f"missing release workflow job: {name}"
    assert isinstance(job.get("steps"), list), f"job has no steps: {name}"
    return job


def _step(job_name: str, step_name: str) -> dict:
    matches = [
        step for step in _job(job_name)["steps"] if step.get("name") == step_name
    ]
    assert len(matches) == 1, f"expected one {job_name}/{step_name}, got {len(matches)}"
    return matches[0]


def test_unix_archive_preserves_executable_mode(tmp_path: Path):
    step = _step("build", "Package Unix archive")
    assert step.get("if") == "runner.os != 'Windows'"
    script = step["run"].replace(
        "${{ matrix.artifact_name }}", "master-skill-desktop-test"
    )
    dist = tmp_path / "dist"
    dist.mkdir()
    binary = dist / "master-skill-desktop-test"
    binary.write_text("binary", encoding="utf-8")
    binary.chmod(0o644)

    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", script],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    archive = dist / "master-skill-desktop-test.tar.gz"
    with tarfile.open(archive, "r:gz") as bundle:
        member = bundle.getmember("master-skill-desktop-test")
    assert member.mode & 0o111 == 0o111


def test_each_build_hands_all_staged_assets_to_the_assembler():
    step = _step("build", "Upload staged assets")
    assert step.get("uses") == (
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
    )
    assert step.get("if") is None
    assert step.get("with") == {
        "name": "desktop-assets-${{ matrix.artifact_name }}",
        "path": "dist/*",
        "if-no-files-found": "error",
    }
    assert all(step.get("name") != "Upload release asset" for step in _job("build")["steps"])


def test_assembler_downloads_every_matrix_leg_with_a_pinned_action():
    job = _job("assemble")
    assert job.get("needs") == "build"
    assert job.get("runs-on") == "ubuntu-latest"
    step = _step("assemble", "Download staged assets")
    assert step.get("uses") == (
        "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"
    )
    assert step.get("with") == {
        "pattern": "desktop-assets-*",
        "path": "dist",
        "merge-multiple": True,
    }


def test_only_assembler_receives_release_write_permission():
    assert WORKFLOW.get("permissions") == {"contents": "read"}
    assert _job("build").get("permissions") is None
    assert _job("assemble").get("permissions") == {"contents": "write"}


def test_assembler_generates_and_verifies_sorted_checksums(tmp_path: Path):
    step = _step("assemble", "Generate and verify SHA256SUMS")
    dist = tmp_path / "dist"
    dist.mkdir()
    expected_assets = [
        "master-skill-desktop-linux-x86_64",
        "master-skill-desktop-linux-x86_64.tar.gz",
        "master-skill-desktop-macos-aarch64",
        "master-skill-desktop-macos-aarch64.tar.gz",
        "master-skill-desktop-windows-x86_64.exe",
    ]
    for name in reversed(expected_assets):
        (dist / name).write_text(name, encoding="utf-8")

    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    manifest = (dist / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert [line.split("  ", 1)[1] for line in manifest] == sorted(expected_assets)
    assert all(len(line.split("  ", 1)[0]) == 64 for line in manifest)


def test_assembler_publishes_release_or_combined_dry_run_artifact():
    release = _step("assemble", "Upload complete release asset set")
    assert release.get("if") == "github.event_name == 'release'"
    assert release.get("env") == {"GH_TOKEN": "${{ github.token }}"}
    assert release.get("run") == (
        'gh release upload "$GITHUB_REF_NAME" dist/* --clobber'
    )

    dry_run = _step("assemble", "Upload combined workflow artifact")
    assert dry_run.get("if") == "github.event_name == 'workflow_dispatch'"
    assert dry_run.get("uses") == (
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
    )
    assert dry_run.get("with") == {
        "name": "master-skill-desktop-release-assets",
        "path": "dist/*",
        "if-no-files-found": "error",
    }
