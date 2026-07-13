# Truthful Quality Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CI fail on real graded regressions, exercise all local tests, dynamically cover all 15 personas, and enforce clean Rust quality checks.

**Architecture:** Fidelity exit status is computed from result data, not workflow-side assumptions. Python regression tests cover CLI exit semantics and static workflow invariants. Voice tests follow the current `references/voice.md` layout and explicitly fail on empty discovery.

**Tech Stack:** Python 3.11+, pytest, GitHub Actions YAML, Rust/Cargo.

## Global Constraints

- Successful dry-runs exit 0; graded failures, API errors, and top-level errors exit non-zero.
- JSON mode writes only JSON to stdout.
- Missing `ANTHROPIC_API_KEY` remains an explicit advisory skip with a GitHub step summary.
- Smoke selection discovers all 15 personas dynamically and excludes meta-skills.
- CI runs `tests/` and `scripts/tests/`, strict lore validation, Rust fmt, clippy, and tests.
- Do not edit npm/CLI/package files, citation instructions, persona metadata, or distribution READMEs.

---

### Task 1: Correct fidelity runner exit semantics

**Files:**
- Create: `tests/test_fidelity_exit.py`
- Modify: `scripts/test-fidelity.py`

**Interfaces:**
- Produces: `results_failed(results: list[dict], dry_run: bool) -> bool`; `main()` exits 1 when it returns true.

- [ ] **Step 1: Write failing unit and subprocess tests**

Import the hyphenated runner with `importlib.util`. Test:

```python
def test_dry_run_results_do_not_fail(runner):
    assert runner.results_failed([{"master": "m", "total": 1, "results": [{"status": "dry_run"}]}], True) is False

def test_failed_count_fails(runner):
    assert runner.results_failed([{"master": "m", "failed": 1, "results": []}], False) is True

def test_api_error_case_fails(runner):
    data = [{"master": "m", "failed": 0, "results": [{"status": "api_error"}]}]
    assert runner.results_failed(data, False) is True

def test_top_level_error_fails(runner):
    assert runner.results_failed([{"error": "missing key"}], False) is True
```

Add a subprocess test that invokes the script with `--master master-does-not-exist --json` and asserts exit 1 with parseable JSON stdout containing one top-level error object.

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_fidelity_exit.py -v`  
Expected: FAIL because `results_failed` does not exist and current errors exit 0.

- [ ] **Step 3: Implement exit evaluation**

Implement:

```python
def results_failed(results: list[dict], dry_run: bool) -> bool:
    if dry_run:
        return any("error" in suite for suite in results)
    return any(
        "error" in suite
        or suite.get("failed", 0) > 0
        or any(case.get("status") in {"FAIL", "api_error"} for case in suite.get("results", []))
        for suite in results
    )
```

After printing JSON or human summaries, set the process result with `return 1 if results_failed(all_results, args.dry_run) else 0` and call `raise SystemExit(main())`. Keep stdout clean in JSON mode.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
python -m pytest tests/test_fidelity_exit.py -v
python scripts/test-fidelity.py --all --dry-run --json >/tmp/fidelity.json
python -m json.tool /tmp/fidelity.json >/dev/null
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```bash
git add scripts/test-fidelity.py tests/test_fidelity_exit.py
git commit -m "fix(fidelity): return failure status for graded regressions"
```

### Task 2: Repair voice-test discovery and progressive-disclosure assertions

**Files:**
- Modify: `tests/test_voice_rules.py`

**Interfaces:**
- Produces: test parameters for all 15 persona `references/voice.md` files.

- [ ] **Step 1: Add an explicit discovery assertion and verify RED**

First run `python -m pytest tests/test_voice_rules.py -q -rs` and record the six empty-parameter skips. Without changing the current discovery expression, add:

```python
def test_voice_persona_discovery_is_complete():
    assert len(MASTER_SLUGS) == 15, MASTER_SLUGS
```

- [ ] **Step 2: Update discovery, fixture paths, and architecture assertion**

Change discovery to inspect `d / "references" / "voice.md"` and read voice content from that path. Replace the obsolete full-body inclusion test with:

```python
def test_skill_md_routes_to_voice_reference(slug, skill_content):
    assert "references/voice.md" in skill_content
    assert "首轮身份中立" in skill_content
