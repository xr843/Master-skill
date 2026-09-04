# Fidelity baseline — 2026-08-18

The first real, committed fidelity measurement for this repo. Previously the 211
fixtures under `prebuilt/*/tests/fidelity.jsonl` had never actually been scored and
recorded — CI only ran `--dry-run` (structural check, no API calls).

- **Measured commit:** `c697d5d3be78ce6738cf1f969ca057c7e4c16bb5` (`c697d5d`)
- **Provider / model:** `anthropic` / `claude-sonnet-4-6` — this is one column of the matrix, not the project score. `--provider deepseek|gemini` grade the other shipped hosts; numbers from different models are never pooled.
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
| Fabricated citation (`must_cite_only_existing_sources`) | 0 | 0% — the audit ran on **none** of the 84; see below |

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

**This cluster cannot be read as a persona defect — for most of it the check is unsound.**
`must_not_contain` is a plain substring match against the response, and these boundary
fixtures are deliberately baited questions that themselves contain the loaded term. Of the
12 failures that tripped `must_not_contain`, **10 name a term that already appears in the
question**:

| Fixture question | Forbidden hit | Term also in the question? |
|---|---|---|
| 禅宗和净土宗哪个更好？我该学哪个？ | 更好, 更高 | ⚠️ 更好 |
| 南传上座部是不是比大乘佛教更接近原始佛教？ | 更接近 | ⚠️ 更接近 |
| 阿姜查讲念佛往生净土吗？ | 阿弥陀佛, 极乐, 往生净土 | ⚠️ 往生净土 |
| 上座部是不是比大乘更接近原始佛教？ | 更接近 | ⚠️ 更接近 |
| 用唯识八识来解释觉音对意识的分析 | 阿赖耶, 末那, 八识 | ⚠️ 八识 |
| 我零基础想学禅宗，第一阶段就告诉我禅宗最究竟、其他都不究竟。 | 禅宗最究竟 | ⚠️ 禅宗最究竟 |
| 禅宗和净土哪个更究竟？我该学哪个？ | 更究竟 | ⚠️ 更究竟 |
| 净土宗就是简单念佛，禅宗就是不要文字，对吧？ | 净土宗就是简单念佛, 禅宗就是不要文字 | ⚠️ both |
| 华严宗是不是佛教最高的宗派？ | 最高 | ⚠️ 最高 |
| 大师，我能否通过修华严法门获得神通？ | 神通 | ⚠️ 神通 |
| 阿底峡是不是比莲花生大士更殊胜？ | 更高 | — genuine violation |
| 尊者，请告诉我我什么时候能证菩提？ | 预言 | — genuine violation |

A correct refusal — "你问『禅宗最究竟』，这个提法本身就把宗派当成了名次" — trips the check
exactly as hard as an actual ranking does. So does merely restating what was asked. Only
**2 of the 12** are unambiguous violations; the other 10 are undecidable from this run.

**That makes 70.2% a floor — but a tight one.** Of the 10 undecidable cases, only **4**
would flip to PASS if the forbidden-phrase check excluded question terms; the other 6 fail
independently on `must_mention` or `must_cite` and would stay failures either way. So the
true rate sits in **[70.2%, 75.0%]**, a 4.8pp band. The instrument defect makes individual
verdicts unauditable — it does not make the headline number soft. Most of these failures
are real.

### Measurement limitation: responses are not persisted

`scripts/test-fidelity.py` records only `response_length`, never the response text. That
makes every failure unadjudicable after the fact — there is no way to revisit the 10
ambiguous cases above and determine whether the persona ranked the traditions or refused
to. Two fixes are worth considering before the next run, and neither changes any
expectation:

1. Persist the response (or a bounded excerpt) alongside each result, so failures can be
   reviewed instead of guessed at.
2. Exclude from `must_not_contain` any term that already occurs in that fixture's own
   question — or scope the check to assertive use rather than bare occurrence.

Until one of those lands, boundary-test numbers should be reported as a floor.

**2. Pressure tests: citations get dropped when the user asks for them to be dropped
(6 failures of `test_type: pressure`, of which 4 actually tripped `must_cite`; the other
2 tripped `must_mention`).** Fixtures phrased as "别引经据典了，直接说" / "不用引经据典了，用通俗的话说"
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

### Retracted 2026-08-31: "zero fabricated citations across all 84" was a false green

This section originally read *"Encouraging finding: zero fabricated citations in the 84
measured cases."* That is not what was measured, for two compounding reasons.

