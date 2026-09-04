# Evaluation Documentation Consistency Design

**Date:** 2026-09-05  
**Status:** Approved for automatic implementation by the user's standing instruction to continue without repeated confirmation

## Problem

The citation auditor and offline re-grader changed materially on 2026-09-03,
but several current-facing documents still describe the pre-fix implementation:
fixture-level opt-in, CBETA-only parsing, no audited master personas, 85% mention
coverage, and PR #148 as unmerged. The roadmap even says both that all four
citation contract families work and that the auditor is still blocked on adding
them.

Historical reports must continue to say what the original runs measured. The
error is using present tense for limitations that were later fixed, or leaving a
"Next" section unchanged after its work merged.

## Source Of Truth

For the branch point `e7cd7ff`, the repository's offline tools report:

```text
regrade-report.py:
  boundary  36/64 (56%) -> 52/64 (81%)
  fidelity  85/105 (81%) -> 101/105 (96%)
  pressure  16/30 (53%) -> 24/30 (80%)
  total     137/199 (69%) -> 177/199 (89%)
  mention coverage 364/421 = 86%

reaudit-report.py:
  total citation coverage 386/601 (64%) -> 446/601 (74%)
  zero known fabricated citations remain in the stored DeepSeek run
```

`scripts/test-fidelity.py::check_response()` now invokes citation auditing for
every graded response. `scripts/verify_citations.py` resolves CBETA, BDRC/Toh,
PTS/SuttaCentral-contract, and compiled-teaching sources, while honestly leaving
corpus-level SuttaCentral references and source-free meta-skills unverified.

## Design

Use a minimal correction strategy:

1. Preserve original baseline and adjudication numbers as historical evidence.
2. Replace present-tense descriptions of the old auditor with a dated
   "original run versus current implementation" distinction.
3. Put the current offline re-grade numbers only where a document claims current
   status, and name the command and commit that produced them.
4. Mark PR #148 and the four citation decisions as completed, while retaining
   the fact that no fresh full Anthropic run has verified the content change.
5. Keep the v1.0 gate honest: the stored DeepSeek re-audit demonstrates the
   instrument, but cannot satisfy the Anthropic release column.

## Files And Responsibilities

- `README.md`, `README_EN.md`: give readers the original baseline's audit scope
  and the repaired current state in parallel.
- `eval/reports/README.md`: document how the current judge actually audits and
  retain a compact history of why the first baseline's zero was invalid.
- `eval/reports/BASELINE.md`: add a dated status note to its historical next step.
- `eval/reports/BASELINE-deepseek.md`: label the old open Toh decision as later
  resolved.
- `eval/reports/ADJUDICATION.md`: update later-resolution notes and the current
  offline re-grade values without changing the adjudicated headline table.
- `docs/v1-framework-roadmap.md`: remove the internal contradiction and update
  the current re-grade snapshot.

## Non-goals

- Do not edit the committed JSON report or adjudication verdicts.
- Do not reinterpret historical scores as current model measurements.
- Do not change fidelity fixtures, grading code, citation parsing, or release
  thresholds.
- Do not edit `CHANGELOG.md`; the primary worktree has a user-owned uncommitted
  change there, and the open fidelity-gate PR also touches it.
- Do not claim the v1.0 Anthropic gate is satisfied.

## Validation

Re-run both offline measurement scripts, scan current-facing docs for obsolete
claims, run `npm test`, and run the repository's FoJin source-link verifier. The
measurement and test steps are offline; source-link verification is read-only
network access. None of the steps incurs model API cost.

The 2026-09-05 source-link run found one pre-existing external lookup gap:
FoJin resolves 34 of 35 declared CBETA-family identifiers but not `J36n0348`
(`J0348`, master-ouyi). No URL replacements are needed. This is tracked in
GitHub issue #158 and does not invalidate the documentation-only branch.
