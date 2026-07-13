"""Static regression checks for the repository validation workflow."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (
    ROOT / ".github" / "workflows" / "validate-and-test.yml"
).read_text(encoding="utf-8")


def test_workflow_runs_all_python_tests():
    assert "python -m pytest tests/ scripts/tests/ -v" in WORKFLOW


def test_workflow_has_no_advisory_quality_steps():
    assert "continue-on-error: true" not in WORKFLOW


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


def test_workflow_discovers_smoke_roster_from_metadata_sources():
    assert "sources" in WORKFLOW and "meta.json" in WORKFLOW


def test_workflow_records_missing_key_advisory_in_step_summary():
    assert 'echo "### Fidelity grading skipped' in WORKFLOW
