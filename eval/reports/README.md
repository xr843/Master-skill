# eval/reports

Committed fidelity-test results. This directory exists because `scripts/test-fidelity.py`
previously only printed to stdout — no scored run had ever been persisted to the repo,
so the README's "Fidelity-tested" pillar was an aspiration, not a measurement. Files here
are the actual, dated results of running the 211 fixtures under `prebuilt/*/tests/fidelity.jsonl`
against a real model.

## Files

- `<version>-<shortsha>.json` — machine-readable run output. A `meta` block (measured
  commit, model, timestamps, coverage/pass totals) wraps the `suites` array, which is
  `scripts/test-fidelity.py --all --json`'s own output, captured verbatim and unmodified.
- `BASELINE.md` — the human-readable summary table and failure analysis for the same run.
- `0.12.15-df76fd2-deepseek-metaskills-tools.json` — the four teaching modes only, the first
  run with file tools (`skill_tools` on every suite, `tool_calls` on every result). Its `meta`
  records cost, both output budgets, and why each unmeasured fixture is unmeasured.
- `0.12.15-ab26c9a-deepseek-debate-subagents.json` — master-debate only, the first run with
  the Task tool: each round in a fresh subagent.

## How to regenerate

```bash
export ANTHROPIC_API_KEY="..."   # never commit this
python3 scripts/test-fidelity.py --all --json --model claude-sonnet-4-6 > /tmp/run.json
# then wrap /tmp/run.json with a meta block (commit SHA, model, timestamps, coverage)
# and save as eval/reports/<version>-<shortsha>.json; update BASELINE.md by hand.
```

A plain `python3 scripts/test-fidelity.py --all` (no `--json`) prints the same information
as human-readable progress + summary text instead of a JSON blob — useful for watching a
run live, but not what gets committed here.

## What these numbers do and do NOT mean

Each fixture in `fidelity.jsonl` is a question plus mechanical checks against the model's
raw response text:

- `must_cite` — a literal substring (e.g. a CBETA ID) must appear in the response.
- `must_mention` — a literal keyword/phrase must appear.
- `must_not_contain` / `must_not_contain_first_turn` — a forbidden phrase must NOT appear
  (used for boundary tests, e.g. a master ranking traditions as "better").
- Citation audit — independently of fixture fields, every graded response is submitted to
  `scripts/verify_citations.py`, and every deterministically detectable citation is checked
  against sources the master declares. `must_cite_only_existing_sources` remains valid
  fixture schema for compatibility, but no longer switches the audit on or off.
- `must_convey` — a requirement the substring gauge cannot decide; never passed or failed
  by the grader, always held for adjudication.
- Teaching-mode contracts (graded since 2026-09-23) — `must_have_sections`,
  `must_select_masters` / `must_select_pair`, `must_have_rounds`, `must_cite_per_master` /
  `must_cite_per_round`, `must_recommend_existing_master`, reported in `contract_failures`.
  On `boundary` / `pressure` fixtures they go to `contract_undecided` for a ruling instead.
  A reply that is tool-call markup fails every fixture type.

`validate-fidelity.py` rejects any `must_*` key the grader does not implement.

### Teaching modes run with file tools (since 2026-09-24)

A teaching mode's instructions are to read its sibling skills — compare-masters loads each
master's `meta.json` and `references/`, debate reads `cross_critique`, help scores every
persona's keywords. In a host the model has a file tool. The eval gave it none, and in
`e97ded0` six graded replies were the tool call written out as text.

Teaching-mode suites now get `read_file` and `list_dir` over the installed layout (every
skill directory side by side — `prebuilt/`), never `tests/`, never outside it. Each result
lists what was read in `tool_calls`; each suite says `skill_tools`. **A teaching-mode suite
with `skill_tools` is a different instrument from one without** — every committed run
before 2026-09-24 is without — and the two are not compared. Persona suites are unchanged.

A teaching mode whose SKILL.md dispatches work through the Task tool — master-debate, whose
protocol runs every round in a fresh subagent so neither side sees the other's text — also
gets `Task` (since 2026-09-26). Each call is a new conversation: a generic subagent system
prompt, the orchestrator's prompt as the only message, the file tools, and no `Task` of its
own. Reads made inside a subagent carry `"agent": "subagent-N"` in `tool_calls`; each Task
call is logged with its description, its reply (up to 8,000 characters) and `in_answer` —
the share of the reply's paragraphs found verbatim in the final answer, since the protocol
has the orchestrator append each round rather than rewrite it. Recorded, not graded. The orchestrator and its subagents
share one deadline (1080 s before no new request starts; `per_fixture_ceiling_s` 1440).
`tool_rounds` sums every conversation's rounds; `tool_rounds_max` is the most any one
conversation used, which is what the 12-round cap applies to. A fixture graded after a
subagent failed carries `subagent_failures` and `needs_review`: the orchestrator answered
without that round.

