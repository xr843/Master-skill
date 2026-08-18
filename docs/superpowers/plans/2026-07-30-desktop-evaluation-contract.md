# Desktop Evaluation Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans and superpowers:test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make fidelity output and desktop evaluation evidence explicit, typed, backward compatible, fail-closed, and truthful about dry-run versus graded coverage.

**Architecture:** The Python runner emits a versioned suite envelope while preserving its top-level JSON array and exit semantics. Rust dispatches versioned and legacy payloads into typed domain states, exposes current evidence errors instead of discarding them, and computes case detail, coverage, failures, trends, and release posture from deliberately selected latest runs. Catalog JSONL parsing returns diagnostics rather than inventing empty cases.

**Tech Stack:** Python 3.11+, pytest, Rust 2021, serde/serde_json, Cargo, egui.

## Global Constraints

- Keep the top-level `scripts/test-fidelity.py --json` shape as a JSON array.
- Do not make paid model calls.
- Keep legacy JSON arrays and legacy `Testing:` / `Result:` trace output readable.
- Treat ambiguity, malformed v1 fields, unsupported versions, and unknown statuses as invalid evidence.
- A later dry-run must not erase the newest graded evidence for behavioral analytics.
- The case-detail query must return one completed run only and never merge history.
- Invalid or unreadable fidelity JSONL contributes zero usable cases and cannot be `Ready`.
- `Ready` requires complete newest-graded coverage with no current error, failure, or regression.
- Keep the implementation in the existing Rust modules; module extraction belongs to a later refactor.
- Preserve unrelated worktree changes.

---

### Task 1: Emit the fidelity JSON v1 suite contract

**Files:**

- Modify: `tests/test_fidelity_exit.py`
- Modify: `scripts/test-fidelity.py`

**Interfaces:**

- Produces: `suite_error(master_name: str, dry_run: bool, message: str) -> dict`
- Produces: every new suite object with `schema_version`, `master`, `mode`, `outcome`, `total`, and `results`
- Preserves: `results_failed(results: list[dict], dry_run: bool) -> bool`

- [ ] **Step 1: Add a failing completed dry-run contract test**

Add a unit test that runs one real local case without a model call:

```python
def test_dry_run_emits_versioned_completed_suite(runner):
    suite = runner.run_tests(
        "master-huineng",
        dry_run=True,
        max_tests=1,
        quiet=True,
    )

    assert suite["schema_version"] == 1
    assert suite["master"] == "master-huineng"
    assert suite["mode"] == "dry_run"
    assert suite["outcome"] == "completed"
    assert suite["total"] == 1
    assert len(suite["results"]) == 1
    assert "passed" not in suite
    assert "failed" not in suite
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
/tmp/master-skill-pr1.nx5E4j/venv/bin/python -m pytest tests/test_fidelity_exit.py::test_dry_run_emits_versioned_completed_suite -q
```

Expected: FAIL because the current dry-run object has no version, mode, or outcome.

- [ ] **Step 3: Add the common v1 fields to completed suites**

Define:

```python
SCHEMA_VERSION = 1


def suite_common(master_name: str, dry_run: bool, outcome: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "master": master_name,
        "mode": "dry_run" if dry_run else "graded",
        "outcome": outcome,
    }
```

Build the dry-run return from `suite_common(..., "completed")` and add
`total` plus `results`. Build the graded completed return the same way while
retaining `model`, `passed`, `failed`, `pass_rate`, and `results`.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the command from Step 2.

Expected: PASS.

- [ ] **Step 5: Add failing error-suite contract tests**

Test `run_tests("master-does-not-exist", dry_run=False)` and the existing
subprocess result. Assert the error suite equals:

```python
{
    "schema_version": 1,
    "master": "master-does-not-exist",
    "mode": "graded",
    "outcome": "error",
    "total": 0,
    "results": [],
    "error": "Master 'master-does-not-exist' not found",
}
```

Also extend the subprocess assertion to require all seven contract fields.

- [ ] **Step 6: Run the error tests and verify RED**

Run:

```bash
/tmp/master-skill-pr1.nx5E4j/venv/bin/python -m pytest \
  tests/test_fidelity_exit.py::test_missing_master_emits_versioned_error_suite \
  tests/test_fidelity_exit.py::test_missing_master_exits_nonzero_with_clean_json_stdout \
  -q
```

Expected: FAIL because precondition errors currently contain only `error`.

- [ ] **Step 7: Centralize precondition errors**

Implement:

```python
def suite_error(master_name: str, dry_run: bool, message: str) -> dict:
    return {
        **suite_common(master_name, dry_run, "error"),
        "total": 0,
        "results": [],
        "error": message,
    }
```

