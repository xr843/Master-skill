# Truthful Fidelity Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a green Fidelity check prove that at least one model response was graded, while preserving an explicit skip only for untrusted fork pull requests and eliminating duplicate same-repository PR runs.

**Architecture:** Extend `check-gate-liveness.py` with an optional fidelity-result input and route both paid workflow jobs through that check after the runner writes JSON. Restrict `push` validation to `main`; `pull_request` remains the feature-branch path. Missing credentials fail for trusted repository events and remain an explicit advisory skip for fork PRs, where GitHub intentionally withholds secrets.

**Tech Stack:** Python 3.9+, pytest, GitHub Actions YAML, Bash.

## Global Constraints

- Do not read, print, upload, or spend an API credential during this implementation.
- A dry run is not evidence that model grading happened.
- A graded suite must contain at least one `PASS` or `FAIL` verdict.
- Only a pull request whose head repository is a fork may skip for a missing `ANTHROPIC_API_KEY`.
- Same-repository pull requests, pushes to `main`, scheduled runs, and manual runs must fail when the required key is absent.
- Feature branches with pull requests run validation once through `pull_request`, not once through both `push` and `pull_request`.

---

### Task 1: Connect Fidelity Result Liveness To The CLI

**Files:**
- Modify: `scripts/check-gate-liveness.py`
- Modify: `scripts/tests/test_check_gate_liveness.py`

**Interfaces:**
- Produces: `load_fidelity_suites(path: Path) -> list[dict]`
- Produces: `run_all(root: Path, fidelity_suites: Optional[list[dict]] = None) -> list[str]`
- Produces: CLI option `--fidelity-results PATH`

- [x] **Step 1: Write failing CLI tests**

Add subprocess tests that write a result file containing no verdicts and assert exit 1 plus `graded suite produced 0 verdicts`; write a second file containing one `PASS` and assert exit 0.

- [x] **Step 2: Run the focused tests and verify RED**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest scripts/tests/test_check_gate_liveness.py -q`

Expected: FAIL because `--fidelity-results` is not accepted and the result is never loaded.

- [x] **Step 3: Implement result loading and CLI wiring**

Accept either the runner's top-level list or a committed report's `{ "suites": [...] }` wrapper. Reject every other shape with a clear `ValueError`. Pass loaded suites to `check_graded_suites_graded_something()` from `run_all()`.

- [x] **Step 4: Run the focused tests and verify GREEN**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest scripts/tests/test_check_gate_liveness.py -q`

Expected: all tests pass.

- [x] **Step 5: Commit**

```bash
git add scripts/check-gate-liveness.py scripts/tests/test_check_gate_liveness.py
git commit -m "fix(fidelity): connect result liveness to the gate"
```

### Task 2: Make Workflow Credential And Trigger Semantics Truthful

**Files:**
- Modify: `.github/workflows/validate-and-test.yml`
- Modify: `scripts/tests/test_validate_workflow.py`

**Interfaces:**
- Consumes: `python scripts/check-gate-liveness.py --fidelity-results PATH`
- Produces: `IS_FORK` environment flag derived from GitHub pull-request metadata

- [ ] **Step 1: Write failing workflow tests**

Assert `push.branches == ["main"]`; execute the no-key smoke branch with `IS_FORK=false` and require a non-zero exit; execute it with `IS_FORK=true` and require the existing explicit skip artifact; assert both keyed smoke/full scripts call `check-gate-liveness.py --fidelity-results`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest scripts/tests/test_validate_workflow.py -q`

Expected: FAIL because push targets every branch, missing keys always exit 0, and result liveness is not called.

- [ ] **Step 3: Implement the workflow policy**

Limit `push` to `main`. Export `IS_FORK` from `github.event.pull_request.head.repo.fork`. In the missing-key branch, write a skip artifact and exit 0 only when `IS_FORK=true`; otherwise write an error artifact, append a failure summary, and exit 1. Run the result-liveness CLI after both keyed smoke and full-suite executions.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run: `PATH="$PWD/.venv/bin:$PATH" python -m pytest scripts/tests/test_validate_workflow.py scripts/tests/test_check_gate_liveness.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/validate-and-test.yml scripts/tests/test_validate_workflow.py
git commit -m "fix(ci): stop passing an unrun fidelity gate"
```

### Task 3: Record The Correct Gate Contract

**Files:**
- Modify: `CONTRIBUTING.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: workflow behavior from Task 2
- Produces: contributor-facing secret/skip policy

- [ ] **Step 1: Update current documentation**

State that a missing key is advisory only for fork PRs and a hard failure for trusted repository events. Record both the previously dead liveness function and duplicate `push`/`pull_request` execution in `[Unreleased]`.

- [ ] **Step 2: Verify documentation consistency**

Run: `rg -n "advisory pass|main repo|主仓|fork" CONTRIBUTING.md .github/workflows/validate-and-test.yml CHANGELOG.md`

Expected: no claim says the main repository can pass a required smoke check without grading.

- [ ] **Step 3: Commit**

```bash
git add CONTRIBUTING.md CHANGELOG.md
git commit -m "docs: state the enforced fidelity gate policy"
```

### Task 4: Full Verification

**Files:**
- Verify only

**Interfaces:**
- Consumes: all preceding tasks
- Produces: release-quality verification evidence

- [ ] **Step 1: Run the full deterministic suite**

Run: `PATH="$PWD/.venv/bin:$PATH" npm test`

Expected: all structural validators, Node tests, and Python tests pass.

- [ ] **Step 2: Review the final diff**

Run: `git diff --check && git status --short && git diff HEAD~3..HEAD --stat`

Expected: no whitespace errors and only the planned files changed.
