# Adjudicating the first full-coverage run — 2026-09-03

The 2026-08-31 sweep failed **62 of 199** graded cases. This is the ruling on
every one of those failures, plus the 29 cases the run flagged `needs_review`
and never had decided.

- **Run adjudicated:** [`0.11.0-06b8142-deepseek.json`](./0.11.0-06b8142-deepseek.json)
  (`deepseek-v4-flash`, commit `06b8142`)
- **Verdicts:** [`adjudication-06b8142-deepseek.json`](./adjudication-06b8142-deepseek.json) — 74 cases
- **Re-check them:** `python3 scripts/verify-adjudication.py` (in `npm test` and CI)

Every verdict carries a quote from the answer it judges, and the gate proves
each quote is still in the stored response, that each term really failed in the
run, and that the headline numbers below are recomputed from the verdicts rather
than typed in. It also refuses an adjudication that does not declare what it
left undecided: **59 of the 62 failures are ruled on here**, and the three that
are not — `master-tsongkhapa` #2, #3 and #9, all `Toh:3861` — are the open
contract decision already held in `KNOWN_UNDECLARED`, which is a maintainer's
call and not a reader's. A verdict file that cannot be re-derived from the run
it judges would be one more green report that examined nothing.

## The headline

| | as graded | adjudicated | v1.0 gate |
|---|---:|---:|---:|
| `fidelity` | 85/105 = 81.0% | **99/105 = 94.3%** | ≥90% |
| `boundary` | 36/64 = 56.2% | **55/64 = 85.9%** | ≥80% |
| `pressure` | 16/30 = 53.3% | **25/30 = 83.3%** | ≥70% |
| total | 137/199 = 68.8% | **179/199 = 89.9%** | — |

43 failures were overturned; **one case that graded PASS was turned into a
FAIL**. Adjudication that can only move a number upward is advocacy, not
judgement, so the recount is built to move it both ways.

**None of this advances the v1.0 gate.** That gate is defined on the Anthropic
column, and these are one reader's rulings on one model's answers. What the
numbers do establish is that the gap between 56.2% and 85.9% on `boundary` is
mostly the ruler, and that deciding what to fix from the raw column would have
sent the next round of work in the wrong direction.

## Why 74% of the failures were about spelling

46 of the 62 failures had `must_mention` as their only failing check, and
`must_mention` is `if mention not in response` — a bare substring match against
2-to-5-character Chinese terms. 55 of the 67 individual term verdicts came back
as artifacts of that matcher:

| defect | count | example |
|---|---:|---|
| synonym / literary-vs-vernacular rewrite | 50 | `master-nagarjuna` wrote **「空非虚无」** for a fixture demanding `不是虚无` |
| traditional vs simplified characters | 2 | `master-ouyi` answered entirely in traditional — **「須先明信願」** ×6 against `信愿` |
| enumeration punctuation inside the term | 1 | `master-mahasi-sayadaw` wrote **「"升、降"是主门」** against `升降` |
| reversed character order | 1 | `master-xuanzang` wrote **「破此"我执"之结」** against `执我` |
| formal title vs common alias | 1 | `master-zhiyi` cited **《修習止觀坐禪法要》** with the correct `T1915` against `小止观` |

Three of the run's 211 answers are written in traditional characters while every
fixture keyword is simplified. Two of those three failed on exactly that.

The deeper problem is that `must_mention` holds two kinds of requirement that
cannot both be matched this way: **terms of art** the persona genuinely must
name (`阿赖耶`, `十念法`, `khaṇika-samādhi`, `/compare-masters`), and
**propositions** written as short strings (`不是虚无`, `各有侧重`, `未做精确分判`,
`不抓取`, `完整法义`, `长远心`). The first kind is matchable. The second never was.

## The boundary check is worse, and it is the pillar

`must_not_contain` is the only check that measures an actual boundary violation.
It fired **7 times in the whole run**. Reading all seven:

| case | term | ruling |
|---|---|---|
| `master-mahasi-sayadaw` #9 | 末那, 八识 | **real** — a whole section explains the marking method through Yogācāra's three natures |
| `master-milarepa` #6 | 胜于 | false — 「何来一宗胜于他宗？」 is a rhetorical denial, and the second hit matched across a word boundary inside 「殊胜于何」 |
| `master-milarepa` #11 | 某日 | false — 「则相见不必待某日」 |
| `master-nagarjuna` #5 | 胜于 | false — 「然若执『中观』定胜于『唯识』，此执却正是戏论」 |
| `master-tsongkhapa` #10 | 预言 | false — 「正法不以预言立教」 |
| `master-zhiyi` #5 | 不如 | false — 「说得千般高，不如一念回光」, an idiom deflating the ranking |
| `master-zhiyi` #6 | 神通 | false — 「不在求神通」,「若求神通而舍三观，即失止观本旨」 |

**Six of seven are the persona refusing the thing in so many words.** PR #132
exempted a forbidden term the *question* already contained; it never covered a
term the *answer* introduces in order to deny it. Same defect, other half.

So `check_response` now records `forbidden_context` — the text around every
forbidden hit, found and echoed alike. It changes no verdict. It means the next
run's boundary failures can be ruled on from the report instead of by re-reading
199 answers.

## The echo rule's own false green

`forbidden_echoed` does not fail a case; it sets `needs_review`. Of the 29
flagged cases, 21 carry `forbidden_echoed`, 4 carry `boundary_echoed` (a
first-turn form of address) and 5 carry `audit_unavailable`. The four
first-turn ones read like this:

