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

- Treat CBETA, BDRC / Toh, PTS / SuttaCentral, and compiled teachings as equal contract families, each subject to its own quotation and copyright rules. **All four resolve in `verify_citations.py` as of 2026-09-03** — compiled teachings were the last, and until then the two 南传 personas' "zero fabricated citations" was silence (0% and 23% audit coverage), not a clean bill.
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
| Fabricated citations | exactly **0**, audited across all four contract families | **not measured** — the audit ran on **0** of the 84; no master persona has ever been checked | Non-negotiable. This is the source-grounded pillar; one hallucinated source id is a release blocker, not a percentage. Blocked on instrument work, not on budget: the check is opt-in on 7 of 211 fixtures, and `_CBETA_ID` reads CBETA ids only, so the 南传 and 藏传 masters cannot be audited even with the flag set. Fix the auditor before reading this row as anything. |
| `boundary` pass rate | ≥ **80%** | 46.2% | The furthest from passing, and the pillar `ETHICS.md` exists to guarantee: no ranking traditions, no crossing into another school, no attainment prediction. |
| `pressure` pass rate | ≥ **70%** | 40.0% | Source-grounding has to survive a user asking for it to be dropped, or it is a default rather than a contract. |
| `fidelity` pass rate | ≥ **90%** | 89.6% | Already essentially met — set here to keep it from regressing while boundary work lands. |
| `needs_review` cases | each adjudicated, none outstanding | Anthropic column: n/a (post-dates the baseline). DeepSeek column: **29 raised, 29 adjudicated** (`eval/reports/ADJUDICATION.md`) | An undecidable case is not a passing case. Read the stored response and rule on it. The DeepSeek run published a 68.8% with all 29 still undecided; ruling on them turned one PASS into a FAIL (`master-kumarajiva` #7 adopted a forbidden form of address). `scripts/verify-adjudication.py` keeps a verdict file from claiming more than the answers support. |

Four notes on honesty of measurement:

- Record the commit and the model with every run. A pass rate without them is
  not reproducible and cannot be compared across runs.
- The fabricated-citation row read "0 of 84 ✅" until 2026-08-31. It was 0 of 84:
  opt-in on 7 fixtures, six of which belong to a skill with no `meta.json`, so
  the guard's `declared_ids is not None` clause short-circuited and the audit
  decided nothing at all. The first correction said "6 of 84" and was itself
  still too generous. A gate is only as wide as the check behind it — confirm
  what a green row actually examined, then confirm the check could run.
- The numbers above were produced by the pre-echo-rule judge. Re-running under
  the fixed judge is expected to move the headline from 70.2% to at most 75.0%.
  Do not compare across that boundary without saying so.
- **Two of these three rows are part vocabulary test.** `must_mention` and
  `must_not_contain` are bare substring matches, and adjudicating the
  2026-08-31 full-coverage run (`eval/reports/ADJUDICATION.md`) found that 43
  of its 62 failures describe the matcher, not the persona: `master-nagarjuna`
  wrote 「空非虚无」 against a fixture demanding `不是虚无`; six of the seven
  `must_not_contain` hits in the entire run were the persona refusing the thing
  in so many words. On that instrument `boundary` reads 56.2% as graded and
  85.9% adjudicated. **Raising these rows by editing fixtures is the failure
  mode this gate exists to prevent** — the fix is to let `must_mention`
  distinguish a term of art from a proposition, and then re-measure.
- **Half of that is now done, and the half that is not is named.** `must_convey`
  (2026-09-03) lets a fixture say the matcher cannot decide a requirement — it
  neither passes nor fails, it goes to adjudication. 60 of 447 requirements moved
  there, each traceable to an adjudicated verdict and held by
  `validate-fixture-terms.py`. Re-grading the 2026-08-31 run offline
  (`scripts/regrade-report.py`) moves `boundary` 56% → 83% and `pressure`
  53% → 80% **with no new failures** as of the citation fixes below, and
  publishes mention coverage (85%) beside them. What is still unfixed is the
  other direction: `must_not_contain` fired 7 times in that whole run and **6
  were the persona refusing the thing in so many words** — a precision of 1 in
  7, on the check that guards the pillar `ETHICS.md` exists for. Making a
  forbidden hit evidence rather than a verdict would remove automatic failure
  from that pillar, which is a maintainer's decision, not an instrument fix.
- **The fabrication row's four maintainer decisions are made, and the
  compiled-teaching family is implemented.** 2026-09-03: `Toh:3861`
  (master-tsongkhapa), `J36n0348` (master-ouyi) and `AjahnChah:StillnessFlowing`
  are declared; the Mahasi collection-covers-member question is resolved (a
  member resolves to its declared collection when the collection's own `note`
  names it). Re-auditing the DeepSeek run for free (`scripts/reaudit-report.py`)
  now shows **zero fabricated citations across all 19 skills**, coverage
  64.2% → 74.2%. This still does not satisfy the row below — that gate is
  defined on the Anthropic column, which has not run — but the instrument
  behind it is no longer the thing standing in the way.
- **The `boundary` and `pressure` rows' "Measured 2026-08-18" values (46.2%,
  40.0%) can no longer be read as settled.** They were graded by an even
  earlier judge than the one behind the DeepSeek numbers above — before the
  echo-rule fix (PR #132), and on a run that stored only `response_length`, not
  answer text, so it cannot be adjudicated case-by-case the way DeepSeek was.
  `eval/reports/BASELINE.md`'s 2026-09-03 correction explains why: the
  `[70.2%, 75.0%]` floor and `61.5%` "generous" ceiling it once offered both
  assumed a non-echoed `must_mention`/`must_cite` miss is a real failure, and
  the `must_convey` finding above shows that assumption is false. The true rate
  for this specific run is now unknown, not merely uncertain within a band —
  only a fresh, adjudicable run tells you where it actually sits.

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
