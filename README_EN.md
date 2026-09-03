<h1 align="center">Master-skill</h1>

<p align="center">
  <em>"All conditioned phenomena<br>
  Are like a dream, an illusion, a bubble, a shadow,<br>
  Like dew, or a flash of lightning;<br>
  Thus should they be contemplated."</em><br>
  <sub>— Diamond Sūtra (Vajracchedikā Prajñāpāramitā Sūtra)</sub>
</p>

<p align="center">
  <a href="https://www.npmjs.com/package/master-skill"><img src="https://img.shields.io/npm/v/master-skill.svg?label=npm&color=cb3837" alt="npm version"></a>
  <a href="https://www.npmjs.com/package/master-skill"><img src="https://img.shields.io/npm/dm/master-skill.svg?color=cb3837" alt="npm downloads"></a>
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/Python-3.9+-green.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/Claude%20Code-Skill-purple.svg" alt="Claude Code Skill">
  <img src="https://img.shields.io/badge/AgentSkills-Standard-orange.svg" alt="AgentSkills Standard">
</p>

<p align="center">
  Opening the 100-fascicle Yogācārabhūmi-śāstra — not knowing where to begin?<br>
  Want to study Chan, but unsure which patriarch to approach?<br>
  Modern translations feel one layer removed, but reading classical Chinese is daunting?<br>
  Need authoritative citations of patriarchs' teachings for scholarly work?
</p>

<p align="center">
  <strong>A FoJin-powered Buddhist AI persona framework</strong><br>
  Source-grounded · Boundary-aware · Fidelity-tested · Runtime-ready · 15 masters across 印度 / 汉传 / 藏传 / 南传
</p>

<p align="center">
  <sub>CBETA / BDRC / SuttaCentral / PTS Vism citations · AgentSkills Standard</sub>
</p>

<p align="center">
  <a href="#try-it-now-browser-first">Browser</a> ·
  <a href="#seriousness-statement">Statement</a> ·
  <a href="#features">Features</a> ·
  <a href="#developer-installation">Install</a> ·
  <a href="#pre-built-masters">Masters</a> ·
  <a href="#relationship-to-fojin">FoJin</a> ·
  <a href="README.md">中文</a>
</p>

---

## Try It Now (Browser-First)

> **Most users don't need to install anything.** Buddhist students, researchers, and curious readers can use every master directly in a web browser.

### 👉 [Open fojin.app/chat](https://fojin.app/chat)

On the AI Q&A page, open the **"法师模式"** (Master Mode) dropdown in the bottom-left and pick one of the 15 pre-built masters across four traditions to start chatting.

- No install, no signup
- Three teaching modes available: `/compare-masters` (side-by-side comparison), `/master-debate` (4-round dialectic), `/master-curriculum` (time-sequenced study path) — all cross-tradition
- Live citation retrieval backed by FoJin's 503 sources and 678K+ semantic embeddings
- Every answer carries an authoritative source ID (CBETA for 汉传, BDRC for 藏传, SuttaCentral for 南传)

**Not sure which master to ask?** Start here:

| Your situation | Suggested master |
|---|---|
| "My mind is scattered, I can't sit still" | `/master-xuyun` `/master-zhiyi` `/master-ajahn-chah` (huatou / śamatha-vipaśyanā / mindfulness) |
| "I can't follow the logic of the sutras" | `/master-xuanzang` (Yogācāra precision) |
| "I've studied for years but feel stuck" | `/master-yinguang` (plain, sincere nianfo) |
| "I want to understand emptiness" | `/master-nagarjuna` `/master-kumarajiva` `/master-huineng` `/master-milarepa` `/master-tsongkhapa` (Madhyamaka source / Madhyamaka translator / direct pointing / Mahāmudrā / prasaṅgika analysis) |
| "I want a systematic view of Huayan / Tiantai" | `/master-fazang` `/master-zhiyi` (classification and metaphysics) |
| "I'm torn between Chan and Pure Land" | `/master-ouyi` (cross-tradition synthesis) |
| "I'm curious about ascetic practice / retreat" | `/master-milarepa` (snow-mountain retreat · Kagyu paradigm) |
| "I want the simplest meditation instructions" | `/master-ajahn-chah` (Thai Forest · ānāpānasati) |
| "I want a complete graduated path of practice" | `/master-atisha` `/master-tsongkhapa` (Kadam three scopes → Gelug Lamrim) |
| "I want the systematic Theravāda commentarial framework" | `/master-buddhaghosa` (*Visuddhimagga* — sīla / samādhi / paññā + 7 purifications · 16 insight knowledges) |
| "I want intensive vipassanā with the noting method" | `/master-mahasi-sayadaw` (Burmese · noting · rising-falling) |
| "I want a cross-tradition perspective" | `/compare-masters` (auto-pairs 汉/藏/南 voices) · `/master-debate` (adversarial dialectic) · `/master-curriculum` (study path by tradition) |

