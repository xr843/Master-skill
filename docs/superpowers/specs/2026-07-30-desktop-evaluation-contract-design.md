# Desktop Evaluation Contract Design

**Date:** 2026-07-30

**Target branch:** `fix/desktop-evaluation-contract`

**Goal:** Make desktop fidelity evidence deterministic, typed, backward
compatible, and truthful about the difference between structural dry-runs and
graded behavioral evidence.

## Scope and selected approach

This PR fixes the evaluation-specific findings from the desktop review:

- historical case results can overwrite the newest result;
- dry-run mode is inferred from a missing JSON field;
- malformed and error suites disappear;
- invalid JSONL can count as a fidelity case;
- complete dry-run coverage is presented as release-ready.

Three approaches were considered:

1. **Patch the UI map and relabel the gate.** This is small, but the store API
   would still return the wrong data and malformed/error evidence would remain
   invisible.
2. **Add a backward-compatible fidelity v1 contract and typed Rust domain
   states.** This is the selected approach because it fixes the boundary that
   creates all five symptoms while retaining old traces and external JSON
   consumers.
3. **Replace the fidelity runner and trace analytics together.** This would
   permit a cleaner new API but would unnecessarily break the existing Python
   runner, CI automation, and persisted history.

The PR keeps evaluation code in the existing Rust files. Extracting
`evaluation.rs` and a bulk desktop API remains later architecture work.

## Root-cause evidence

### Historical case results overwrite current results

`TraceStore::latest_evaluation_case_results_for` walks every record
newest-first and returns every matching historical case. The UI collects that
sequence into a `BTreeMap<case_index, result>`. Older values are inserted after
newer values, so an old result for the same case index replaces the current
result.

The store API promises "latest" while returning history. The fix belongs in the
store query rather than changing UI insertion order.

### Evaluation mode and errors are implicit

The Python JSON output omits `passed` for a dry-run. Rust interprets that
absence as `dry_run = true`, skips suites with missing fields, and drops
`{"error": ...}` suites. The catalog parser separately converts an invalid
JSONL line into an empty JSON value and still counts it as a case.

The root cause is using field absence and `serde_json::Value` defaults as domain
state.

### Dry-run coverage is presented as release evidence

The gate returns `Ready` whenever every skill has any latest run and there are
no parsed failures or regressions. A complete dry-run therefore produces
`Ready` even though it makes no model calls and cannot pass or fail behavioral
assertions.

One coverage count currently represents two claims: structural discoverability
and graded behavioral evidence.

## Backward-compatible fidelity JSON v1

`scripts/test-fidelity.py --json` continues to emit a top-level JSON array so
existing automation that iterates suites remains compatible. Every suite in new
output uses this v1 contract:

```json
{
  "schema_version": 1,
  "master": "master-huineng",
  "mode": "dry_run",
  "outcome": "completed",
  "total": 2,
  "results": [
    {
      "index": 0,
      "question": "什么是见性成佛？",
      "difficulty": "basic",
      "status": "dry_run"
    }
  ]
}
```

Exact field rules:

- `schema_version` is the integer `1`.
- `master` is always present, including error suites.
- `mode` is exactly `dry_run` or `graded`.
- `outcome` is exactly `completed` or `error`.
- `total` and `results` are present for every outcome; precondition errors use
  `0` and `[]`.
- A completed graded suite also has integer `passed` and `failed`.
- An error suite has a non-empty string `error`.
- A completed dry-run preserves the existing omission of `passed` and `failed`
  for consumers that still use the legacy convention.

The runner's existing exit contract remains unchanged: successful dry-runs exit
zero; top-level errors, API errors, and graded failures exit non-zero.

## Rust wire and domain types

Rust parses v1 suites into required wire fields and converts them to domain
types:

```text
EvaluationMode = DryRun | Graded
EvaluationCaseStatus = Pass | Fail | DryRun | ApiError | Unknown(String)
EvaluationSuiteOutcome = Completed | Error(String)
EvaluationEvidenceError = Execution | MalformedPayload | UnsupportedVersion
```

`Unknown(String)` is retained for diagnostics and makes the suite invalid
evidence; it is never treated as a pass or an ordinary graded failure.
Malformed v1 fields produce an explicit evaluation evidence error.

Legacy trace history remains readable:

- the old JSON array is accepted;
- legacy mode is inferred as dry-run only when every case status is `dry_run`;
- a suite with `passed` is graded;
- the old plain-text `Testing:` / `Result:` format remains readable;
- ambiguous legacy JSON becomes invalid evidence instead of a dry-run.

Raw command output remains stored for audit and migration diagnostics.

## Latest-result and analytics semantics

For the case-detail panel, a skill query returns results from the newest
completed trace record that contains that skill and stops. It never combines
case indexes from different runs.

Behavioral analytics do not let a later dry-run erase valid graded evidence:

- the case-detail panel uses the latest completed run of either mode;
- structural coverage uses the latest completed run of either mode;
- graded coverage, failure insights, and regression comparisons use the newest
  graded run per skill;
- the newest failed or malformed attempt remains visible as an evidence error
  until a later successful attempt for the same scope replaces it.

A regression test records an older FAIL and a newer PASS for the same skill and
case index, then asserts that only the newer PASS is returned.

Trace records do not contain repository revision hashes, so this PR does not
claim that historical graded evidence is newer than the skill content. Adding
content/revision fingerprints is a separate design.

## Fail-closed local fidelity diagnostics

Fidelity JSONL parsing returns a line-numbered error instead of a default case.
The desktop distinguishes:

- missing fidelity suite;
- valid, non-empty fidelity suite;
- invalid or unreadable fidelity suite.

Invalid or unreadable suites have zero usable cases, cannot produce
`QualityLevel::Ready`, and display an `invalid fidelity suite` diagnostic.
Existing repository validators remain the authoritative CI gate; this desktop
behavior protects locally modified or partially corrupted clones.

## Truthful gate semantics

Coverage tracks structural runs, newest graded runs, and current evaluation
errors separately.

Decision precedence is:

1. a current graded regression is `Blocked`;
2. a current evaluation execution or parse error is `Blocked`;
3. a current graded case failure requires review under the existing failure
   posture;
4. incomplete structural coverage is `Unproven`;
5. complete structural coverage without complete graded coverage is
   `Unproven`, with the headline `Graded evidence incomplete`;
6. `Ready` requires complete newest-graded coverage with no current errors,
   failures, or regressions.

The dry-run-only state explicitly says that structural baseline coverage is
complete while graded evidence remains absent. It must not recommend proceeding
with release approval.

This PR does not add a paid local grading button or change the repository policy
that paid grading may be advisory when credentials are absent.

## Tests and acceptance

Tests cover:

- older case results cannot overwrite the newest run;
- v1 dry-run and graded suites parse with explicit modes;
- legacy JSON and legacy text traces remain readable;
- error suites and malformed v1 payloads become visible evidence errors;
- unknown case statuses are not counted as passes;
- invalid JSONL is not counted as a fidelity case;
- complete dry-run coverage remains `Unproven`;
- complete passing graded coverage can become `Ready`;
- the Python runner emits v1 fields for completed and error suites;
- JSON stdout remains parseable and existing exit semantics remain intact.

The PR must pass Rust formatting, strict Clippy, all Rust tests, `npm test`, and
the complete Python test suite. No paid model evaluation is run.

## Non-goals

- No trace persistence or worker lifecycle changes; those are PR 2.
- No new paid-evaluation workflow or credential handling.
- No content/repository fingerprinting for evidence freshness.
- No broad module split, SQLite, Tokio, or eframe upgrade.
- No changes to doctrinal fixtures or evaluation assertions.