- `master-huineng` #7 answered **「莫呼老僧为善信」** — rejects the honorific.
- `master-ouyi` #7 answered **「善知识之称不敢当」** — rejects it.
- `master-yinguang` #7 answered **「老衲乃出家之僧，非居士也」** — rejects it.
- `master-kumarajiva` #7 answered **「善男子所问，正是大乘佛法的心髓」** — **adopts it.**

The rule cleared all four identically, and the case passed. That is the one
verdict here that turns a PASS into a FAIL. The mechanism was not broken — it
correctly refused to decide and asked for a human. Nobody was asked:
**`BASELINE-deepseek.md` does not contain the string `needs_review`**, so all 29
undecided cases were published as part of a 68.8% and cited as a result. That is
how a case that adopts a forbidden form of address ships as a pass.

## Five `pressure` failures ask a contract question nobody has answered

Six cases failed on `must_cite` alone, all of them `pressure` — the type where
the user asks the persona to stop citing. One is an instrument artifact:
`master-buddhaghosa` wrote 「今依拙著《清净道论》慧地品」 against a fixture
demanding the Pali title `Visuddhimagga`. Same work, other language.

The other five are the same shape as each other, and none of them is a persona
dropping its grounding:

| case | told to | did |
|---|---|---|
| `master-kumarajiva` #8 | 「别引中论了」 | 「好，那我就不搬《中论》了」 — then cited 《金刚经》 `T08n0235` with a live link |
| `master-fazang` #8 | 「不用引经据典了」 | cited 《华严经探玄记》 `T35n1733` |
| `master-fazang` #9 | 「别引那些古文」 | 「但为不违圣教，我仍以简注标明出处」 — cited three declared sources |
| `master-tsongkhapa` #11 | 「别引那些藏文论典」 | 「教法必有所本」 — cited 《菩提道次第广论》 |
| `master-yinguang` #9 | (challenged 念佛 as superstition) | cited 《佛說阿彌陀經》 and 《佛說無量壽經》 |

Every one held the citation contract and cited a **declared** source. Each failed
because the fixture names a *particular* text. So `pressure` as written measures
"cites the text we picked", while the B1 rule requires "cites a declared source",
and in `master-kumarajiva` #8 the text the fixture demands is exactly the one the
user asked the persona to drop — the fixture cannot be satisfied without either
ignoring the user or failing the check.

These are recorded as `open_question`: evidenced, but **deciding nothing**. They
do not move a number here. Which of the two readings `pressure` means is a
maintainer's call, and the two are not equivalent — one of them makes a persona
that changes citation *under pressure* a failure, the other does not.

## The failures that stand

Seventeen cases still fail after adjudication. Ten are persona or content
defects, five are the contract question above, and two are real boundary
crossings.

| case | what is actually wrong |
|---|---|
| `master-help` #2 | answers the doctrinal question itself; emits no `/` command at all |
| `master-help` #8 | writes 「贫僧玄奘」 and delivers a full Yogācāra lecture — exactly what a routing skill must not do |
| `master-mahasi-sayadaw` #9 | **real crossing** — a whole section explains the marking method through Yogācāra's three natures (末那, 八识) |
| `master-kumarajiva` #7 | **adopts** 善男子 as a form of address; the PASS turned FAIL |
| `master-ajahn-chah` #1 | never gives the Pali `sati`; `Satipaṭṭhāna` appears only as a sutta title |
| `master-buddhaghosa` #7 | correctly refuses to rank, but never asserts both traditions carry the complete Dharma |
| `master-huineng` #5 | no 方便 / 对机 framing anywhere |
| `master-mahasi-sayadaw` #5 | no 持续 / 相续 / 不间断 in any form |
| `master-milarepa` #6 | no 根机 / 利钝 / 根器 / 对机 in any form |
| `master-ouyi` #6 | never addresses the 因缘 the question turns on |
| `master-tsongkhapa` #7 | names 宁玛 and 格鲁 only; 「藏传四派」 does not hold |
| `master-yinguang` #1 | gives 净念相继 without 都摄六根 — half of 印光's signature pair; 六根 is absent entirely |
| `master-fazang` #8, #9 · `master-kumarajiva` #8 · `master-tsongkhapa` #11 · `master-yinguang` #9 | the `pressure` contract question above |

Both `master-help` failures are the same defect: a routing skill that answers
instead of routing. That is the clearest content finding in the run, and neither
would have been visible from the pass rate alone.

One verdict is against the fixture rather than either side: `master-xuanzang` #6
is required to say the word `经论` while the answer cites five of them. That
requirement measures vocabulary, not behaviour.

## What this does not license

- **Do not raise a score by editing fixtures.** Nothing here has been changed in
  `prebuilt/`. The rulings say which requirements are unmatchable as written;
  turning that into a fixture change is a separate decision under
  `CONTRIBUTING.md` §③, and it needs the `must_mention` schema to distinguish a
  term of art from a proposition first.
- **Do not pool these numbers with the Anthropic baseline.** Different model,
  different instrument.
- **Do not read the adjudicated column as a measurement.** It is what this run
  would have scored if the matcher measured meaning instead of spelling. The
  measurement still has to be made by an instrument, not by a reader.

## Next

1. Give `must_mention` a way to express "any of these forms" and mark which
   entries are terms of art. Until then, every `boundary` and `pressure` number
   this repo publishes is part vocabulary test.
2. Decide what `pressure` means when the user names the text to drop: cite that
   text anyway, or cite any declared source. Five failures hang on it.
3. Fix the two `master-help` failures — a routing skill that lectures is a
   content defect, not an instrument one.
4. Implement the compiled-teaching contract family in `verify_citations.py`;
   `master-ajahn-chah` still audits at 0% and `master-mahasi-sayadaw` at 23%.
5. Then the Anthropic column is worth its $5–8.
