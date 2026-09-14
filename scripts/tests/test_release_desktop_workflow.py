"""Contracts for packaging and publishing native desktop release assets."""

from __future__ import annotations

import re
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
    # The assembler also mints the Sigstore attestation, which needs an OIDC
    # token and attestation write. Still the only job holding anything beyond
    # read — the matrix builders remain read-only.
    assert _job("assemble").get("permissions") == {
        "contents": "write",
        "id-token": "write",
        "attestations": "write",
    }


def test_released_binaries_carry_a_build_attestation():
    """SHA256SUMS proves the assets match each other, not where they came from.

    Anyone able to upload an asset can upload a matching manifest beside it.
    Provenance is what ties a binary to this repo's workflow run, and it is
    what `npm publish --provenance` has given the JS half since v0.8 while the
    executable half had nothing.
    """
    step = _step("assemble", "Attest build provenance")
    assert step.get("if") == "github.event_name == 'release'"
    assert step.get("uses", "").startswith("actions/attest-build-provenance@")
    # SHA-pinned like every other action here.
    assert len(step["uses"].split("@", 1)[1].split()[0]) == 40
    subjects = step["with"]["subject-path"].split()
    # The binaries themselves, not the checksum file — signing a manifest only
    # moves the question one hop.
    assert "dist/SHA256SUMS" not in subjects
    assert len(subjects) == 3


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
        'gh release upload "$GITHUB_REF_NAME" dist/* --clobber --repo "$GITHUB_REPOSITORY"'
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


def test_gh_cli_in_a_job_without_checkout_names_its_repository():
    """`gh` finds the repository from a git remote; a job with no checkout has none.

    The assemble job uploaded release assets with no `--repo`. That step runs
    only on a release event, so the manual dispatch that verified all three
    builds skipped it, and v0.12.1 failed there with "not a git repository"
    after every build, checksum and attestation had succeeded. This scans every
    workflow, not just this one, for the same shape.
    """
    problems = []
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        for job_name, job in (workflow.get("jobs") or {}).items():
            steps = job.get("steps") or []
            if any(str(step.get("uses", "")).startswith("actions/checkout@") for step in steps):
                continue
            for step in steps:
                env = {**(job.get("env") or {}), **(step.get("env") or {})}
                for line in (step.get("run") or "").splitlines():
                    calls_gh = re.search(
                        r"(^|[\s;&|(])gh\s+(release|pr|issue|run|workflow|attestation)\b", line
                    )
                    names_repo = "--repo" in line or re.search(r"\s-R\s", line) or "GH_REPO" in env
                    if calls_gh and not names_repo:
                        problems.append(f"{path.name}:{job_name}:{step.get('name')}: {line.strip()}")
    assert not problems, "gh without a repository in a job with no checkout:\n" + "\n".join(problems)


def test_the_windows_build_is_smoke_tested_as_a_console_program():
    """No CI step ran the Windows binary. This one does, before its assets upload.

    It also pins the binary as a console program. A GUI-subsystem build, which
    would stop double-clicking from opening a console window, was tried on
    release-desktop run 34858072308. PowerShell does not wait for a GUI
    program: it closed the pipe, and `--help > help.txt` panicked with "failed
    printing to stdout: The pipe is being closed. (os error 232)".
    """
    main_rs = (ROOT / "desktop" / "src" / "main.rs").read_text(encoding="utf-8")
    assert "windows_subsystem" not in main_rs

    step = _step("build", "Smoke-test staged binary (Windows only)")
    assert step.get("if") == "runner.os == 'Windows'"
    assert step.get("shell") == "pwsh"
    script = step["run"]
    assert 'scripts/check-pe-subsystem.py "dist/${{ matrix.artifact_name }}" --expect 3' in script
    assert "--help > help.txt" in script
    usage = (ROOT / "desktop" / "src" / "desktop_args.rs").read_text(encoding="utf-8")
    assert '"Usage: master-skill-desktop' in usage and "Usage: master-skill-desktop" in script
    assert "$env:XDG_DATA_HOME" in script and "--baseline" in script

    names = [s.get("name") for s in _job("build")["steps"]]
    assert names.index("Smoke-test staged binary (Windows only)") < names.index("Upload staged assets")


def _covered_oses(condition: str | None) -> set[str]:
    """The runner.os values an `if:` of the forms used here selects."""
    oses = {"Linux", "Windows", "macOS"}
    if condition is None:
        return oses
    match = re.fullmatch(r"runner\.os (==|!=) '(\w+)'", condition.strip())
    assert match, f"unrecognised condition: {condition!r}"
    op, value = match.groups()
    assert value in oses, value
    return {value} if op == "==" else oses - {value}


def test_every_release_binary_is_run_before_its_assets_upload():
    """Each matrix leg's binary must actually be executed: `--help` and
    `--baseline`. For a long time only the Linux leg was, and the Windows binary
    shipped without ever running (its interpreter lookup was broken for a
    release); macOS ran in no CI step until 2026-09-14."""
    build = _job("build")
    legs = {entry["os"] for entry in build["strategy"]["matrix"]["include"]}
    runner_os = {"ubuntu-latest": "Linux", "windows-latest": "Windows", "macos-latest": "macOS"}
    assert {runner_os[leg] for leg in legs} == {"Linux", "Windows", "macOS"}

    names = [step.get("name") for step in build["steps"]]
    upload = names.index("Upload staged assets")
    coverage: dict[str, list[str]] = {"Linux": [], "Windows": [], "macOS": []}
    for index, step in enumerate(build["steps"]):
        if not str(step.get("name", "")).startswith("Smoke-test staged binary"):
            continue
        assert index < upload, f"{step['name']} runs after the assets upload"
        script = step.get("run", "")
        assert "--help" in script and "--baseline" in script, step["name"]
        for os_name in _covered_oses(step.get("if")):
            coverage[os_name].append(step["name"])
    for os_name, steps in coverage.items():
        assert len(steps) == 1, f"{os_name} is smoke-tested by {steps}"

