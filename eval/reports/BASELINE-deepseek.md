# DeepSeek column — 2026-08-31

The first fidelity run in this repo's history to cover the whole suite, and the
first in which **the fabricated-citation audit executed at all**.

- **Measured commit:** `06b814204082b3e4738185cf3eefa44ed149f9f0` (`06b8142`)
- **Provider / model:** `deepseek` / `deepseek-v4-flash`, `--max-output-tokens 8192`
- **Run window:** 2026-08-31 13:39–15:34 UTC (1h 55m)
- **Cost:** ¥3.89 (~$0.55), measured by account-balance delta, not estimated
- **Raw data:** [`0.11.0-06b8142-deepseek.json`](./0.11.0-06b8142-deepseek.json)

## Read this before the table

**This is a column, not a score, and it cannot advance the v1.0 gate.** That gate
is defined on the Anthropic column (`claude-sonnet-4-6`), and `aggregation_conflicts()`
refuses to pool the two because two models are two instruments. The pass rate below
describes what `deepseek-v4-flash` did with these prompts. Nothing more.

What it *is* good for is the audit. The fabrication check is a mechanical
string-resolution test — does a citation-shaped token resolve to a declared
source — and that is close to model-independent. Before this run it had never
executed on a single case (see the retraction in [`BASELINE.md`](./BASELINE.md)),
so every fabrication number this project had ever published described nothing.

## Three numbers, and the third decides whether the first two mean anything

| | |
|---|---|
| **Pass rate** | 137 / 199 graded = **68.8%** |
| **Fixture coverage** | 199 / 211 = **94.3%** (12 truncated, recorded as unmeasured) |
| **Audit coverage** | 386 / 601 citations = **64.2%** |

A master's "zero fabricated citations" is worth exactly as much as its audit
coverage. Nine skills are at 100%. Four are at or near zero — and for those,
the fabrication result is not a clean bill of health, it is silence.

## The split the v1.0 gate is actually defined on

The aggregate above hides the signal. The gate in
[`docs/v1-framework-roadmap.md`](../../docs/v1-framework-roadmap.md) is set per
`test_type`, and this run was published without that breakdown:

| `test_type` | passed / graded | | v1.0 gate |
|---|---:|---:|---:|
| `fidelity` | 85 / 105 | 81.0% | ≥90% |
| `boundary` | 36 / 64 | **56.2%** | ≥80% |
| `pressure` | 16 / 30 | **53.3%** | ≥70% |

All three miss on this instrument. **Do not act on these three numbers before
reading [`ADJUDICATION.md`](./ADJUDICATION.md)** — 59 of the 62 failures behind
them have since been ruled on (the other three are the open `Toh:3861` decision),
and 43 describe the matcher rather than the persona. Adjudicated, the three rows
read 94.3% / **85.9%** / **83.3%**.

29 cases in this run were flagged `needs_review` and this report did not
mention them. They are decided in `ADJUDICATION.md`; one of them turned a
PASS into a FAIL.

## Results

| Skill | Passed / graded | Fixtures | Truncated | Citations checked | Unparsed | Audit coverage | Contract violations |
|---|---:|---:|---:|---:|---:|---:|---:|
| `compare-masters` | 13/13 | 18 | 5 | 0 | 47 | **0%** | 0 |
| `master-ajahn-chah` | 6/12 | 13 | 1 | 0 | 48 | **0%** | 0 |
| `master-atisha` | 8/12 | 12 |  | 25 | 7 | **78%** | 0 |
| `master-buddhaghosa` | 10/12 | 13 | 1 | 44 | 16 | **73%** | 0 |
| `master-curriculum` | 8/8 | 8 |  | 0 | 6 | **0%** | 0 |
| `master-debate` | 8/8 | 8 |  | 0 | 0 | **n/a** | 0 |
| `master-fazang` | 5/9 | 10 | 1 | 32 | 0 | **100%** | 0 |
| `master-help` | 8/10 | 10 |  | 0 | 0 | **n/a** | 0 |
| `master-huineng` | 6/10 | 12 | 2 | 24 | 0 | **100%** | 0 |
| `master-kumarajiva` | 6/10 | 10 |  | 26 | 0 | **100%** | 0 |
| `master-mahasi-sayadaw` | 8/13 | 13 |  | 12 | 40 | **23%** | 0 |
| `master-milarepa` | 8/12 | 12 |  | 42 | 0 | **100%** | 0 |
| `master-nagarjuna` | 6/10 | 10 |  | 33 | 0 | **100%** | 0 |
| `master-ouyi` | 6/8 | 10 | 2 | 20 | 0 | **100%** | 0 |
| `master-tsongkhapa` | 5/12 | 12 |  | 3 | 50 | **6%** | **3** |
| `master-xuanzang` | 7/10 | 10 |  | 32 | 1 | **97%** | 0 |
| `master-xuyun` | 4/10 | 10 |  | 24 | 0 | **100%** | 0 |
| `master-yinguang` | 8/10 | 10 |  | 30 | 0 | **100%** | 0 |
| `master-zhiyi` | 7/10 | 10 |  | 39 | 0 | **100%** | 0 |
| **Total** | **137/199** | **211** | **12** | **386** | **215** | **64.2%** | **3** |