Use it for missing master, missing fidelity data, missing `anthropic`, and
missing `ANTHROPIC_API_KEY`.

- [ ] **Step 8: Verify the Python contract and exit behavior**

Run:

```bash
/tmp/master-skill-pr1.nx5E4j/venv/bin/python -m pytest tests/test_fidelity_exit.py -q
/tmp/master-skill-pr1.nx5E4j/venv/bin/python scripts/test-fidelity.py \
  --master master-huineng --dry-run --json > /tmp/master-skill-pr1-fidelity.json
/tmp/master-skill-pr1.nx5E4j/venv/bin/python -m json.tool \
  /tmp/master-skill-pr1-fidelity.json >/dev/null
```

Expected: all tests pass and both commands exit 0.

- [ ] **Step 9: Commit Task 1**

```bash
git add scripts/test-fidelity.py tests/test_fidelity_exit.py
git commit -m "feat(fidelity): emit versioned evaluation suites"
```

---

### Task 2: Parse evaluation suites into typed Rust evidence

**Files:**

- Modify: `desktop/src/trace.rs`

**Interfaces:**

- Produces:

```rust
pub enum EvaluationMode {
    DryRun,
    Graded,
}

pub enum EvaluationCaseStatus {
    Pass,
    Fail,
    DryRun,
    ApiError,
    Unknown(String),
}

pub enum EvaluationEvidenceErrorKind {
    Execution,
    MalformedPayload,
    UnsupportedVersion,
}

pub struct EvaluationEvidenceError {
    pub trace_id: u64,
    pub slug: Option<String>,
    pub kind: EvaluationEvidenceErrorKind,
    pub message: String,
}
```

- Changes `EvaluationRunResult` and `EvaluationRunHistoryItem` from
  `dry_run: bool` to `mode: EvaluationMode`
- Changes `EvaluationCaseResult.status` from `String` to
  `EvaluationCaseStatus`
- Produces `TraceRecord::evaluation_errors()`

- [ ] **Step 1: Add failing v1 parsing tests**

Add one test with a completed v1 dry-run suite and one with a completed v1
graded suite. Assert explicit `EvaluationMode`, typed case statuses, counts,
and slug normalization.

Use this dry-run fixture:

```json
[{
  "schema_version": 1,
  "master": "master-huineng",
  "mode": "dry_run",
  "outcome": "completed",
  "total": 1,
  "results": [{"index": 0, "question": "Q", "status": "dry_run"}]
}]
```

Use a graded fixture with `passed: 1`, `failed: 1`, one `PASS`, and one
`FAIL`.

- [ ] **Step 2: Run the v1 tests and verify RED**

Run:

```bash
cargo test --locked --manifest-path desktop/Cargo.toml \
  parses_v1_evaluation -- --nocapture
```

Expected: compilation/test failure because the typed domain API does not exist.

- [ ] **Step 3: Introduce typed domain enums and wire structs**

Derive `Clone`, `Debug`, `PartialEq`, and `Eq` for the domain enums. Add
`EvaluationMode::is_dry_run()` and a case-status parser that recognizes
case-insensitive `PASS`, `FAIL`, `dry_run`, and `api_error`, retaining any
other text in `Unknown`.

Deserialize versioned suites through required wire fields:

```rust
#[derive(Deserialize)]
struct EvaluationSuiteV1 {
    schema_version: u64,
    master: String,
    mode: EvaluationModeWire,
    outcome: EvaluationOutcomeWire,
    total: usize,
    results: Vec<EvaluationCaseWire>,
    passed: Option<usize>,
    failed: Option<usize>,
    error: Option<String>,
}
```

Use a small `schema_version` probe only to dispatch each JSON object. Do not
default missing required v1 fields.

- [ ] **Step 4: Convert valid v1 suites and verify GREEN**

For `outcome = completed`, require:

- dry-run cases to contain only `DryRun`, with no graded counts required;
- graded suites to contain integer `passed` and `failed`;
- no `Unknown` status.

Convert each valid suite into run and case domain values, then run the tests
from Step 2.

Expected: PASS.

- [ ] **Step 5: Add failing legacy compatibility tests**

Retain or extend tests for:

- old JSON with all `dry_run` statuses => `EvaluationMode::DryRun`;
- old JSON with `passed` => `EvaluationMode::Graded`;
- legacy plain-text `Testing:` / `Result:` output => graded result;
- ambiguous legacy JSON without `passed` and without all-dry-run cases =>
  malformed evidence.

- [ ] **Step 6: Run legacy tests and verify RED where behavior changes**