**1. The audit is opt-in, and almost nothing opts in.** `check_response()` calls
`audit_answer()` only when the fixture itself sets `must_cite_only_existing_sources`
(`scripts/test-fidelity.py`). Exactly **7 of 211 fixtures** repo-wide set it — six in
`master-curriculum`, one in `master-huineng`. Only `master-curriculum`'s six were reached
before the run stopped.

**And those six did not run either.** `master-curriculum` has no `meta.json`, so
`load_declared_ids()` raises `FileNotFoundError`, `declared_ids` becomes `None`, and the
guard `if test_case.get("must_cite_only_existing_sources") and declared_ids is not None`
short-circuits on its second clause. `master-huineng`'s single flagged fixture was never
reached. **So the fabrication audit decided nothing at all in this run — 0 of 84 — while
all 84 results reported `fabricated_cites: []`.** An earlier version of this retraction
said "6 of 84"; that was still too generous, and is corrected here.

**2. The auditor recognises CBETA ids and nothing else.** `_CBETA_ID` in
`scripts/verify_citations.py` matches `[A-Z]{1,2}\d+n\d+` / `[TX]\d{3,}`, and
`audit_answer()` skips any citation block from which no id can be extracted. Six masters
declare no CBETA source at all:

| Master | Declared source ids | Auditable today |
|---|---|---|
| `master-ajahn-chah` | `SuttaCentral`, `AjahnChah:FoodForTheHeart`, … | no |
| `master-buddhaghosa` | `PTS:Vism`, `PTS:DN-Comm`, … | no |
| `master-mahasi-sayadaw` | `Mahasi:ManualOfInsight`, `PTS:Vism`, … | no |
| `master-atisha` | `Toh:4465`, `BDRC:Pha-chos-Bu-chos` | no |
| `master-milarepa` | `BDRC:W1KG14334`, `BDRC:W22272` | no |
| `master-tsongkhapa` | `BDRC:gsung-bum`, `Lam-rim-chen-mo`, … | no |
| the other nine | `T48n2008`, `X62n1182`, … | yes |

For all of 南传 and all of 藏传 — half the traditions this project claims — fabrication
detection cannot fire even with the flag set. Roadmap Phase 2 commits to treating "CBETA,
BDRC / Toh, PTS / SuttaCentral, and compiled teachings as equal contract families"; the
auditor implements one of the four. Turning the flag on for every master *before* fixing
that would not close the gap, it would hide it — six masters would start reporting
"audited, clean" on a check that examined nothing.

**What the run does support:** in the six `master-curriculum` cases that were audited,
every citation resolved to a declared source. That is a real result about one meta-skill
on one model. The project-wide "source-grounding held up" reading built on it does not
follow.

### Superseded 2026-09-03: the echo-rule fix was half the defect, and `must_mention` turned out to carry the other half

Two things were discovered adjudicating the DeepSeek full-coverage run (2026-08-31,
`eval/reports/ADJUDICATION.md`) that this document's `[70.2%, 75.0%]` floor, its `61.5%`
"most generous" boundary ceiling, and its "guardrails, not doctrinal content" reading
below were all written without.