## The three contract violations, and why "fabricated" is the wrong word for them

`master-tsongkhapa` is the only skill that produced any, and all three are the
same identifier — `Toh:3861` — cited in three separate answers.

The model did not invent it. `Toh 3861` is the correct Tohoku number for
Candrakīrti's *Madhyamakāvatāra* (《入中论》), and it is written into the persona's
own instructions:

```
prebuilt/master-tsongkhapa/SKILL.md:125
   - 印度大乘论典所引：`【月称《入中论》§第六章】（Toh 3861）`
prebuilt/master-tsongkhapa/sources/INDEX.md:15
   - 印度论典所引：`【月称《入中论》§第六章】（Toh 3861）`
```

`meta.json` declares five sources, none of them `Toh:3861`. So the skill instructs
the persona to emit a citation that the citation contract forbids, and the persona
complies. Every use of that instruction is a violation.

**This is a defect in the shipped persona, not a model failure**, and it is exactly
the class the source-grounded pillar exists to catch. It is left for a maintainer to
resolve rather than silently patched, because there are two defensible fixes and
they are not equivalent:

1. Declare `Toh:3861` in `meta.json.sources[]` — asserting that Tsongkhapa's persona
   may cite Candrakīrti's root text directly.
2. Remove the example from `SKILL.md` / `INDEX.md` — asserting that it may only cite
   the works Tsongkhapa himself wrote.

That is a doctrinal and bibliographic call, not a code change.

## Where the audit is blind, stated as numbers instead of caveats

| Skill | Coverage | Why |
|---|---|---|
| `master-ajahn-chah` | 0% (0 / 48) | Declares `SuttaCentral` (corpus-level, unauditable by contract) and `AjahnChah:FoodForTheHeart` (compiled teachings, `Author:Work`). The compiled-teaching family is **not implemented** in `verify_citations.py`. |
| `master-tsongkhapa` | 6% (3 / 53) | Declares bare Wylie titles (`Lam-rim-chen-mo`) that free text cannot be distinguished from an invented title. Documented as out of reach. |
| `master-mahasi-sayadaw` | 23% (12 / 52) | Same compiled-teaching family (`Mahasi:ManualOfInsight`). |
| `compare-masters`, `master-curriculum` | 0% | No `meta.json`, so no declared set to audit against; recorded as `audit_unavailable`. |
| `master-help`, `master-debate` | n/a | Emit no citations at all. |
| the other 9 masters | 97–100% | CBETA, `Toh:`, `BDRC:` and `PTS:` all resolve. |

The four families the roadmap's Phase 2 promises to treat as equal are still not
equal: CBETA, Toh and BDRC and PTS work; **compiled teachings do not**. That is now
a number (0% and 23%) rather than a sentence in a known-gaps list.

## Truncation

12 of 211 fixtures hit the 8192-token output budget and were recorded as
`truncated` — unmeasured, never scored as failures. They cluster where answers
are longest: `compare-masters` 5 of 18, `master-huineng` 2, `master-ouyi` 2.
Before PR #142 these would have been graded as `missing_cites` / `must_mention`
failures that never happened.

## What this run does not tell you

- Nothing about the v1.0 gate. That needs the Anthropic column.
- Nothing about doctrinal quality. These are keyword and citation-string checks;
  see the caveat in [`README.md`](./README.md).
- Nothing about `master-ajahn-chah`'s or `master-tsongkhapa`'s source-grounding.
  0% and 6% audit coverage means the question was not asked, let alone answered.

## Next

0. Done, 2026-09-03: every failure and every `needs_review` in this run is
   adjudicated in [`ADJUDICATION.md`](./ADJUDICATION.md).
1. Resolve the `Toh:3861` contract inconsistency (a maintainer decision, above).
2. Implement the compiled-teaching family in `verify_citations.py` — it is the
   last of the four, and it is what holds Ajahn Chah at 0% and Mahasi at 23%.
3. Only then is an Anthropic run worth its $5–8: it would land on an instrument
   that can read three quarters of what it is shown rather than two thirds.