> Developers and Claude Code / Cursor users should skip to [Developer Installation](#developer-installation) to use the masters as terminal AgentSkills.

---

## What It Looks Like

A real `/master-huineng` (Master Huineng, the Sixth Patriarch of Chan) exchange. Note that **every doctrinal claim carries a CBETA citation**, and the voice matches the master himself — direct, plain-spoken, fond of metaphor:

```text
You: I want to practice Chan, but I can't sit still and my mind is too busy.

Master Huineng:
You say you "can't sit still" — you have mistaken the posture for Chan.
You say your mind is "too busy" — you have made your thoughts the enemy.
Neither of these is Chan.

What is "sitting in meditation"? When, amid all conditions good and bad,
no thought arises in the mind — that is "sitting". When you inwardly see
the self-nature unmoved — that is "Chan". Sitting is not a matter of the
legs; it is the mind not grasping at objects.
  【Platform Sutra · Sitting Meditation】→ https://fojin.app/texts/58

Do not fear arising thoughts. "Amid all objects the mind is unstained —
this is called no-thought." It does not mean having no thoughts; it means
a thought arises yet you do not chase it, do not let it stick. Like a
cloud crossing the sky — the sky has never moved.
  【Platform Sutra · Concentration and Wisdom】→ https://fojin.app/texts/58

For further study, consult the original texts at FoJin (fojin.app).
```

> ⚠️ The above is **AI-synthesized content**, generated from the *Platform Sutra*; it does not represent Master Huineng's actual spoken teachings. Masters currently answer in Classical/Modern Chinese — the English here is an illustrative translation. Try the multi-master `/compare-masters` mode directly at [fojin.app/chat](https://fojin.app/chat).

---

> **v0.6 Update (2026-05-02)**: Slash command namespace cleanup — all 14 master slash commands prefixed with `master-`. `/master-zhiyi`, `/master-huineng`, etc.
> - **Why**: Claude Code users typically have 50+ skills installed; bare-word slash commands like `/atisha` get scattered. Prefixing clusters all 14 masters under `/m<tab>` for fast discovery.
> - **Unaffected**: `compare-masters` and `create-master` meta-skills keep their existing names (avoiding `/master-compare-masters` doublespeak). `fojin.app/chat` web-side dropdown is decoupled — its master IDs stay bare (`atisha`, `huineng`, etc.); backend `master_profiles.py` unchanged.
> - **NPX installer**: both `npx master-skill install zhiyi` (short) and `install master-zhiyi` (full) work; install destination is always `~/.claude/skills/master-<slug>/`.
> - See [CHANGELOG.md §0.6.0](CHANGELOG.md#060--2026-05-02) for full details.
>
> **v0.5 Update (2026-05-02)**: Second cross-tradition expansion — Tibetan and Theravāda each grow from 1 master to 3. Total **14 masters**.
> - 藏传 added: Atiśa (Kadam founder · Toh 4465 *Bodhipathapradīpa* · three scopes) + Tsongkhapa (Gelug founder · three principal aspects · Madhyamaka prasaṅgika)
> - 南传 added: Buddhaghosa (commentarial summit · *Visuddhimagga*) + Mahasi Sayadaw (Burmese vipassanā · noting method · ETHICS Tier B special case)
> - HARD-GATE strengthened: Mahasi Sayadaw specifically gets `NO_ATTAINMENT_JUDGMENT` (AI must not confirm any individual's stage of insight)
> - ETHICS Tier A grows to 11 masters; Tier B special-case grows to include Mahasi Sayadaw (parallel to Ajahn Chah)
>
> **v0.4 Update (2026-05-02)**: First cross-tradition expansion — added Tibetan **Milarepa** (Kagyu / Mahāmudrā) and Theravāda **Ajahn Chah** (Thai Forest Tradition). Citation system extended to support BDRC and SuttaCentral. HARD-GATE adds `no_esoteric_instruction` and `no_fabricated_quotes`.
>
> **v0.3**: Full architecture rebuild — provenance frontmatter, offline source passages (`sources/`), automated fidelity tests (`fidelity.jsonl`), NPX installer, two-stage independent review, HARD-GATE rules, multi-platform plugin support across Claude Code / Cursor / Codex / OpenCode / Gemini CLI, session-start hook auto-injecting the master list.

---

Master-skill is a [FoJin](https://fojin.app)-powered Buddhist AI persona framework: grounded in primary sources, constrained by ethical boundaries, checked by fidelity tests, and packaged as runtime-ready AgentSkills for Claude Code, Cursor, Codex CLI, OpenCode, and Gemini CLI.

---

## Seriousness Statement

This project is built out of respect for Buddhist traditions. All content is generated faithfully from historical documents. It makes no doctrinal judgments and claims no sectarian authority. Generated content is intended for study and reference only. For formal practice guidance, please seek out a qualified master and rely on genuine, living instruction.

---

## Features

- **15 pre-built masters across four traditions**: 1 印度 (Madhyamaka · Nāgārjuna) + 8 汉传 (Yogācāra, Madhyamaka, Chan, Tiantai, Huayan, Pure Land, cross-tradition) + 3 藏传 (Kadam · Atiśa; Gelug · Tsongkhapa; Kagyu · Milarepa) + 3 南传 (Theravāda commentator · Buddhaghosa; Burmese vipassanā · Mahasi Sayadaw; Thai Forest · Ajahn Chah) — plus a `compare-masters` multi-master comparison meta-skill, ready to use out of the box
- **Provenance enforcement**: Every master ships with declared source IDs (CBETA / BDRC / Toh / SuttaCentral / PTS / compliant compiled teachings); live retrieval adds a FoJin locator only when a real `text_id` is returned, and every doctrinal claim must carry a source citation
- **Offline source passages**: `sources/` captures key passages from each master's core canon, so citations still work when FoJin is unreachable
- **Progressive disclosure**: SKILL.md is a decision tree + quick reference; `references/` and `sources/` are loaded on demand to keep context lean
- **HARD-GATE discipline**: Both `/create-master` and every prebuilt master require doctrinal claims, practice guidance, and text interpretation to cite that persona's declared sources (CBETA / BDRC / Toh / SuttaCentral / PTS / compliant compiled teachings); fabricated source IDs and fictional personas are forbidden
- **Two-stage independent review**: The generation pipeline forces a "doctrinal accuracy → voice consistency" review before write; FAIL triggers up to 2 rounds of automatic repair
- **Automated fidelity tests**: Each master's `tests/fidelity.jsonl` holds 10+ Q&A samples (the `compare-masters` meta-skill holds 18) validating citations and keyword coverage; CI runs a dry-run on every push, and a graded run needs `ANTHROPIC_API_KEY` as a manual local/pre-release step — the first committed [baseline](#fidelity-baseline-first-real-run) landed 2026-08-18: 59/84 measured cases passed (70%), covering 40% of all 211 fixtures (see [eval/reports/](eval/reports/))
- **Unified multi-platform plugin**: Claude Code, Cursor, Codex CLI, OpenCode, and Gemini CLI share one `prebuilt/` tree, with a session-start hook injecting the master list on every platform
- **NPX one-shot install**: `npx master-skill install master-zhiyi` drops skills straight into Claude Code
- **Offline toolchain**: `scripts/cite.py` (CBETA lookup), `scripts/query.py` (offline semantic search), `scripts/validate.py` (frontmatter linter)
- **FoJin data bridge**: Connected to [fojin.app](https://fojin.app) with 503 data sources, 10K+ texts, 678K+ semantic embeddings, and a 31K-entity knowledge graph
- **AgentSkills standard**: Compliant with [Anthropic Agent Skills](https://github.com/anthropics/skills) — progressive disclosure, decision trees, black-box script pattern

## Framework Positioning

Master-skill is not a prompt pack. It is a verifiable Buddhist AI persona framework:

| Dimension | Implementation |
|---|---|
| Source-grounded | `sources[]`, offline excerpts, FoJin live fallback, and citation self-audits per master |
| Boundary-aware | `ETHICS.md`, per-master Layer 0 HARD-GATE rules, copyright tiers, and boundary violation reporting |
| Fidelity-tested | `tests/fidelity.jsonl`, persona-fidelity schema, promptfoo RAW / SPE / CUS evals, [real measured baseline below](#fidelity-baseline-first-real-run) |
| Runtime-ready | `prebuilt/master-*` AgentSkills, npm CLI, multi-platform hooks, and a FoJin runtime contract |

The v1.0 track prioritizes framework stability over adding more masters. See [docs/v1-framework-roadmap.md](docs/v1-framework-roadmap.md) and [docs/fojin-runtime-contract.md](docs/fojin-runtime-contract.md).

### Fidelity baseline (first real run)

The 211 fixtures under `tests/fidelity.jsonl` used to be just fixtures — `scripts/test-fidelity.py` only printed to stdout, and no scored run had ever been committed. On 2026-08-18 we ran and committed the first real baseline (commit [`c697d5d`](https://github.com/xr843/Master-skill/commit/c697d5d3be78ce6738cf1f969ca057c7e4c16bb5), model `claude-sonnet-4-6`):

| | Value |
|---|---|
| Passed / measured | **59 / 84 (70%)** |
| Coverage of the full suite | 84 / 211 (40%) — the run stopped partway when the API account's credit balance ran out (HTTP 400), not from rate limiting or a code bug; the remaining 127 cases were never evaluated and are **not** counted as failures |
| Where real failures cluster | Missing expected keyword 14/25; forbidden phrase present 12/25; missing citation 5/25; fabricated citations 0 — **but that audit ran on none of the 84 cases**, see below |
| By test type | ordinary doctrine 43/48 = **89.6%**; boundary 12/26 = **46.2%**; citation-under-pressure 4/10 = **40.0%** (⚠️ see below — "the weakness is guardrails" is no longer a safe conclusion) |
| ⚠️ Instrument warning (scope widened 2026-09-03) | At the time, 10 of 12 forbidden-phrase failures were ruled question-echoed bait (the check is a plain substring match, so a correct refusal trips it as hard as a real violation), giving a **[70.2%, 75.0%]** "floor" — but that estimate assumed a non-echoed `must_mention`/`must_cite` miss is a real failure. Adjudicating a later run proved **that assumption false**: the same judge code misjudged 55/67 `must_mention` terms as missing when the answer had simply paraphrased them, and the boundary check still has an unfixed second failure mode — a forbidden term the *answer itself* introduces while refusing (never in the question). **Neither this row's numbers nor "the weakness is guardrails, not doctrine" can be treated as settled** — see the 2026-09-03 correction in the baseline report |
| ⚠️ What the fabrication audit actually covered | The audit is **opt-in per fixture**: 7 of 211 fixtures set `must_cite_only_existing_sources` (six in `master-curriculum`, one in `master-huineng`), and those six belong to a skill with no `meta.json`, so the guard's `declared_ids is not None` clause short-circuited and they did not run either. **The audit decided nothing at all — 0 of 84 — and no master persona has ever been checked for a fabricated citation.** Its id pattern also recognises CBETA ids only, so the six masters declaring `PTS:` / `Toh:` / `BDRC:` / `SuttaCentral` sources (all of Theravāda and all of Tibetan) cannot be audited even with the flag set. Corrected 2026-08-31; this row previously read "zero fabricated citations" |

This measures **keyword/citation-string coverage, not doctrinal correctness or LLM-judged answer quality**. Full table, failing cases, and methodology notes: **[eval/reports/BASELINE.md](eval/reports/BASELINE.md)**.

---

## Developer Installation

> 👤 **Just want to try it?** Use [fojin.app/chat](https://fojin.app/chat) — no install needed.
> 🛠️ **This section is for** Claude Code / Cursor / Codex CLI / OpenCode / Gemini CLI users.

```bash
npx master-skill install --all          # all 20 skills at once
npx master-skill install master-huineng # or just one
npx master-skill list                   # see everything installable
npx master-skill recommend "how do I actually practice nianfo"   # not sure who to ask?
```

Once installed, invoke `/master-huineng`, `/compare-masters`, etc. directly in chat.

> Per-platform setup (Claude Code plugin / Cursor / OpenCode / Codex CLI / Gemini CLI),
> global install, teaching-mode usage, and `/create-master`
> → **[docs/install.en.md](docs/install.en.md)**

## Desktop Manager

A native desktop console (pure Rust, egui, single binary, no Electron) that unifies management of installation status, fidelity evaluation coverage, run tracing, and the quality gate across all 19 master skills:

![Master-skill Desktop Manager](https://raw.githubusercontent.com/xr843/Master-skill/main/docs/assets/desktop-manager.png)

**Download**: [Releases](https://github.com/xr843/Master-skill/releases) provides pre-built binaries for Linux / Windows / macOS — download and run directly (execute from the repository root; requires a local clone of this repo). On Linux/macOS you'll need to `chmod +x` the downloaded binary first; on macOS it's unsigned, so the first run needs right-click → Open, or `xattr -d com.apple.quarantine <file>` to clear the quarantine flag.

**Build from source**:

```bash
cd desktop && cargo build --release
./target/release/master-skill-desktop            # GUI
./target/release/master-skill-desktop --baseline # headless fidelity dry-run baseline
```

---

## Pre-built Masters

Fifteen masters across four traditions. The command *is* the skill name — invoke it directly once installed.

| Command | Master | Tradition · School | Dates |
|---|---|---|---|
| `/master-nagarjuna` | Nāgārjuna | Indian · Madhyamaka | c. 150-250 |
| `/master-kumarajiva` | Kumārajīva | Chinese · Sanlun / Madhyamaka | 344-413 |
| `/master-zhiyi` | Zhiyi | Chinese · Tiantai | 538-597 |
| `/master-xuanzang` | Xuanzang | Chinese · Yogācāra | 602-664 |
| `/master-huineng` | Huineng | Chinese · Chan (Sixth Patriarch) | 638-713 |
| `/master-fazang` | Fazang | Chinese · Huayan | 643-712 |
| `/master-ouyi` | Ouyi | Chinese · Tiantai / Pure Land | 1599-1655 |
| `/master-xuyun` | Xuyun | Chinese · Chan (all five houses) | 1840-1959 |
| `/master-yinguang` | Yinguang | Chinese · Pure Land | 1861-1940 |
| `/master-atisha` | Atiśa Dīpaṃkara | Tibetan · Kadam (lamrim) | 982-1054 |
| `/master-milarepa` | Milarepa | Tibetan · Kagyu (Mahāmudrā) | 1052-1135 |
| `/master-tsongkhapa` | Tsongkhapa | Tibetan · Gelug (Prāsaṅgika) | 1357-1419 |
| `/master-buddhaghosa` | Buddhaghosa | Theravāda · commentarial | 5th c. |
| `/master-mahasi-sayadaw` | Mahāsi Sayādaw | Theravāda · Burmese vipassanā | 1904-1982 |
| `/master-ajahn-chah` | Ajahn Chah | Theravāda · Thai Forest | 1918-1992 |

**Teaching modes**: `/compare-masters` · `/master-debate` · `/master-curriculum` · `/master-help` · `/create-master`

> Life, doctrine, and declared sources for each → **[docs/masters.en.md](docs/masters.en.md)**

## Architecture

Directory layout and data flow → **[docs/architecture.en.md](docs/architecture.en.md)**

## Relationship to FoJin

[FoJin](https://fojin.app) is a Buddhist text aggregation platform integrating 503 data sources, 10K+ texts, 678K+ semantic vector embeddings, and a knowledge graph of 31K entities. It covers major corpora including CBETA Chinese Buddhist Canon, SuttaCentral Pali Canon and translations, and 84000 Tibetan Buddhist translations.

Master-skill connects to the FoJin API via `tools/fojin_bridge.py` to enable:

- Knowledge graph entity retrieval (master biography, lineage, school)
- Semantic similarity search (doctrinally relevant sutras)
- Runtime RAG retrieval for grounding answers in real texts
- Source passage extraction with provenance tracking

Every citation must resolve to the persona's declared source ID. A FoJin locator is added only when live retrieval returns a real `text_id`; otherwise the corresponding official catalog or offline declared source is used.

---

## Sensitivity Boundaries

**Will not:**

- Pass judgment on the relative merits of different schools or traditions
- Provide personal practice diagnoses (karma readings, past lives, etc.)
- Claim supernatural powers or auspicious experiences
- Engage with politically charged religious topics
- Offer medical advice

**Will:**

- Cite declared sources faithfully with traceable source IDs, adding a FoJin locator only when a real `text_id` is available
- Use runtime RAG only when the citation contract permits it and offline material is insufficient; never present model memory as a primary text
- Acknowledge clearly when a question falls outside scope
- Encourage users to seek out qualified masters and authentic practice

---

## Troubleshooting

Common install, invocation, and retrieval questions → **[docs/troubleshooting.en.md](docs/troubleshooting.en.md)**

## Contributing

Contributions are welcome: new prebuilt masters, corrections to source attributions, offline passage additions, or toolchain improvements.

New masters must follow the v0.3 layout: `prebuilt/<name>/` containing SKILL.md (with provenance routing and a decision tree), `meta.json` (declared sources plus citation contract), `references/teaching.md` and `references/voice.md` (loaded on demand), `sources/*.md` (offline declared-source passages), and `tests/fidelity.jsonl` (5+ Q&A fidelity samples). Run `python3 scripts/validate.py --strict` and `python3 scripts/validate-citation-contract.py` for zero errors, and make sure the CI fidelity dry-run passes before opening a PR.

Before submitting, verify that every source resolves to the persona's declared source family, content is faithful to historical documents, and no sectarian bias is introduced.

---

## License

MIT License

---

## Acknowledgments

Gratitude to the following open-source Buddhist text projects:

- [CBETA](https://cbeta.org) — digitized Chinese Buddhist Canon
- [SuttaCentral](https://suttacentral.net) — Pali Canon and multilingual translations
- [84000](https://84000.co) — Tibetan Buddhist translation project

---

## Community

- [LINUX DO](https://linux.do) — Thanks to the LINUX DO community for support and feedback
