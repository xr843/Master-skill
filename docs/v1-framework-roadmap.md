# Master-skill v1.0 Framework Roadmap

Master-skill v1.0 should mark framework stability, not roster expansion. The goal is to make the existing 15 masters trustworthy, testable, installable, and governed.

## Positioning

> FoJin-powered Buddhist AI persona framework: source-grounded, boundary-aware, fidelity-tested, runtime-ready.

The four pillars map directly to implementation work:

| Pillar | v1.0 meaning |
|---|---|
| Source-grounded | Every doctrinal claim is backed by the persona's declared sources; live retrieval is used only when its contract permits it |
| Boundary-aware | Runtime answers obey ethics, copyright, and religious-practice boundaries |
| Fidelity-tested | Every master has deterministic fixtures and persona-fidelity coverage |
| Runtime-ready | npm install, hooks, slash commands, and FoJin fallback behave predictably |

## Phase 1: Alignment

Status: in progress.

- Align README, README_EN, PRD, npm description, and GitHub description.
- Replace obsolete `teachers/` and "Chinese-only" language in docs with `prebuilt/master-*` and four-tradition language.
- Document the FoJin runtime contract.
- Keep historical design notes in `docs/superpowers/` but make `docs/PRD.md` the current product contract.

## Phase 2: Citation Contract

Status: implemented in v0.10.1; fidelity coverage continues in Phase 3.

- Treat CBETA, BDRC / Toh, PTS / SuttaCentral, and compiled teachings as equal contract families, each subject to its own quotation and copyright rules.
- Require all 15 personas to declare the versioned `citation_contract` in `meta.json`.
- Validate exact policy fields and require `allowed_source_types` to equal the persona's sorted unique `sources[].type` values.
- Require doctrinal claims, practice guidance, and text interpretation to cite declared source identifiers; permit live retrieval only when `live_retrieval_allowed` is true.
- Add one citation-focused fidelity case per master if missing.

## Phase 3: Full Persona-Fidelity Coverage

Current representative promptfoo coverage exists for a subset of masters. v1.0 should cover all 15.

Minimum per master:

- 1 RAW case: instruction following and boundary behavior.
- 1 SPE case: school-specific doctrinal fidelity.
- 1 CUS case: voice/style fidelity using `signature_phrases` and `style.qa`.
- 1 citation case: answer must cite a declared source; live retrieval may supply it only when the persona contract permits retrieval.

Evaluation policy:

- Schema validation is a hard gate.
- LLM-as-judge grading remains advisory unless a stable budget and secret policy is in place.
- Results should be uploaded as CI artifacts when available.

## Phase 4: Teaching Mode Contracts

Document and enforce output contracts for the three meta-skills.

`/compare-masters` should include:

- common ground,
- core divergence,
- fitting use cases/root concerns,
- recommended follow-up master,
- citations.

`/master-debate` should preserve:

- no winner judgment,
- no strawman,
- sourced `cross_critique` ammunition,
- final neutral summary.

`/master-curriculum` should include:

- L0-L3 stage,
- core texts,
- practice/research cautions,
- recommended masters,
- source-backed next steps.

## Phase 5: Runtime And CLI Polish

Candidate v1.x CLI improvements:

```bash
npx master-skill doctor
npx master-skill inspect master-huineng
npx master-skill update --all
```

These are useful but not required for v1.0 unless the current install/update path becomes a blocker.

## Phase 6: Release

### Fidelity gate (numeric)

Every checklist item this project has ever had was procedural — "tests pass",
"docs are consistent". A framework whose positioning is *fidelity-tested* should
gate v1.0 on the fidelity numbers themselves. Since 2026-08-18 there is a
measured baseline to set them against (`eval/reports/BASELINE.md`), so they can
be real thresholds rather than aspirations.

| Gate | Threshold | Measured 2026-08-18 | Why this number |
|---|---|---|---|
| Coverage | 211 / 211 fixtures graded | 84 / 211 (40%) | A partial run is not a release baseline. Any suite reporting 0 verdicts fails `check-gate-liveness.py`. |
| Fabricated citations | exactly **0**, audited across all four contract families | **not measured** — the audit ran on 6 of the 84, all in `master-curriculum`; no master persona was checked | Non-negotiable. This is the source-grounded pillar; one hallucinated source id is a release blocker, not a percentage. Blocked on instrument work, not on budget: the check is opt-in on 7 of 211 fixtures, and `_CBETA_ID` reads CBETA ids only, so the 南传 and 藏传 masters cannot be audited even with the flag set. Fix the auditor before reading this row as anything. |
| `boundary` pass rate | ≥ **80%** | 46.2% | The furthest from passing, and the pillar `ETHICS.md` exists to guarantee: no ranking traditions, no crossing into another school, no attainment prediction. |
| `pressure` pass rate | ≥ **70%** | 40.0% | Source-grounding has to survive a user asking for it to be dropped, or it is a default rather than a contract. |
| `fidelity` pass rate | ≥ **90%** | 89.6% | Already essentially met — set here to keep it from regressing while boundary work lands. |
| `needs_review` cases | each adjudicated, none outstanding | n/a (post-dates the baseline) | An undecidable case is not a passing case. Read the stored response and rule on it. |

Three notes on honesty of measurement:

- Record the commit and the model with every run. A pass rate without them is
  not reproducible and cannot be compared across runs.
- The fabricated-citation row read "0 of 84 ✅" until 2026-08-31. It was 6 of 84,
  none of them a master persona, on an auditor that reads one of the four
  declared contract families. A gate is only as wide as the check behind it —
  confirm what a green row actually examined before setting a threshold on it.
- The numbers above were produced by the pre-echo-rule judge. Re-running under
  the fixed judge is expected to move the headline from 70.2% to at most 75.0%.
  Do not compare across that boundary without saying so.

### Release checklist

- The fidelity gate above is met, and the run backing it is committed under `eval/reports/`.
- `npm test` passes on a clean checkout.
- `scripts/check-gate-liveness.py` passes — no gate examined an empty set.
- Documentation uses the framework positioning consistently.
- No open P0/P1 ethics, citation, or security issues.
- Changelog includes v1.0 positioning and migration notes.
- npm package metadata uses the v1.0 tagline.
- GitHub description matches the framework positioning.

## Post-v1 Master Expansion Gate

New masters should wait until the framework is stable. After v1.0, require:

- copyright Tier review,
- at least 3 primary or declared sources,
- complete `meta.json`, `SKILL.md`, `references/`, `sources/`, and tests,
- at least 8-10 fidelity fixtures,
- explicit Layer 0 boundary rules,
- no living-teacher persona without future governance approval.
