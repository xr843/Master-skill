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
- `must_cite_only_existing_sources` — every citation-shaped string in the response must
  resolve to a source the master actually declares (checked via `scripts/verify_citations.py`);
  anything else counts as a fabricated citation.

**This is keyword and citation-string coverage, not doctrinal correctness and not
LLM-judged answer quality.** A pass only means the expected strings showed up (or stayed
out); it says nothing about whether the surrounding explanation is accurate, well-reasoned,
or faithful to the master's actual teaching beyond those strings. A response could pass by
including the right keywords in a garbled explanation, and could fail by giving a perfectly
sound answer that happens to phrase things differently than the fixture author expected
(see BASELINE.md for real examples of both). The separate `persona-fidelity.yml` CI job
(LLM-rubric grading) is the closer approximation to quality, and it is advisory-only
(`|| true`) with no `ANTHROPIC_API_KEY` configured in repo secrets — it has never actually
run for real either.

## Cost

Full run cost is roughly $5-8 USD for 211 sequential `claude-sonnet-4-6` calls (see
BASELINE.md for what was actually spent on the first, partial run: ~84 completed calls
before the account ran out of API credit, on the order of $2-4).

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