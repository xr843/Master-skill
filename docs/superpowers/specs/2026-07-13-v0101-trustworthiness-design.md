# v0.10.1 Trustworthiness Closure Design

**Date:** 2026-07-13  
**Target branch:** `agent/v0101-trustworthiness`  
**Goal:** Close the three highest-value gaps before further feature or persona expansion: complete distribution, cross-tradition citation enforcement, and truthful CI gates.

## Scope and chosen approach

Three implementation agents will work concurrently in isolated worktrees. Each agent owns a disjoint file set and commits only its work. The integration branch cherry-picks the three reviewed commits and runs the complete quality suite.

The selected distribution approach is one complete `master-skill` npm package. Two alternatives were considered and rejected for v0.10.1:

1. Splitting the generator into a second npm package would create cleaner long-term package boundaries, but it adds migration and documentation work that is not justified for a patch release.
2. Keeping npm persona-only and requiring a Git clone for `/create-master` is smaller, but contradicts the advertised single-package installation experience.

The citation work uses one source-family-neutral contract. Retaining CBETA-only rules would remain incorrect for Tibetan and Theravada sources, while separate hard-coded rules in each skill would preserve the current drift.

The CI work makes deterministic and graded failures observable and enforceable. Missing paid API credentials remain an explicit advisory skip, not a fabricated pass.

## Workstream A: complete npm distribution and install contract

### User-visible contract

- The npm tarball contains every runtime resource referenced by the root `create-master` skill: `tools/`, `prompts/`, `references/`, `requirements.txt`, `ETHICS.md`, and an initially empty `masters/` destination.
- `master-skill install --all` installs 19 skills: 15 personas, 3 teaching modes, and the `create-master` generator.
- `master-skill install compare-masters` installs the existing `prebuilt/compare` source at `~/.claude/skills/compare-masters`.
- `master-skill install create-master` copies a self-contained generator bundle to `~/.claude/skills/create-master`; it must continue to work after the transient `npx` package directory disappears.
- Existing persona aliases such as `zhiyi` and `master-zhiyi` remain compatible.

### Internal design

Add `skill-catalog.json` at the repository root. Each record declares `name`, `kind` (`persona`, `teaching-mode`, or `generator`), `source`, `install_dir`, `aliases`, and an optional `bundle_paths` array used only by the generator. The CLI uses this catalog for installation instead of deriving installability from directory names.

The `create-master` record's `bundle_paths` is exactly `SKILL.md`, `tools/`, `prompts/`, `references/`, `requirements.txt`, `ETHICS.md`, and `masters/`. The catalog contains exactly 19 records; duplicate names, aliases, sources, or install directories are fatal.

`list --json` adds a complete `skills` array and category counts. The existing `masters` field remains during v0.10.x as a backward-compatible desktop API and retains its existing shape. Human-readable `list` displays all installable skills grouped by kind.

The generator is copied using an explicit bundle allowlist rather than copying the whole npm package. Missing declared bundle entries are fatal and result in a non-zero exit.

### Error handling and tests

Tests must first reproduce these failures against current code:

- packed tarball omits the generator runtime directories;
- `install --all` omits `compare-masters` and `create-master`;
- `install compare-masters` fails;
- a generator installed from the packed tarball has dangling required paths.

Acceptance requires an end-to-end test that runs `npm pack`, extracts the tarball into a temporary directory, invokes that packaged CLI with an isolated home, and verifies all 19 installed `SKILL.md` files plus the generator's required runtime paths.

Owned files: `package.json`, `bin/cli.mjs`, `tests/cli.test.mjs`, the new catalog, and distribution-focused README sections only.

## Workstream B: cross-tradition citation contract

### Contract

Replace project-wide CBETA-only wording with:

> No doctrinal claim without a declared, verifiable source citation.

Each of the 15 persona `meta.json` files gains a versioned `citation_contract` object with these exact fields:

```json
{
  "version": 1,
  "claim_policy": "declared_sources_only",
  "required_for": ["doctrinal_claim", "practice_guidance", "text_interpretation"],
  "allowed_source_types": ["types present in this persona's sources array"],
  "minimum_claim_coverage": 0.9,
  "live_retrieval_allowed": true
}
```

`allowed_source_types` must equal the sorted unique `sources[].type` values declared by that persona; it may not introduce undeclared source families. Meta-skills do not receive persona citation contracts.

### Validator and runtime text

Add `scripts/validate-citation-contract.py`. It checks all 15 persona contracts, validates exact field types and values, rejects missing or extra allowed source types, and reports the persona path with every error. `scripts/tests/test_validate_citation_contract.py` covers CBETA, Tibetan, Pali, compiled-teaching, missing-contract, and type-drift cases.

Root `SKILL.md`, `compare-masters`, the doctrine reviewer prompt, runtime ethics summary, source conventions, PRD, and roadmap must use the neutral contract. Cross-tradition comparison must filter against each persona's declared source identifiers rather than `primary_cbeta_ids` only.

No source identifiers, quotations, or doctrinal positions are changed in this workstream.

Owned files: root and compare skill instructions, the 15 persona metadata files, citation/reference documentation, the new validator, and its tests.

## Workstream C: truthful quality gates

### Fidelity exit semantics

`scripts/test-fidelity.py` returns non-zero when any graded suite contains a failed case, an API error, or a top-level error. A successful dry-run still returns zero. JSON output remains clean and parseable on stdout; diagnostics go to stderr when needed.

The scheduled full-fidelity workflow keeps the no-key path advisory, but writes an explicit GitHub step summary stating that grading did not run. When a key is present, graded failures fail the job.

### Complete test discovery

- PR smoke selection dynamically discovers all 15 personas from repository metadata/source declarations; no fixed roster is allowed.
- CI runs both `tests/` and `scripts/tests/`.
- `tests/test_voice_rules.py` discovers `references/voice.md`. Empty persona discovery is a test failure, not six skipped parametrizations. Its assertions must reflect the current progressive-disclosure architecture instead of requiring obsolete inlined voice content.
- Lore-trigger content validation becomes a hard gate because the repository currently passes strict validation.
- Rust CI runs `cargo fmt --check` and `cargo clippy --locked --all-targets -- -D warnings` before tests. The currently reproduced `option_as_ref_deref` warning is fixed without unrelated refactoring.

### Tests

Tests first reproduce the fidelity zero-exit bug, zero voice-test discovery, and 14-person smoke roster. Add subprocess exit tests in `tests/test_fidelity_exit.py`; repair `tests/test_voice_rules.py`; and add static workflow assertions in `scripts/tests/test_validate_workflow.py`. No test may depend on paid API calls.

Owned files: `scripts/test-fidelity.py`, fidelity/voice regression tests, `.github/workflows/validate-and-test.yml`, and the minimal Rust line required for a clean clippy gate.

## Parallel integration and review

The three worktrees start from the same design commit. They must not edit another workstream's owned files. Each agent follows red-green-refactor, records the failing command and expected failure before production changes, runs focused tests, commits, and reports its root-cause evidence.

After all agents finish:

1. Review each workstream against this specification and for code quality.
2. Cherry-pick the approved commits onto `agent/v0101-trustworthiness`.
3. Resolve only integration-level conflicts; overlapping production edits indicate a scope violation and are returned to the responsible agent.
4. Run `npm test`, all Python tests, strict citation/lore validators, npm packed-tarball integration tests, Rust fmt/clippy/tests, and workflow syntax checks available locally.
5. Perform a whole-branch review before declaring completion.

## Non-goals

- No new personas or teaching modes.
- No npm package split.
- No desktop product redesign or Issue #113 concurrency work.
- No paid LLM evaluation policy change.
- No changes to historical quotations, source excerpts, or doctrinal content.
- No remote push, release, or pull request creation.
