"""Structural and behavior checks for the repository validation workflow."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "validate-and-test.yml"
WORKFLOW_TEXT = WORKFLOW_PATH.read_text(encoding="utf-8")


def _load_workflow_text(text: str) -> dict:
    workflow = yaml.safe_load(text)
    assert isinstance(workflow, dict)
    assert isinstance(workflow.get("jobs"), dict)
    return workflow


def _job(workflow: dict, job_name: str) -> dict:
    job = workflow["jobs"].get(job_name)
    assert isinstance(job, dict), f"missing workflow job: {job_name}"
    assert isinstance(job.get("steps"), list), f"job has no steps: {job_name}"
    return job


def _step(workflow: dict, job_name: str, step_name: str) -> dict:
    matches = [
        step
        for step in _job(workflow, job_name)["steps"]
        if step.get("name") == step_name
    ]
    assert len(matches) == 1, f"expected one {job_name}/{step_name} step, got {len(matches)}"
    return matches[0]


def _assert_hard(step: dict) -> None:
    assert step.get("continue-on-error") not in (True, "true")


WORKFLOW = _load_workflow_text(WORKFLOW_TEXT)


def test_free_text_tokens_cannot_substitute_for_workflow_structure():
    fake = _load_workflow_text(
        """\
name: fake
jobs:
  validate:
    steps:
      - name: comments only
        run: echo 'python -m pytest tests/ scripts/tests/ -v'