Run:

```bash
cargo test --locked --manifest-path desktop/Cargo.toml legacy_evaluation -- --nocapture
```

Expected: the new ambiguity test fails until legacy conversion is explicit.

- [ ] **Step 7: Implement legacy conversion without field-absence mode inference**

Deserialize legacy suites into a separate wire struct. Infer dry-run only when
the suite has at least one case and every status is `DryRun`. Infer graded only
when `passed` is present. Reject every other legacy JSON suite. Keep the
existing plain-text parser as a graded fallback only when the detail is not a
JSON document.

- [ ] **Step 8: Add failing evidence-error tests**

Test:

- v1 `outcome = error` creates `Execution`;
- malformed JSON creates `MalformedPayload`;
- `schema_version = 2` creates `UnsupportedVersion`;
- an unknown case status creates `MalformedPayload` and produces no completed
  run;
- a failed fidelity `TraceRecord` creates `Execution`.

- [ ] **Step 9: Run evidence-error tests and verify RED**

Run:

```bash
cargo test --locked --manifest-path desktop/Cargo.toml evaluation_evidence_error -- --nocapture
```

Expected: FAIL because errors are currently dropped.

- [ ] **Step 10: Return one parsed evaluation payload per trace**

Add a private container:

```rust
#[derive(Default)]
struct ParsedEvaluationEvidence {
    runs: Vec<EvaluationRunResult>,
    cases: Vec<EvaluationCaseResult>,
    errors: Vec<EvaluationEvidenceError>,
}
```

Make `TraceRecord::evaluation_results()`,
`TraceRecord::evaluation_case_results()`, and
`TraceRecord::evaluation_errors()` delegate to the same conversion rules.
For a failed fidelity trace, preserve its scope and detail in an execution
error. For JSON that begins as JSON but cannot satisfy a supported contract,
return a parse/version error instead of falling through to the text parser.

- [ ] **Step 11: Update enum call sites and verify the trace module**

Replace string status comparisons with enum matches and replace direct
`dry_run` field access with `mode`/`is_dry_run()`. Then run:

```bash
cargo fmt --manifest-path desktop/Cargo.toml
cargo test --locked --manifest-path desktop/Cargo.toml trace::tests -- --nocapture
```

Expected: all trace tests pass.

- [ ] **Step 12: Commit Task 2**

```bash
git add desktop/src/trace.rs
git commit -m "refactor(desktop): type evaluation evidence"
```

---

### Task 3: Enforce latest-run semantics for cases and graded analytics

**Files:**

- Modify: `desktop/src/trace.rs`
- Modify: `desktop/src/app.rs`
- Modify: `desktop/tests/baseline_cli.rs`

**Interfaces:**

- `latest_evaluation_case_results_for(slug)` returns cases from one newest
  completed run
- Structural coverage uses newest completed run of either mode
- Graded coverage/failures/trends use newest graded run per skill
- Current evidence errors remain until a successful attempt for the same scope

- [ ] **Step 1: Add a failing no-history-merge regression test**

Create an older graded trace with case index `0 = FAIL` and a newer graded
trace with case index `0 = PASS`. Assert:

```rust
let cases = store.latest_evaluation_case_results_for("huineng");
assert_eq!(cases.len(), 1);
assert_eq!(cases[0].status, EvaluationCaseStatus::Pass);
assert_eq!(cases[0].trace_id, newer_trace_id);
```

- [ ] **Step 2: Run the case test and verify RED**

Run:

```bash
cargo test --locked --manifest-path desktop/Cargo.toml \
  latest_case_results_do_not_merge_history -- --nocapture
```

Expected: FAIL because the current method returns both records.

- [ ] **Step 3: Stop after the newest completed record for a skill**

Walk trace records newest-first. At the first completed record containing the
normalized slug, return only that record's cases for the slug. Remove the UI's
dependence on insertion order; collecting those cases by index is then safe.

- [ ] **Step 4: Verify the latest-case test GREEN**

Run the command from Step 2.

Expected: PASS.

- [ ] **Step 5: Add failing graded-evidence retention tests**

Create an older graded PASS followed by a newer dry-run for the same skill.
Assert:

- structural latest mode is dry-run;
- newest graded result is still the older graded PASS;
- failure insights use newest graded cases;
- dry-run history is not compared as a graded regression.

- [ ] **Step 6: Run the graded-retention tests and verify RED**

Run:

```bash
cargo test --locked --manifest-path desktop/Cargo.toml \
  later_dry_run_preserves_graded_evidence -- --nocapture
```

Expected: FAIL because current analytics use the latest result of any mode.

