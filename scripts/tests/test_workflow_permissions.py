"""Least-privilege contracts for GitHub Actions token permissions."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_no_workflow_grants_an_oidc_token_to_every_job(path: Path):
    # A workflow-level `id-token: write` reaches every job, including ones that
    # only install dependencies and run tests. It belongs on the job that
    # exchanges the token (npm publish, attestation), nowhere else.
    workflow = _load(path)
    top = workflow.get("permissions") or {}
    assert isinstance(top, dict), f"{path.name}: permissions must be an explicit map"
    assert "id-token" not in top, f"{path.name}: id-token granted at workflow level"


def test_only_the_npm_publish_job_can_mint_an_oidc_token():
    workflow = _load(ROOT / ".github" / "workflows" / "npm-publish.yml")
    assert workflow.get("permissions") == {"contents": "read"}
    # No permissions block: `gate` inherits the read-only workflow default.
    assert workflow["jobs"]["gate"].get("permissions") is None
    # A job-level block replaces the workflow-level one, so contents: read is
    # restated for checkout. Nothing in the job reads release assets or writes.
    assert workflow["jobs"]["publish"].get("permissions") == {
        "contents": "read",
        "id-token": "write",
    }
    assert workflow["jobs"]["publish"]["environment"]["name"] == "npm"