```

Keep the Layer 0, opening, address, and forbidden-term assertions unchanged unless a failing persona demonstrates a current heading variant; in that case normalize extraction without weakening the forbidden-term rule.

- [ ] **Step 3: Run voice tests and verify GREEN**

Run: `python -m pytest tests/test_voice_rules.py -v -rs`  
Expected: 91 passing cases and no skips (1 discovery test plus 6 parameterized tests × 15 personas).

- [ ] **Step 4: Commit**

```bash
git add tests/test_voice_rules.py
git commit -m "fix(tests): restore voice rule coverage"
```

### Task 3: Make workflow invariants testable and truthful

**Files:**
- Create: `scripts/tests/test_validate_workflow.py`
- Modify: `.github/workflows/validate-and-test.yml`

**Interfaces:**
- Produces: static regression checks for workflow commands and dynamic persona discovery.

- [ ] **Step 1: Write failing workflow assertions**

Read the workflow as text and assert:

```python
assert "python -m pytest tests/ scripts/tests/ -v" in workflow
assert "continue-on-error: true" not in workflow
assert "python scripts/validate-lore-triggers-content.py --strict" in workflow
assert "cargo fmt --manifest-path desktop/Cargo.toml -- --check" in workflow
assert "cargo clippy --locked --manifest-path desktop/Cargo.toml --all-targets -- -D warnings" in workflow
assert "master-nagarjuna master-xuanzang" not in workflow
assert "sources" in workflow and "meta.json" in workflow
assert 'echo "### Fidelity grading skipped' in workflow
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest scripts/tests/test_validate_workflow.py -v`  
Expected: FAIL on the current split pytest command, advisory lore step, missing Rust lint, fixed roster, and absent step summary.

- [ ] **Step 3: Update the validate and Rust jobs**

Run both Python suites with `python -m pytest tests/ scripts/tests/ -v`. Run lore validation with `--strict` and no `continue-on-error`. Add Rust fmt and clippy commands before `cargo test --locked --manifest-path desktop/Cargo.toml`; keep the build step locked.

- [ ] **Step 4: Replace the fixed smoke roster**

Use a Python heredoc to read `prebuilt/master-*/meta.json` and print only directories whose `sources` value is a non-empty list. Store the sorted output in a Bash array with `mapfile -t MASTERS`. Reject an empty array. If a changed directory is not in the discovered array, ignore it and rotate over all 15 personas.

- [ ] **Step 5: Add explicit advisory summaries**

In both no-key branches append Markdown to `$GITHUB_STEP_SUMMARY`. The full run uses:

```bash
{
  echo "### Fidelity grading skipped"
  echo
  echo "ANTHROPIC_API_KEY is not configured; deterministic validation ran, but model grading did not run."
} >> "$GITHUB_STEP_SUMMARY"
```

The keyed full run relies on the corrected fidelity runner exit status and needs no extra JSON parser.

- [ ] **Step 6: Run workflow tests and verify GREEN**

Run: `python -m pytest scripts/tests/test_validate_workflow.py -v`  
Expected: all assertions pass.

- [ ] **Step 7: Commit**

```bash
git add .github/workflows/validate-and-test.yml scripts/tests/test_validate_workflow.py
git commit -m "fix(ci): enforce truthful complete quality gates"
```

### Task 4: Make the new Rust lint gate clean

**Files:**
- Modify: `desktop/src/app.rs`

**Interfaces:**
- Produces: warning-free Rust targets under the configured clippy command.

- [ ] **Step 1: Reproduce the lint failure**

Run: `cargo clippy --locked --manifest-path desktop/Cargo.toml --all-targets -- -D warnings`  
Expected: FAIL at the `top_failure_skill_slug.as_ref().map(|slug| slug.as_str())` expression with `option_as_ref_deref`.

- [ ] **Step 2: Apply the minimal lint fix**

Replace that expression with `top_failure_skill_slug.as_deref()` and make no surrounding refactor.

- [ ] **Step 3: Run Rust quality gates**

Run:

```bash
cargo fmt --manifest-path desktop/Cargo.toml -- --check
cargo clippy --locked --manifest-path desktop/Cargo.toml --all-targets -- -D warnings
cargo test --locked --manifest-path desktop/Cargo.toml
```

Expected: all commands exit 0.

- [ ] **Step 4: Commit**

```bash
git add desktop/src/app.rs
git commit -m "fix(desktop): satisfy strict clippy gate"
```