### What the fabrication check covers now

1. **It runs for every graded response.** When a non-empty declared source set is
   available, `check_response()` resolves every detectable citation against it. A missing
   or empty declared set plus a detectable citation produces `audit_unavailable` and
   `needs_review`; it is not reported as audited-and-clean.
2. **It implements all four contract families.** The resolver handles CBETA,
   BDRC / Toh, PTS / SuttaCentral-contract sources, and compiled teachings. Normalisation
   covers forms such as `Toh 4465` versus `Toh:4465`, CBETA short ids, and declared
   compiled-work titles. Corpus-level SuttaCentral references such as `MN 10` cannot be
   authenticated as individual works without an index, so they remain outside the
   numeric audit coverage instead of being guessed valid or fabricated.
3. **Unreadable evidence remains visible.** Citation blocks with no deterministically
   extractable id are recorded in `unparsed_citations`. Together with
   `audit_unavailable`, that separates "checked and clean" from "the instrument could not
   decide."

**Historical correction.** The 2026-08-18 Anthropic baseline predates those fixes. Its
audit was fixture-opt-in (7 of 211 fixtures), its only reached opt-ins belonged to a skill
without usable metadata, and its parser was CBETA-only. It therefore audited **0 of 84**
measured answers; the report's original "zero fabricated citations" line was retracted on
2026-08-31. The stored DeepSeek run can now be re-audited offline at 446/601 (74%) citation
coverage with zero known fabrication findings, but only a new full Anthropic run can fill
the v1.0 release-gate column.

**This is keyword and citation-string coverage, not doctrinal correctness and not
LLM-judged answer quality.** A pass only means the expected strings showed up (or stayed
out); it says nothing about whether the surrounding explanation is accurate, well-reasoned,
or faithful to the master's actual teaching beyond those strings. A response could pass by
including the right keywords in a garbled explanation, and could fail by giving a perfectly
sound answer that happens to phrase things differently than the fixture author expected
(see BASELINE.md for real examples of both). The separate persona-fidelity CI grading is
the closer approximation to quality. Its execution and secret policy are documented in
the top-level README and `CONTRIBUTING.md`; a dry run is structural validation, never a
model-quality score.

## Cost

Full run cost is roughly $5-8 USD for 211 sequential `claude-sonnet-4-6` calls (see
BASELINE.md for what was actually spent on the first, partial run: ~84 completed calls
before the account ran out of API credit, on the order of $2-4).

Teaching-mode fixtures now make several requests each — one per round of file reads, up to
12 rounds per conversation within a 360 s budget (1080 s for master-debate, whose rounds are
subagents — each a conversation of its own) — and each round re-sends the conversation so
far. Expect those 44 fixtures to cost a multiple of what they did; the persona fixtures are
unaffected. A subagent's system prompt is too short to cache, so master-debate's
`input_tokens_saved` is not comparable with runs before 2026-09-26.

## Report size

Since the judge fix, every result carries the full `response` text, not just
`response_length` — that is what makes a failure reviewable after the fact.
Expect roughly 300–500 KB for a full 211-case run. `eval/` is deliberately not
in `package.json`'s `files[]`, so reports never ship in the npm tarball.

## Provider is an axis, not a shortcut

This project ships one `prebuilt/` to five hosts — Claude Code, Cursor, Codex
CLI, OpenCode, Gemini CLI — and the README calls that a unified plugin. Every
fidelity number it has produced so far came from one Anthropic model. A fixture
measures whether the *prompt* induces the right behaviour, and that is a
property of the prompt-and-model pair, not of the prompt alone. The Gemini CLI
path in particular ships `gemini-extension.json` and `GEMINI.md` and has no
evidence behind it at all.

So `--provider` exists to fill in a missing column, not to spend less:

```bash
python3 scripts/test-fidelity.py --all --json                                  # anthropic, default model
python3 scripts/test-fidelity.py --all --json --provider deepseek --model <id> # DeepSeek
python3 scripts/test-fidelity.py --all --json --provider gemini   --model <id> # Gemini
```

Non-Anthropic providers require `--model`. There is deliberately no default: a
model id committed to this repo would rot silently, and a run that cannot name
its model is not a reproducible measurement. Both non-Anthropic providers go
through their OpenAI-compatible endpoints, so one adapter covers them.

**Never pool across models.** Two models are two instruments; averaging a Sonnet
run with a DeepSeek run — or a Sonnet run with an Opus run — produces a figure
that describes neither. `--all` prints a warning and `aggregation_conflicts()`
names the offending pair. Report one row per provider/model, and say which
instrument produced each number.
\n
