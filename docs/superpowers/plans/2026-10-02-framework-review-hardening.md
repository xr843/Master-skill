# Framework review hardening

Implement the five improvements authorized after the 2026-10-01 review, in order.
Use the existing Python 3.9 runtime floor, no new runtime dependencies, no paid
evaluation during implementation. Historical reports remain historical; never
rewrite their evidence to make a new gate pass.

1. Citation evidence: unverified live links require review; distinguish source-ID
   resolution from direct-quote support. Check quotations against declared local
   original excerpts; missing excerpt evidence is unknown, not a fabrication verdict.
   Exercise invented links/quotes and genuine local quotations.
2. Release identity: fingerprint skill instructions, references, source declarations,
   sibling skills used by teaching modes, and evaluation code. Record fingerprints
   on measured suites and require current fingerprints at release. Old reports fail
   closed. Exercise edits, missing digests, and documentation-only changes.
3. Persona evaluation: use the same context loader as deterministic fidelity runs,
   cover all 15 personas with RAW/SPE/CUS and citation fixtures, retain curated
   existing rubrics, and validate coverage. Exercise actual prompt rendering and drift.
4. Installation: stage every replacement, roll back failures, persist installation
   file hashes, detect local modifications before replacement, provide --dry-run and
   --force. Old installations without an inventory are conservatively protected.
   Preserve generated masters and existing all-skill update semantics. Exercise
   user edits, upstream updates, copy/swap failures, legacy installs and previews.
5. Query: --json always returns an array, including zero hits. Exercise CLI output.

Each behavioral change gets a failing regression test before implementation.
Run focused checks per task, then npm test and hook checks; report any desktop
verification limitations separately. Implement sequentially in this branch.

## Implementation verification

All five tasks implemented. Independent review reproduced and closed quote-format,
preceding-attribution and declared-ID-link bypasses. Installation tests also cover
rejecting unsupported uninstall previews and preserving generated-persona links.

- `npm test`: all structural gates, 102 CLI tests and 1334 Python tests passed.
- `npm run test:hook`: 36 tests passed.
- `cargo +1.95.0 test --locked` in `desktop/`: 133 tests passed.
- No paid model sweep was launched, no historical measurement was rewritten, and
  no package was published. The new 15-persona rubrics remain advisory until calibrated.

## Follow-up quality checks

- Added start/end input fingerprint comparison: preserve collected answers, fail the
  run and release gate on changed inputs or missing stability evidence.
- Exercise the pinned Promptfoo CLI against every persona's real fixture questions
  with a local provider comparing exact system/user messages. An intentionally
  reduced prompt must fail. Persona CI requires this integration check; no API key
  or paid model is involved.
- Final verification: `npm test` gates and 102 CLI tests pass; the full Python suite
  with pinned Promptfoo available passes 1339 tests without skips. Hooks pass 36,
  desktop passes 133. Independent review's embedded-blockquote citation bypass is
  closed; focused quotation/response/identity verification passes 65 tests.
- Remote desktop CI exposed eager OpenCC loading during structural dry-runs.
  Reproduced with `python -S`, moved conversion initialization to actual quotation
  checking, and added a standard-library-only all-suite dry-run regression.
  Focused tests pass 83; the Rust baseline passes all 3 tests with a `python -S`
  interpreter wrapper. Graded quotation checking still requires OpenCC.

## Continued online citation verification

The continuation closes an evidence gap within Task 1: a nonempty HTTP 200 JSON
response was sufficient for online success even when it was an error envelope,
or lacked the metadata needed to compare the cited work. Nine regressions first
failed on this path. Online checks now preserve missing metadata and unavailable
title comparison as unknown, while definite mismatches take precedence over
other pending citations sharing the link. The CLI preserves exit 2 for unknown.
The live FoJin `api/texts/20` response was checked read-only: it is a dictionary
with id 20, CBETA id T0366 and the Chinese title of the Amitabha Sutra.
No paid model call, historical report rewrite, merge or package publish is part
of this continuation. Keep all changes on the existing review branch.

Verification: 147 citation tests pass, including 16 new cases; independent
review finds no material issue. `npm test` gates and 102 CLI tests pass, with
1354 Python tests passing and the 2 CI-only Promptfoo integrations skipped locally.

## Keyless evaluation planning