- [ ] **Step 7: Add newest-graded queries and graded trend comparison**

Implement newest-first queries that filter `EvaluationMode::Graded` before
deduplicating by slug. Use them for graded coverage, case-failure insights,
failure queue, and regression comparison. Keep the case-detail and structural
queries mode-agnostic. Give dry-run history entries `New` rather than comparing
them against graded scores.

- [ ] **Step 8: Add failing current-error replacement tests**

Test:

- newest failed/malformed attempt for a skill is returned;
- an older error is suppressed by a later successful completed attempt for the
  same skill;
- errors for other skills remain visible;
- an all-scope error is current until a later successful all-scope run.

- [ ] **Step 9: Implement current evidence error selection**

Walk records newest-first and track handled scopes. A successful suite handles
its skill scope; an error handles its explicit skill scope; an all-scope action
uses a distinct all-scope key. Return only the first outcome observed per
scope.

- [ ] **Step 10: Verify trace, app, and integration tests**

Run:

```bash
cargo fmt --manifest-path desktop/Cargo.toml
cargo test --locked --manifest-path desktop/Cargo.toml
```

Expected: all Rust tests pass.

- [ ] **Step 11: Commit Task 3**

```bash
git add desktop/src/trace.rs desktop/src/app.rs desktop/tests/baseline_cli.rs
git commit -m "fix(desktop): select current evaluation evidence"
```

---

### Task 4: Fail closed on invalid fidelity JSONL

**Files:**

- Modify: `desktop/src/catalog.rs`
- Modify: `desktop/src/app.rs`

**Interfaces:**

- Changes `parse_fidelity_cases(content)` to
  `Result<Vec<FidelityCase>, String>`
- Adds `fidelity_error: Option<String>` to `SkillDiagnostics` and `SkillRow`
- Makes diagnostic gaps own strings so the line-numbered parse detail can be
  surfaced

- [ ] **Step 1: Add a failing invalid-line catalog test**

Write a temporary `tests/fidelity.jsonl` with one valid case and a malformed
second line. Assert:

```rust
assert_eq!(diagnostics.fidelity_case_count, 0);
assert!(diagnostics.fidelity_cases.is_empty());
assert!(diagnostics
    .fidelity_error
    .as_deref()
    .is_some_and(|error| error.contains("line 2")));
```

Apply the diagnostics to a row and assert it is not `QualityLevel::Ready` and
its summary contains `invalid fidelity suite`.

- [ ] **Step 2: Run the catalog test and verify RED**

Run:

```bash
cargo test --locked --manifest-path desktop/Cargo.toml \
  invalid_fidelity_jsonl_fails_closed -- --nocapture
```

Expected: FAIL because the current parser turns invalid lines into default
values and still counts them.

- [ ] **Step 3: Parse every nonblank line transactionally**

For each nonblank line, deserialize `serde_json::Value`, require a non-empty
string `q`, and convert it to `FidelityCase`. On the first error return:

```rust
Err(format!("line {}: {error}", line_index + 1))
```

Do not return partial cases. Distinguish missing file (`None`), unreadable file
(`Some(read error)`), valid file, and invalid file.

- [ ] **Step 4: Propagate the diagnostic through rows and quality**

Copy `fidelity_error` in `apply_diagnostics`. Require
`fidelity_error.is_none()` for `Ready`. Emit either:

- `missing fidelity suite`, or
- `invalid fidelity suite: {line-numbered detail}`

but never both.

- [ ] **Step 5: Update row fixtures and verify GREEN**

Set `fidelity_error: None` in test helpers and app fixtures. Run:

```bash
cargo fmt --manifest-path desktop/Cargo.toml
cargo test --locked --manifest-path desktop/Cargo.toml catalog::tests -- --nocapture
```

Expected: all catalog tests pass.

- [ ] **Step 6: Commit Task 4**

```bash
git add desktop/src/catalog.rs desktop/src/app.rs
git commit -m "fix(desktop): reject invalid fidelity suites"
```

---

### Task 5: Make evaluation coverage and release posture truthful

**Files:**

- Modify: `desktop/src/trace.rs`
- Modify: `desktop/src/app.rs`
- Modify: `desktop/tests/baseline_cli.rs`

**Interfaces:**

- Expands `EvaluationRunCoverage` with structural, graded, dry-run, and current
  error counts
- Adds `is_structurally_complete()` and `is_graded_complete()`
- Enforces decision precedence:
  regression, error, graded failure, structural gap, graded gap, ready

- [ ] **Step 1: Add a failing dry-run-only gate test**