"""
    )

    with pytest.raises(AssertionError, match="Run Python tests"):
        _step(fake, "validate", "Run Python tests")


def test_workflow_has_no_softened_steps():
    for job_name, job in WORKFLOW["jobs"].items():
        for step in job.get("steps", []):
            assert step.get("continue-on-error") not in (True, "true"), (
                f"softened workflow step in {job_name}: {step.get('name', step.get('uses'))}"
            )


@pytest.mark.parametrize(
    ("step_name", "command"),
    [
        ("Run Python tests", "python -m pytest tests/ scripts/tests/ -v"),
        ("Validate citation contracts", "python scripts/validate-citation-contract.py"),
        (
            "Validate lore_triggers content (v0.8 — hard gate)",
            "python scripts/validate-lore-triggers-content.py --strict",
        ),
    ],
)
def test_validate_job_contains_hard_gate_commands(step_name: str, command: str):
    step = _step(WORKFLOW, "validate", step_name)
    assert step.get("run") == command
    _assert_hard(step)


@pytest.mark.parametrize(
    ("step_name", "command"),
    [
        ("Check desktop formatting", "cargo fmt --manifest-path desktop/Cargo.toml -- --check"),
        (
            "Lint desktop app",
            "cargo clippy --locked --manifest-path desktop/Cargo.toml "
            "--all-targets -- -D warnings",
        ),
        ("Test desktop app", "cargo test --locked --manifest-path desktop/Cargo.toml"),
        ("Build desktop app", "cargo build --locked --manifest-path desktop/Cargo.toml"),
    ],
)
def test_desktop_job_contains_hard_gate_commands(step_name: str, command: str):
    step = _step(WORKFLOW, "desktop-rust", step_name)
    assert step.get("run") == command
    _assert_hard(step)


def test_desktop_quality_gates_run_before_tests_and_build():
    step_names = [step.get("name") for step in _job(WORKFLOW, "desktop-rust")["steps"]]
    assert step_names.index("Check desktop formatting") < step_names.index("Lint desktop app")
    assert step_names.index("Lint desktop app") < step_names.index("Test desktop app")
    assert step_names.index("Test desktop app") < step_names.index("Build desktop app")


def test_windows_cli_job_installs_the_generator_python_runtime():
    job = _job(WORKFLOW, "cli-windows")
    uses = [step.get("uses", "") for step in job["steps"]]
    assert any(use.startswith("actions/setup-python@") for use in uses)
    install = _step(WORKFLOW, "cli-windows", "Install generator dependencies")
    assert install.get("run") == "python -m pip install -r requirements.txt"
    _assert_hard(install)


def test_python39_job_compiles_and_runs_the_four_generator_cli_steps():
    job = _job(WORKFLOW, "python-compat")
    setup = next(
        step
        for step in job["steps"]
        if str(step.get("uses", "")).startswith("actions/setup-python@")
    )
    assert setup.get("with", {}).get("python-version") == "3.9"
    smoke = _step(WORKFLOW, "python-compat", "Run Python 3.9 generator smoke")
    command = smoke["run"]
    assert "python -m compileall -q tools scripts" in command
    assert "sutra_collector.py" in command
    assert "verify_sources.py --check-links" in command
    assert "master_builder.py" in command
    assert "verify_sources.py --final-check" in command
    _assert_hard(smoke)


def test_push_paths_include_distribution_and_generator_runtime():
    triggers = WORKFLOW.get("on", WORKFLOW.get(True))
    assert isinstance(triggers, dict)
    paths = set(triggers["push"]["paths"])
    assert {
        "skill-catalog.json",
        "SKILL.md",
        "references/**",
        "ETHICS.md",
        "requirements.txt",
        "README.md",
        "README_EN.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        ".claude-plugin/**",
        ".cursor-plugin/**",
        "gemini-extension.json",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/**",
    } <= paths


def test_pick_step_uses_checked_selector_without_fixed_roster():
    checkout = next(
        step
        for step in _job(WORKFLOW, "fidelity-smoke")["steps"]
        if str(step.get("uses", "")).startswith("actions/checkout@")
    )
    assert checkout.get("with", {}).get("fetch-depth") == 0
    step = _step(WORKFLOW, "fidelity-smoke", "Pick smoke target")
    script = step["run"]
    assert "if ! CHANGED=$(python scripts/select-fidelity-smoke.py" in script
    assert "if ! DIFF_OUTPUT=$(git diff --name-only" in script
    assert "CHANGED_CANDIDATES" in script
    assert "--prebuilt prebuilt" in script
    assert '--day-of-year "$(date +%j)"' in script
    assert "MASTERS=(" not in script
    _assert_hard(step)


def test_smoke_selector_producer_failure_is_not_masked(tmp_path: Path):
    pick_step = _step(WORKFLOW, "fidelity-smoke", "Pick smoke target")
    script = pick_step["run"].replace("${{ github.base_ref || 'main' }}", "main")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_python = bin_dir / "python"
    fake_python.write_text(
        "#!/bin/sh\nprintf 'master-partial\\n'\nexit 7\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    output_path = tmp_path / "github-output"
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["GITHUB_OUTPUT"] = str(output_path)

    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", script],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert not output_path.exists()


def test_smoke_git_diff_failure_is_not_masked(tmp_path: Path):
    pick_step = _step(WORKFLOW, "fidelity-smoke", "Pick smoke target")
    script = pick_step["run"].replace("${{ github.base_ref || 'main' }}", "main")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_git = bin_dir / "git"
    fake_git.write_text("#!/bin/sh\nexit 7\n", encoding="utf-8")
    fake_git.chmod(0o755)
    fake_python = bin_dir / "python"
    fake_python.write_text(
        "#!/bin/sh\nprintf 'master-alpha\\n'\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    output_path = tmp_path / "github-output"
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["GITHUB_OUTPUT"] = str(output_path)

    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", script],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "git diff failed" in result.stdout
    assert not output_path.exists()


@pytest.mark.parametrize(
    ("job_name", "step_name"),
    [
        ("fidelity-smoke", "Run fidelity smoke"),
        ("fidelity-full", "Run fidelity tests"),
    ],
)
def test_each_fidelity_no_key_branch_records_step_summary(job_name: str, step_name: str):
    job = _job(WORKFLOW, job_name)
    assert job.get("needs") == "validate"
    step = _step(WORKFLOW, job_name, step_name)
    script = step["run"]
    assert 'if [ -z "${ANTHROPIC_API_KEY:-}" ]; then' in script
    assert script.count('echo "### Fidelity grading skipped"') == 1
    assert '} >> "$GITHUB_STEP_SUMMARY"' in script
    _assert_hard(step)