Continue toward the release measurement by adding `--plan` to the existing runner.
Use its actual fixture selection and runtime context preparation; report model,
digests, initial context bytes, configured output/concurrency/retry/time limits,
initial request counts and maximum SDK attempts where the implementation bounds
them. Represent Task fanout as unknown rather than inventing a paid-call ceiling.
Plans must not load SDKs, read keys, make API requests or claim graded evidence.
No price estimate or monetary cap is part of this bounded change.

Seven initial CLI regressions first failed for the missing flag. Added file-tool
request accounting, plan/preview fixture-selection agreement and human-output
checks. Ten focused tests pass in a `python -S` subprocess. The current whole-tree
plan covers 19 suites and 211 fixtures; the initial output limits sum to 1,783,808
tokens, excluding all follow-up requests. Only master-debate lacks a request bound.
Independent review finds no material issue. `npm test` passes all structural gates,
102 CLI tests and 1364 Python tests; the 2 CI-only Promptfoo integrations are
skipped locally. Existing graded-run and structural-preview regression tests pass.
Two additional CLI regressions exposed NaN/infinite timeout values bypassing the
positive-number check; finite timeout validation now rejects both before planning
or paid execution. Regenerate the plan after this grader change.
Final local verification: 12 plan CLI tests pass; full `npm test` passes its gates,
102 CLI tests and 1366 Python tests (2 CI-only integrations skipped). The keyless
whole-tree plan was regenerated against the final grading code.

## Complete teaching-mode input coverage

Continued inspection found that SkillFiles permits more files than the original
fingerprint whitelist: auxiliary text files, non-persona skills and empty directory
entries can affect tool responses without invalidating the measurement. Three
initial regressions reproduced missing coverage and linked-source-directory
bypasses. Teaching-mode fingerprints now bind the complete tool-visible prebuilt
tree; tests/ stays excluded with the same casefold rule as file tools. Persona
context scope is retained. Directory types are framed separately from file bodies.

Reject symlinks along each input's ancestor path; do not open FIFOs or device nodes
while fingerprinting their visible names. A subprocess regression reproduced the
FIFO hang with unsafe reading enabled, then passed with the read guard restored.
Runtime input preparation errors return an error suite before API initialization,
preserving batch reporting. Two such regressions failed before this error handling.
Historical reports remain unchanged; regenerate planning artifacts after this code
change. No paid evaluation, merge or package publish was performed.

Independent review reproduced a second FIFO hang in context loading after the
fingerprint had completed. Context reads now reject nonregular files. Six full
preparation subprocess cases cover SKILL.md, sources and references in plan and
graded modes; the SKILL.md case first timed out before the loader guard, then all
six returned structured errors without initializing an API client.

Final local verification: full npm test gates and 102 CLI tests pass; 1379 Python
tests pass with 2 CI-only integrations skipped. The actual pinned Promptfoo CLI
was then exercised separately: all 4 runtime-loading tests pass, including the
negative control. The keyless plan was regenerated: 19 completed suites and 211
fixtures. The independent review's only material finding was the loader FIFO hang
addressed above.

## Validate runtime catalog before evaluation

Continued inspection found that skill_kind directly indexed catalog entries and
returned None for a missing selected directory. Malformed entries could abort the
batch; missing or unsupported kinds could silently remove teaching-mode tools.
Eighteen plan/graded regressions first failed for these shapes. Validate the root,
skills list, required string fields, supported kinds and unique names/directories;
reject a missing selected directory through the existing input-error suite path.
The recommendation-name consumer shares this validation. Keep dry-run independent
of runtime configuration and avoid API calls for these checks.

A CLI batch regression checks that a completed plan remains in JSON output when
a later selected skill lacks a catalog record, with a nonzero overall exit code.
Focused runtime-tool, planning and exit tests pass 77 cases. Keep this continuation
on the existing PR branch; perform independent review and full npm test before
committing. Regenerate the keyless plan after grader changes.

Verification complete: npm test passes all structural gates, 102 CLI tests and
1398 Python tests (2 CI-only integrations skipped). Independent review found no
material issues and reproduced a standard-library-only plan for 19 suites / 211
fixtures. Catalog fields unrelated to runtime kind/name/directory selection are
left to their existing validators; dry-run behavior and recommendation-name cache
remain unchanged. Active-run edits remain governed by the end-of-run fingerprint.
