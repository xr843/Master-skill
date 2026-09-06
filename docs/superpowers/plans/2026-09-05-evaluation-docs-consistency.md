# Evaluation Documentation Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every current-facing evaluation document distinguish historical baseline limitations from the citation auditor and offline re-grader that exist at commit `e7cd7ff`.

**Architecture:** Treat repository scripts and committed reports as the source of truth. Preserve historical measurements in place, add dated correction/status prose around them, and synchronize the Chinese and English top-level summaries without modifying evaluators or evidence files.

**Tech Stack:** Markdown, Python 3 offline evaluation scripts, ripgrep, npm test harness

## Global Constraints

- Preserve the original 2026-08-18 and 2026-08-31 measurements as historical evidence.
- Current re-grade values must be `boundary` 81%, `fidelity` 96%, `pressure` 80%, total 89%, and mention coverage 86%.
- Current re-audit coverage must be 446/601 (74%), with zero known fabricated citations in the stored DeepSeek run.
- Do not claim that DeepSeek evidence satisfies the v1.0 Anthropic gate.
- Do not edit `CHANGELOG.md`, report JSON, verdict JSON, fixtures, or evaluator code.

---

### Task 1: Correct Current-facing Evaluation Summaries

**Files:**
- Modify: `README.md`
- Modify: `README_EN.md`
- Modify: `eval/reports/README.md`
- Modify: `docs/v1-framework-roadmap.md`

**Interfaces:**
- Consumes: `check_response()`'s unconditional audit semantics, `verify_citations.py`'s four contract-family support, and the exact output of `regrade-report.py` / `reaudit-report.py`
- Produces: synchronized current descriptions for readers and release planning

- [x] **Step 1: Replace the bilingual baseline audit rows**

Keep the original `0/84` finding, explicitly label opt-in and CBETA-only behavior
as the 2026-08-18 implementation, then state that the current judge audits every
graded response and that the stored DeepSeek re-audit covers `446/601 (74%)`
citations with zero known fabrication findings. End by saying the Anthropic gate
still needs a fresh full run.

- [x] **Step 2: Rewrite the evaluation report README's auditor section**

Replace `The fabrication check is narrower than it looks` with a current contract
description. State that missing/empty source declarations become
`audit_unavailable`, unparseable blocks remain review evidence rather than clean
passes, and corpus-level SuttaCentral identifiers remain outside deterministic
work-level verification. Follow it with a dated historical note explaining why
the first baseline audited `0/84`.

- [x] **Step 3: Correct the roadmap gate row and measurement note**

Retain `not measured` under the explicitly historical 2026-08-18 column. Change
the rationale from a current instrument blocker to: the old auditor was opt-in
and CBETA-only; the current auditor is unconditional and supports all four
families; the remaining release evidence is a fresh Anthropic run. Update the
offline re-grade snapshot to `81% / 96% / 80% / 89%` and mention coverage `86%`.

- [x] **Step 4: Scan the four files for contradictory current-tense claims**

Run:

```bash
rg -n -i "is opt-in|逐条夹具选配|only recognises CBETA|只认 CBETA|no master persona has ever|祖师无一|blocked on instrument|mention coverage \(85%\)" README.md README_EN.md eval/reports/README.md docs/v1-framework-roadmap.md
```

Expected: no matches outside prose explicitly prefixed as historical behavior.

- [x] **Step 5: Commit the current-facing corrections**

```bash
git add README.md README_EN.md eval/reports/README.md docs/v1-framework-roadmap.md
git commit -m "docs: reconcile current evaluation state"
```

### Task 2: Add Later-status Notes To Historical Reports

**Files:**
- Modify: `eval/reports/BASELINE.md`
- Modify: `eval/reports/BASELINE-deepseek.md`
- Modify: `eval/reports/ADJUDICATION.md`

**Interfaces:**
- Consumes: PR #148's merged state, PR #150's resolved source decisions, and the offline measurements from Task 1
- Produces: historical reports that remain intact while no longer presenting completed work as open

- [x] **Step 1: Add a dated status note to the first baseline's next step**

State that the two auditor prerequisites were completed on 2026-09-03 and that
the remaining action is a fresh full Anthropic run; do not alter the original
table or retraction narrative.

- [x] **Step 2: Qualify the DeepSeek report's old open decision**

After the sentence calling `Toh:3861` open, add that PR #150 later declared it
and that the report's existing correction/Next section records the resolution.

- [x] **Step 3: Update adjudication follow-up status**

Mark the Toh decision as later resolved by PR #150. Replace the stale offline
snapshot with `boundary` 81%, `fidelity` 96%, `pressure` 80%, total 89%, and
mention coverage 86%. Mark PR #148 merged while preserving the caveat that no
fresh live grading run has tested the changed persona output. Keep the five-case
pressure contract question open.

- [x] **Step 4: Verify the adjudication evidence remains unchanged and valid**

Run:

```bash
python3 scripts/verify-adjudication.py
```

Expected: `OK: adjudication-06b8142-deepseek.json — 74 cases, every verdict backed by the answer text`.

- [x] **Step 5: Commit the historical-report addenda**

```bash
git add eval/reports/BASELINE.md eval/reports/BASELINE-deepseek.md eval/reports/ADJUDICATION.md
git commit -m "docs(eval): close stale report follow-ups"
```

### Task 3: Verify Provenance And Repository Health

**Files:**
- Modify: `docs/superpowers/plans/2026-09-05-evaluation-docs-consistency.md` (checkbox status only)

**Interfaces:**
- Consumes: all documentation edits from Tasks 1 and 2
- Produces: reproducible evidence that prose values match repository tools and the repository remains green

- [x] **Step 1: Recompute the offline measurements**

Run:

```bash
python3 scripts/regrade-report.py eval/reports/0.11.0-06b8142-deepseek.json
python3 scripts/reaudit-report.py eval/reports/0.11.0-06b8142-deepseek.json
```

Expected: the exact values in Global Constraints, including `364/421 = 86%`
mention coverage and `446/601 74%` citation coverage.

- [x] **Step 2: Run the full deterministic suite**

Run:

```bash
npm test
```

Expected: 73 Node tests and 578 Python tests pass, with every validator green.

- [x] **Step 3: Run FoJin source-link validation**

Run the same read-only source check configured in
`.github/workflows/verify-links.yml`:

```bash
python3 tools/verify_sources.py
```

Observed at the 2026-09-05 branch point: exit 0, 34/35 identifiers resolved,
and no URL replacements were needed. The apparent `J36n0348` → `J0348` miss
was subsequently corrected to the canonical `J36nB348` → `JB348`; FoJin still
does not resolve it, so issue #158 remains open.

- [x] **Step 4: Review the complete diff and mark this plan complete**

Run:

```bash
git diff --check
git diff origin/main...HEAD -- README.md README_EN.md docs/v1-framework-roadmap.md eval/reports docs/superpowers
```

Expected: no whitespace errors; changes are limited to the seven target docs,
this design, and this plan. Change every completed checkbox in this plan to
`[x]`.

- [x] **Step 5: Commit plan completion**

```bash
git add docs/superpowers/specs/2026-09-05-evaluation-docs-consistency-design.md docs/superpowers/plans/2026-09-05-evaluation-docs-consistency.md
git commit -m "docs(plan): record evaluation consistency work"
```
