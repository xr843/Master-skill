"""Static regression checks for the repository validation workflow."""

import os
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (
    ROOT / ".github" / "workflows" / "validate-and-test.yml"
).read_text(encoding="utf-8")


def test_workflow_runs_all_python_tests():
    assert "python -m pytest tests/ scripts/tests/ -v" in WORKFLOW


def test_workflow_has_no_advisory_quality_steps():
    assert "continue-on-error: true" not in WORKFLOW


def test_workflow_validates_citation_contract():
    assert "python scripts/validate-citation-contract.py" in WORKFLOW


def test_workflow_runs_strict_lore_validation():
    assert "python scripts/validate-lore-triggers-content.py --strict" in WORKFLOW


def test_workflow_checks_rust_formatting():
    assert "cargo fmt --manifest-path desktop/Cargo.toml -- --check" in WORKFLOW


def test_workflow_runs_strict_clippy():
    command = (
        "cargo clippy --locked --manifest-path desktop/Cargo.toml "
        "--all-targets -- -D warnings"
    )
    assert command in WORKFLOW


def test_workflow_does_not_use_fixed_smoke_roster():
    assert "master-nagarjuna master-xuanzang" not in WORKFLOW
    assert "MASTERS=(" not in WORKFLOW


def test_workflow_delegates_smoke_roster_discovery_to_selector():
    assert "python scripts/select-fidelity-smoke.py" in WORKFLOW
    assert "--prebuilt prebuilt" in WORKFLOW


def test_workflow_invokes_smoke_selector_with_checked_status():
    assert "if ! CHANGED=$(python scripts/select-fidelity-smoke.py" in WORKFLOW
    assert '"$(date +%j)"' in WORKFLOW


def test_smoke_selector_producer_failure_is_not_masked(tmp_path: Path):
    workflow = yaml.safe_load(WORKFLOW)
    pick_step = next(
        step
        for step in workflow["jobs"]["fidelity-smoke"]["steps"]
        if step.get("name") == "Pick smoke target"
    )
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


def test_workflow_records_missing_key_advisory_in_step_summary():
    assert 'echo "### Fidelity grading skipped' in WORKFLOW
