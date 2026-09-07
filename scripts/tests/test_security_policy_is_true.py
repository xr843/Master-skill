"""SECURITY.md makes checkable claims. Nothing was checking them.

Three of its statements were false when this test was written: it listed a
required status check that branch protection does not require, promised
per-file `.sha256` release assets the workflow cannot produce, and certified a
test count that was 27 low. A security policy that drifts is worse than a
thinner one that holds, because readers act on it.

The count is not asserted here. It was simply removed from the docs instead:
a bare number in a changelog is a historical note that goes stale on the next
PR that adds a test, so policing it forever buys friction rather than safety.
What is asserted below are claims about the repository as it stands now, each
of which would be acted on by a reader and each of which was wrong.

These assert only what the repository can verify offline. Branch-protection
contents need the GitHub API and a token, so the claim is instead pinned to the
job names that produce those checks — a rename still breaks the policy, and
this catches the rename.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
SECURITY = (ROOT / "SECURITY.md").read_text(encoding="utf-8")


def _workflow(name: str) -> dict:
    return yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"))


def _job_names(workflow: dict) -> set[str]:
    return {
        (job.get("name") or job_id)
        for job_id, job in (workflow.get("jobs") or {}).items()
        if isinstance(job, dict)
    }


@pytest.mark.parametrize(
    ("claimed", "workflow"),
    [
        ("Validate SKILL.md & fidelity structure", "validate-and-test.yml"),
        ("Fidelity smoke (1 master × 1 fixture)", "validate-and-test.yml"),
    ],
)
def test_every_required_check_named_in_the_policy_still_exists(claimed, workflow):
    """A renamed job silently un-requires itself: branch protection matches the
    full check-run name, so the policy and the workflow must agree."""
    assert claimed in SECURITY, f"SECURITY.md no longer names {claimed!r}"
    assert claimed in _job_names(_workflow(workflow)), (
        f"SECURITY.md lists {claimed!r} as a required check, but no job in "
        f"{workflow} produces that name"
    )


def test_the_policy_does_not_promise_release_assets_the_workflow_cannot_produce():
    """It promised per-file `.sha256`; #157 ships one `SHA256SUMS` manifest and
    its asset-count contract fails on any extra file."""
    release = (ROOT / ".github" / "workflows" / "release-desktop.yml").read_text(encoding="utf-8")
    for promised in re.findall(r"`([A-Za-z0-9_.*-]+\.sha256)`", SECURITY):
        assert promised in release, (
            f"SECURITY.md promises {promised}, which release-desktop.yml never writes"
        )
    if "SHA256SUMS" in SECURITY:
        assert "SHA256SUMS" in release


def test_the_attestation_command_names_a_file_that_is_actually_attested():
    """`gh attestation verify <file>` fails on an unattested asset, and only
    the three raw binaries are signed — not the two tarballs the READMEs
    recommend downloading."""
    release = _workflow("release-desktop.yml")
    steps = release["jobs"]["assemble"]["steps"]
    attest = next(s for s in steps if "attest-build-provenance" in str(s.get("uses", "")))
    subjects = {Path(p).name for p in attest["with"]["subject-path"].split()}
    for cited in re.findall(r"gh attestation verify (\S+)", SECURITY):
        assert cited in subjects, (
            f"SECURITY.md tells the reader to verify {cited!r}, which is not among "
            f"the attested subjects {sorted(subjects)}"
        )


def test_the_supported_version_line_matches_the_shipped_version():
    """It promised fixes for the 0.8.x line while main was 0.11."""
    import json

    version = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
    series = ".".join(version.split(".")[:2])
    assert f"`{series}.x`" in SECURITY, (
        f"package.json ships {version}; SECURITY.md's supported-version table "
        f"does not mention the {series}.x line"
    )
