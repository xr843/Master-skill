# Desktop Release Archives And Checksums Plan

**Goal:** Publish executable-bit-preserving Unix archives and one verified checksum manifest without breaking existing raw desktop-binary download links.

**Architecture:** Each platform build stages its existing raw binary; Linux and macOS additionally create a `.tar.gz`. Matrix legs upload intermediate workflow artifacts only. A dependent Ubuntu job downloads all legs, generates and verifies a deterministic `SHA256SUMS`, then either uploads the complete set to the GitHub release or exposes one combined dry-run artifact.

**Tech Stack:** GitHub Actions YAML, Bash, tar, sha256sum, pytest/actionlint.

## Constraints

- Keep the three existing raw asset names for compatibility.
- Add `.tar.gz` only for Linux and macOS; the Windows `.exe` remains directly downloadable.
- Generate checksums only after every matrix build succeeds.
- Pin every GitHub Action to a full commit SHA.
- A manual dispatch must exercise assembly and checksum generation without mutating a release.
- Do not create or modify an actual GitHub release while implementing this workflow.

### Task 1: Specify The Release Asset Contract

**Files:**
- Create: `scripts/tests/test_release_desktop_workflow.py`

- [x] Add failing tests for Unix archives, build-artifact handoff, the dependent assembly job, pinned download-artifact, checksum verification, release upload, and manual combined artifact.
- [x] Run the focused test and confirm RED against the current direct-upload workflow.

### Task 2: Implement Matrix Packaging And Assembly

**Files:**
- Modify: `.github/workflows/release-desktop.yml`

- [x] Package Linux/macOS binaries with `tar -czf` after applying executable mode.
- [x] Upload every matrix leg as an intermediate artifact on both trigger types.
- [x] Add an assembly job that downloads all legs, emits sorted `SHA256SUMS`, verifies it, and publishes the complete asset set to the appropriate destination.
- [x] Run focused tests and actionlint with ShellCheck; confirm GREEN.

### Task 3: Document The Download Contract

**Files:**
- Modify: `README.md`
- Modify: `README_EN.md`
- Modify: `CHANGELOG.md`

- [x] Recommend `.tar.gz` for Unix while documenting raw-name compatibility and the checksum manifest.
- [x] Record the release workflow change under `[Unreleased]`.

### Task 4: Full Verification And Delivery

- [x] Run `npm test` and actionlint with ShellCheck.
- [x] Review `git diff --check` and the complete branch diff.

Delivery status is recorded by the pull request and the post-merge manual workflow run.