Build rows for every expected skill and add completed v1 dry-run traces for
every skill. Assert:

```rust
assert!(snapshot.run_coverage.is_structurally_complete());
assert!(!snapshot.run_coverage.is_graded_complete());
assert_eq!(snapshot.decision.posture, EvaluationDecisionPosture::Unproven);
assert_eq!(snapshot.decision.headline, "Graded evidence incomplete");
```

- [ ] **Step 2: Run the dry-run gate test and verify RED**

Run:

```bash
cargo test --locked --manifest-path desktop/Cargo.toml \
  complete_dry_run_coverage_is_unproven -- --nocapture
```

Expected: FAIL because complete dry-run coverage currently becomes `Ready`.

- [ ] **Step 3: Separate structural and graded coverage**

Populate:

```rust
pub struct EvaluationRunCoverage {
    pub total_skill_count: usize,
    pub structural_run_skill_count: usize,
    pub graded_run_skill_count: usize,
    pub dry_run_skill_count: usize,
    pub current_error_count: usize,
}
```

Structural counts come from newest completed any-mode results. Graded counts
come from newest graded results independently. Clamp counts to the discovered
skill total only for presentation percentages, not for evidence selection.

- [ ] **Step 4: Implement decision precedence through focused tests**

Add one focused test for each state:

1. graded regression => `Blocked`;
2. current evidence error => `Blocked`;
3. current graded case failure => existing failure-review posture;
4. incomplete structural coverage => `Unproven`;
5. complete structural but incomplete graded => `Unproven` with
   `Graded evidence incomplete`;
6. complete graded passing coverage => `Ready`.

Run each new test immediately before implementing its branch, verify RED,
implement the smallest branch, then verify GREEN.

- [ ] **Step 5: Update UI labels and baseline assertions**

Show structural and graded counts separately. Ensure dry-run copy says it
establishes structure only. Update the baseline integration test to require
structural completeness while explicitly expecting dry-run-only evidence not
to be release-ready.

- [ ] **Step 6: Verify the complete Rust suite**

Run:

```bash
cargo fmt --manifest-path desktop/Cargo.toml
cargo clippy --locked --manifest-path desktop/Cargo.toml --all-targets -- -D warnings
cargo test --locked --manifest-path desktop/Cargo.toml
```

Expected: all commands exit 0.

- [ ] **Step 7: Commit Task 5**

```bash
git add desktop/src/trace.rs desktop/src/app.rs desktop/tests/baseline_cli.rs
git commit -m "fix(desktop): require graded release evidence"
```

---

### Task 6: Review, document, and verify PR 1

**Files:**

- Modify only if evidence requires it: `README.md`, `desktop/README.md`
- Review: every file changed since `origin/main`

- [ ] **Step 1: Inspect the complete diff**

Run:

```bash
git diff --check
git diff --stat origin/main...HEAD
git diff origin/main...HEAD
```

Check for:

- accidental schema breakage;
- a path that still infers dry-run from missing `passed`;
- stringly typed case status comparisons;
- latest-any evidence feeding graded analytics;
- malformed/error suites disappearing;
- dry-run-only copy implying release readiness;
- unrelated changes.

- [ ] **Step 2: Run focused contract tests**

Run:

```bash
/tmp/master-skill-pr1.nx5E4j/venv/bin/python -m pytest tests/test_fidelity_exit.py -q
cargo test --locked --manifest-path desktop/Cargo.toml
```

Expected: all pass.

- [ ] **Step 3: Run repository-wide verification**

Run:

```bash
npm test
/tmp/master-skill-pr1.nx5E4j/venv/bin/python -m pytest tests/ scripts/tests/ -q
cargo fmt --manifest-path desktop/Cargo.toml -- --check
cargo clippy --locked --manifest-path desktop/Cargo.toml --all-targets -- -D warnings
cargo test --locked --manifest-path desktop/Cargo.toml
cargo build --locked --manifest-path desktop/Cargo.toml
```

Expected: all commands exit 0, with no paid evaluation.

- [ ] **Step 4: Perform final self-review**

Re-read both design and implementation plan documents against the diff. Fix
every correctness, compatibility, or clarity issue found through a new
red-green cycle where behavior changes.

- [ ] **Step 5: Commit documentation-only corrections if needed**

```bash
git add docs README.md desktop/README.md
git commit -m "docs(desktop): explain evaluation evidence modes"
```

Skip this commit when no documentation correction is needed.

- [ ] **Step 6: Prepare the PR handoff**

Record:

- commit list;
- diff summary;
- exact verification commands and outcomes;
- backward-compatibility behavior;
- intentionally deferred PR 2 runtime work.