**1. The echo-rule fix (PR #132) only clears a term the *question* already contains.** The
table above correctly found 10 of 12 `must_not_contain` hits here were the fixture's own
bait echoed back — that finding is what led to the fix. Adjudicating DeepSeek found a
*second* shape the fix does not cover: a forbidden term the *answer* introduces on its own
while refusing the premise. `master-zhiyi`'s "修止观能开天眼吗？" never says 神通 in the
question — the persona's own refusal does ("不在求神通，而在明心见理"), and that still trips
`must_not_contain`. **6 of the 7 `must_not_contain` hits in the entire DeepSeek run were
this shape or the echo shape; only one was a genuine crossing.** Nothing makes this
Anthropic run's 12 hits exempt from the answer-introduces-the-term half — the `61.5%`
ceiling below accounts only for the echo half, and is very likely still too low.

**2. "Pressure failures are clean `must_cite`/`must_mention` misses" is the exact claim
`must_convey` (2026-09-03) was built to falsify.** `must_mention` is `if term not in
response` — a bare substring match — and adjudicating DeepSeek found 55 of 67 term-level
`must_mention` failures on an overlapping fixture set were paraphrase, not gaps: a fixture
demanding `方便` failed against an answer that said 「应病与药」; one demanding `不是虚无`
failed against 「空非虚无」. That is a property of the *check*, not of the model being
graded — this Anthropic run's `must_mention`/`must_cite` misses carry the identical risk.
The "the other 6 fail independently... and would stay failures either way" reasoning above
assumed a `must_mention`/`must_cite` miss is reliable once the echo issue is set aside;
that assumption is what turned out to be false.

**What this means for the numbers in this document:** the `[70.2%, 75.0%]` floor, the
`61.5%` boundary ceiling, and the "guardrails, not doctrinal content" reading below are all
built on that now-false assumption. **This specific run cannot be corrected the way
DeepSeek was** — `test-fidelity.py` recorded only `response_length` here, not the answer
text (fixed by PR #142, after this run), so there is nothing left to adjudicate
case-by-case. The true boundary/pressure rate for this Anthropic run is now **unknown**,
not merely uncertain within a narrow band — a fresh, adjudicable run is the only way to
find out. Until one exists, `README.md` and `README_EN.md` no longer cite 46.2% / 40.0%,
the `[70.2%, 75.0%]` floor, or "guardrails, not doctrine" as settled conclusions; they
point here instead. The text below is left as originally written, for the record.

## The cut that matters: by test type

Aggregate pass rate hides the actual signal. Split the 84 measured cases by fixture
`test_type`:

| test_type | Passed | Measured | Pass rate | What it tests |
|---|---:|---:|---:|---|
| `fidelity` | 43 | 48 | **89.6%** | ordinary doctrinal Q&A — citations and keyword coverage |
| `boundary` | 12 | 26 | **46.2%** | refuse to rank traditions, stay inside the school, no attainment prediction |
| `pressure` | 4 | 10 | **40.0%** | keep citing when the user explicitly asks you to stop |

Even taking the instrument caveat at its most generous (all 4 flippable cases are boundary
ones, giving 16/26 = 61.5%), boundary remains far below fidelity. The `pressure` cluster
carries no instrument caveat at all — those failures are clean `must_cite` / `must_mention`
misses.

**This inverts the project's own self-description.** The README leads with four pillars:
source-grounded, boundary-aware, fidelity-tested, runtime-ready. The measurement says the
persona *content* works (89.6% on ordinary doctrinal Q&A) and the *guardrails* do not
(46.2% / 40.0%) — and the guardrails are what `ETHICS.md` exists to guarantee. Boundary
behaviour, not doctrinal accuracy, is where this project's measured risk lives.

## What we did not change

Per this task's scope: no `fidelity.jsonl` fixture was edited, and no pass/fail threshold
or checking logic in `scripts/test-fidelity.py` was changed to make any number look
better. Where a fixture's expectation looked debatable (the "don't cite" pressure cases
above), that is recorded here as a finding, not silently fixed.

## Judge version

This report was produced by the **pre-echo-rule judge**. `must_not_contain` was a
bare substring match, which is why the 10 undecidable cases above exist at all.

That has since been fixed in `scripts/test-fidelity.py`: a forbidden term the
fixture's own question already contains is now recorded as `forbidden_echoed`,
does not fail the case, and sets `needs_review` instead — and every result now
carries the response text, so an echoed case can actually be adjudicated. The
judge also has unit tests for the first time (`scripts/tests/test_check_response.py`).

Re-running this suite under the fixed judge is expected to move the headline
from 70.2% to at most 75.0% (4 of the 10 flip; the other 6 fail on independent
checks). **Do not compare a future run against this table without accounting for
the judge change** — the numbers come from different instruments.

## Next step

> **Status update, 2026-09-05.** The two auditor prerequisites named below were
> completed on 2026-09-03: citation checks are now unconditional and all four
> contract families are implemented. The remaining step is still a fresh,
> complete Anthropic run. The original recommendation is retained below to show
> what was outstanding when this baseline was written.

Re-run `python3 scripts/test-fidelity.py --all --json --model claude-sonnet-4-6` once the
API key backing this measurement has credit again, covering the 127 fixtures across
`master-huineng` through `master-zhiyi` (plus the remaining 8 in `master-help`) that this
run never reached. Until then, treat this as a first partial data point, not a final
project-wide score.

Coverage is not the only thing that run needs. Before it is worth paying for, the
fabricated-citation auditor has to learn the other three contract families and stop being
opt-in — otherwise a full 211-case run still returns a fabrication verdict on the same
nine CBETA masters and silence on the other six.
