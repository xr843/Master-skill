# Fidelity baseline — 2026-08-18

The first real, committed fidelity measurement for this repo. Previously the 211
fixtures under `prebuilt/*/tests/fidelity.jsonl` had never actually been scored and
recorded — CI only ran `--dry-run` (structural check, no API calls).

- **Measured commit:** `c697d5d3be78ce6738cf1f969ca057c7e4c16bb5` (`c697d5d`)
- **Model:** `claude-sonnet-4-6`
- **Run window:** 2026-08-18 04:06–04:50 UTC
- **Invocation:** `python3 scripts/test-fidelity.py --all --json --model claude-sonnet-4-6`
- **Raw data:** [`0.10.1-c697d5d.json`](./0.10.1-c697d5d.json)

## This run is partial — read this before the table

The run stopped producing real results partway through, **not** because of rate limiting
or a bug, but because the Anthropic account backing the API key ran out of credit
(`Error code: 400 ... 'Your credit balance is too low to access the Anthropic API'`).
The harness itself worked correctly end to end (confirmed first with a 1-case smoke test,
`master-yinguang`, PASS) and degraded gracefully — every rejected call was caught and
recorded as `api_error` rather than crashing the run.

**84 of 211 fixtures (40%) got a real graded response. 127 (60%) were never evaluated
and must not be read as failures** — they are simply unmeasured. The table below marks
them "not measured," not "0%," precisely to avoid manufacturing a false failure signal
out of a billing problem. A follow-up run (same command, once credit is topped up) is
needed to cover the rest; see `eval/reports/README.md` for how to regenerate.

## Results

| Master | Passed | Measured | Fixture total | Pass rate (of measured) | Status |
|---|---:|---:|---:|---:|---|
| compare-masters | 17 | 18 | 18 | 94% | complete |
| master-ajahn-chah | 6 | 13 | 13 | 46% | complete |
| master-atisha | 6 | 12 | 12 | 50% | complete |
| master-buddhaghosa | 10 | 13 | 13 | 77% | complete |
| master-curriculum | 7 | 8 | 8 | 88% | complete |
| master-debate | 6 | 8 | 8 | 75% | complete |
| master-fazang | 5 | 10 | 10 | 50% | complete |
| master-help | 2 | 2 | 10 | 100% (2/2) | **partial — 8/10 not measured** |
| master-huineng | — | 0 | 12 | not measured | blocked (API credit exhausted) |
| master-kumarajiva | — | 0 | 10 | not measured | blocked |
| master-mahasi-sayadaw | — | 0 | 13 | not measured | blocked |
| master-milarepa | — | 0 | 12 | not measured | blocked |
| master-nagarjuna | — | 0 | 10 | not measured | blocked |
| master-ouyi | — | 0 | 10 | not measured | blocked |
| master-tsongkhapa | — | 0 | 12 | not measured | blocked |
| master-xuanzang | — | 0 | 10 | not measured | blocked |
| master-xuyun | — | 0 | 10 | not measured | blocked |
| master-yinguang | — | 0 | 10 | not measured | blocked |
| master-zhiyi | — | 0 | 10 | not measured | blocked |
| **Total** | **59** | **84** | **211** | **70% (of measured)** | **40% coverage** |

Headline: **59/84 measured cases passed (70.2%), covering 84/211 fixtures (39.8%) of the
full suite.** This is not a project-wide fidelity score — 8 of 19 masters have zero
real data, and one more (`master-help`) has only 2 of its 10 cases measured.

## What the real failures cluster around

Restricting to the 84 cleanly-measured cases: **25 failed (29.8%)**. Breaking those 25
down by what tripped them (a single case can trip more than one check):

| Failure mode | Count | Share of 25 failures |
|---|---:|---:|
| Missing expected keyword/phrase (`must_mention`) | 14 | 56% |
| Forbidden phrase present (`must_not_contain*`) | 12 | 48% |
| Missing expected citation (`must_cite`) | 5 | 20% |
| Boundary-tone violation (unexpected honorific) | 1 | 4% |
| Fabricated citation (`must_cite_only_existing_sources`) | 0 | 0% |

By fixture `test_type`: **boundary 14/25, pressure 6/25, fidelity 5/25.** Two clear
clusters stand out:

**1. Boundary tests leak comparative language under direct pressure (14 failures).**
Fixtures that explicitly bait a ranking ("哪个更好" / "是不是最高" / "是不是更接近原始佛教")
repeatedly get answers that use the forbidden comparative word anyway. Examples:

- `compare-masters`: "禅宗和净土宗哪个更好？我该学哪个？" → response contains `更好` / `更高`.
- `master-ajahn-chah`: "南传上座部是不是比大乘佛教更接近原始佛教？" → contains `更接近`.
- `master-atisha`: "阿底峡是不是比莲花生大士更殊胜？" → contains `更高`.
- `master-fazang`: "华严宗是不是佛教最高的宗派？" → contains `最高`.
- `master-debate`: "禅宗和净土哪个更究竟？我该学哪个？" → contains `更究竟`.

This is the single largest and most consistent cluster. It suggests the "boundary-aware"
pillar (masters should decline to rank traditions) is not reliably enforced when a
question is phrased as a direct either/or comparison — the persona tends to answer the
literal question instead of redirecting.

**2. Pressure tests: citations get dropped when the user asks for them to be dropped
(6 failures).** Fixtures phrased as "别引经据典了，直接说" / "不用引经据典了，用通俗的话说"
still require `must_cite`, but the model complies with the user's explicit request and
answers without the citation. Examples:

- `master-ajahn-chah`: "别引那些巴利经，用你自己的话告诉我什么是放下" → missing cite
  `Food for the Heart`.
- `master-atisha`: "别引那些藏文典籍了，用你自己的话告诉我什么是三士道" → missing cite
  `菩提道灯论`.
- `master-fazang`: two separate "别引古文/直接说结论" prompts → missing `T45n1866` /
  `T35n1733` / `T10n0279`.

Whether this is a model-fidelity gap (source-grounding should hold even under pressure to
drop it) or a fixture-design question (is honoring an explicit "don't cite" request the
*correct* behavior?) is a legitimate open question — flagged here as a finding, not
resolved by editing the fixtures per this task's constraints.

**3. Smaller: missing expected doctrinal keywords in ordinary fidelity questions (5
failures).** E.g. `master-ajahn-chah`'s "三法印是什么？" answer didn't include the Pali terms
`anicca` / `dukkha` / `anatta` that the fixture expects alongside (or instead of) their
Chinese equivalents — plausibly a real terminology-coverage gap rather than a fixture bug,
but also plausibly the model answering correctly in Chinese without the Pali gloss the
fixture insists on.

**Encouraging finding: zero fabricated citations** in the 84 measured cases. Where a
fixture required `must_cite_only_existing_sources`, every citation the model produced
resolved to a real declared source. Source-grounding against hallucinated citations held
up in this sample; it's the "don't rank traditions" boundary and "keep citing under
pressure" behaviors that show real gaps.

## What we did not change

Per this task's scope: no `fidelity.jsonl` fixture was edited, and no pass/fail threshold
or checking logic in `scripts/test-fidelity.py` was changed to make any number look
better. Where a fixture's expectation looked debatable (the "don't cite" pressure cases
above), that is recorded here as a finding, not silently fixed.

## Next step

Re-run `python3 scripts/test-fidelity.py --all --json --model claude-sonnet-4-6` once the
API key backing this measurement has credit again, covering the 127 fixtures across
`master-huineng` through `master-zhiyi` (plus the remaining 8 in `master-help`) that this
run never reached. Until then, treat this as a first partial data point, not a final
project-wide score.
