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
  <sub><em>Secured by SHA-pinned GitHub Actions · npm provenance · OIDC Trusted Publishing · CodeQL · cargo-audit · pip-audit — see <a href="SECURITY.md">SECURITY.md</a>.</em></sub>
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
- Live citation retrieval backed by FoJin's 10K+ texts and 678K+ semantic embeddings
- Answers cite sources in each master's declared format: mostly CBETA IDs for 汉传, Toh / BDRC numbers for 藏传, PTS / SuttaCentral references for 南传 (Theravāda and some Tibetan sources have no per-passage ID, and the citation contract says so)

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
| "I want the systematic Theravāda commentarial framework" | `/master-buddhaghosa` (*Visuddhimagga* — sīla / samādhi / paññā + 7 purifications · stages of insight knowledge) |
| "I want intensive vipassanā with the noting method" | `/master-mahasi-sayadaw` (Burmese · noting · rising-falling) |
| "I want a cross-tradition perspective" | `/compare-masters` (auto-pairs 汉/藏/南 voices) · `/master-debate` (adversarial dialectic) · `/master-curriculum` (study path by tradition) |

> Developers and Claude Code / Cursor users should skip to [Developer Installation](#developer-installation) to use the masters as terminal AgentSkills.

---

## What It Looks Like

A real `/master-huineng` answer, **reproduced unedited** (line-wrapped for display) from the 2026-08-31 full run — model `deepseek-v4-flash`, commit [`06b8142`](https://github.com/xr843/Master-skill/commit/06b814204082b3e4738185cf3eefa44ed149f9f0), index 1 of `master-huineng` in the [stored report](eval/reports/0.11.0-06b8142-deepseek.json). It graded PASS, and all five citations carry a CBETA ID that the repository's offline citation audit resolved to Huineng's declared sources (T48n2008 *Platform Sutra*, T08n0235 *Diamond Sutra*). Masters answer in Chinese; below is our English translation, with every citation kept exactly as the model wrote it:

```text
You: What is the difference between sudden awakening and gradual cultivation?

Master Huineng:

Tell me: are sudden and gradual really two different teachings?

The Dharma itself is neither sudden nor gradual; people differ in
sharpness and dullness. The sutra says, "Unawakened, a buddha is a
sentient being; in one moment of awakening, a sentient being is a
buddha" — delusion and awakening lie in a single thought, hence the name
"sudden". It also says, "The previous thought deluded is an ordinary
person; the next thought awakened is a buddha" — turning delusion into
awakening needs nothing sought outside
【《六祖坛经·般若品》，T48n2008】→ https://fojin.app/texts/58

Shenxiu of the Northern School wrote the verse: "The body is the bodhi
tree, the mind a bright mirror stand; wipe it diligently at all times,
and let no dust alight." — an expedient for gradually sweeping away
defilement. The Sixth Patriarch answered: "Bodhi has no tree, the bright
mirror is no stand. Originally there is not a single thing — where could
dust alight?" — directly revealing that self-nature is empty at root,
with nothing that can stain it
【《六祖坛经·行由品》，T48n2008】→ https://fojin.app/texts/58. One deliberately
applies antidotes; the other takes it up right here. These two verses
mark exactly where sudden and gradual part ways.

Yet sudden and gradual are not two. Even concentration and wisdom are
one — "concentration is the substance of wisdom, wisdom the function of
concentration; at the moment of wisdom, concentration is in wisdom; at
the moment of concentration, wisdom is in concentration"
【《六祖坛经·定慧品》，T48n2008】→ https://fojin.app/texts/58 — so how could sudden
and gradual be two kinds? The deluded cultivate gradually, the awakened
accord at once; the medicine is given for the illness, and the Dharma
has no high or low 【《六祖坛经·定慧品》，T48n2008】→ https://fojin.app/texts/58.

Know too that the Sixth Patriarch saw his own nature on hearing "give
rise to a mind that abides nowhere"
【《金刚经》，T08n0235】→ https://fojin.app/texts/7. Sudden awakening is not
mindlessness; it is not abiding in objects. Gradual cultivation is not
dead sitting; it is awareness in thought after thought. In the end there
is only one question: turning the light around in a single thought — has
the original mind appeared yet?

For further study, consult the original texts at FoJin (fojin.app).
```

> ⚠️ The above is **AI-synthesized content**, generated from the *Platform Sutra* and *Diamond Sutra*; it does not represent Master Huineng's actual spoken teachings. The Chinese original is in [README.md](README.md#效果示例). Try the multi-master `/compare-masters` mode directly at [fojin.app/chat](https://fojin.app/chat).

---

Master-skill is a [FoJin](https://fojin.app)-powered Buddhist AI persona framework: grounded in primary sources, constrained by ethical boundaries, checked by fidelity tests, and packaged as runtime-ready AgentSkills for Claude Code, Cursor, Codex CLI, OpenCode, and Gemini CLI.

---

## Seriousness Statement

This project is built out of respect for Buddhist traditions. All content is generated faithfully from historical documents. It makes no doctrinal judgments and claims no sectarian authority. Generated content is intended for study and reference only. For formal practice guidance, please seek out a qualified master and rely on genuine, living instruction.

---

## Features

- **15 pre-built masters across four traditions**: 1 印度 (Madhyamaka · Nāgārjuna) + 8 汉传 (Yogācāra, Madhyamaka, Chan, Tiantai, Huayan, Pure Land, cross-tradition) + 3 藏传 (Kadam · Atiśa; Gelug · Tsongkhapa; Kagyu · Milarepa) + 3 南传 (Theravāda commentator · Buddhaghosa; Burmese vipassanā · Mahasi Sayadaw; Thai Forest · Ajahn Chah) — plus 4 teaching modes (`/compare-masters` side-by-side, `/master-debate` multi-round dialectic, `/master-curriculum` study path, `/master-help` who-to-ask) and the `/create-master` generator
- **Provenance enforcement**: Every master ships with declared source IDs (CBETA / BDRC / Toh / SuttaCentral / PTS / compliant compiled teachings); live retrieval adds a FoJin locator only when a real `text_id` is returned, and every doctrinal claim must carry a source citation
- **Offline source passages**: `sources/` captures key passages from each master's core canon, so citations still work when FoJin is unreachable
- **Progressive disclosure**: SKILL.md is a decision tree + quick reference; `references/` and `sources/` are loaded on demand to keep context lean
- **HARD-GATE discipline**: Both `/create-master` and every prebuilt master require doctrinal claims, practice guidance, and text interpretation to cite that persona's declared sources (CBETA / BDRC / Toh / SuttaCentral / PTS / compliant compiled teachings); fabricated source IDs and fictional personas are forbidden
- **Two-stage independent review**: The generation pipeline forces a "doctrinal accuracy → voice consistency" review before write; FAIL triggers up to 2 rounds of automatic repair
- **Automated fidelity tests**: 211 fixtures (10+ per master, 18 for the `compare-masters` meta-skill) check keyword and citation coverage, and every graded answer also goes through the offline citation audit; CI runs a structural dry-run on every PR and on `main`; graded runs support Anthropic / DeepSeek / Gemini (`--provider`) with the matching API key, as a manual local/pre-release step — the latest full run and its case-by-case adjudication are [below](#fidelity-evaluation-current-data)
- **One `prebuilt/` tree across platforms**: Claude Code, Cursor, Codex CLI, OpenCode, and Gemini CLI each install it differently (see [docs/install.en.md](docs/install.en.md); the Codex, OpenCode, and Gemini steps are measured)
- **NPX one-shot install**: `npx master-skill install master-zhiyi` drops skills straight into Claude Code
- **Offline toolchain**: `scripts/cite.py` (CBETA lookup), `scripts/query.py` (offline semantic search), `scripts/validate.py` (frontmatter linter)
- **FoJin data bridge**: Connected to [fojin.app](https://fojin.app) — 10K+ texts, 678K+ semantic embeddings, a knowledge graph of 110K+ entities, and 600+ registered data sources
- **AgentSkills standard**: Compliant with [Anthropic Agent Skills](https://github.com/anthropics/skills) — progressive disclosure, decision trees, black-box script pattern

## Framework Positioning

Master-skill is not a prompt pack. It is a verifiable Buddhist AI persona framework:

| Dimension | Implementation |
|---|---|
| Source-grounded | `sources[]`, offline excerpts, FoJin live fallback, and citation self-audits per master |
| Boundary-aware | `ETHICS.md`, per-master Layer 0 HARD-GATE rules, copyright tiers, and boundary violation reporting |
| Fidelity-tested | `tests/fidelity.jsonl`, persona-fidelity schema, promptfoo RAW / SPE / CUS evals (currently for 3 masters: Huineng, Tsongkhapa, Ajahn Chah), [current data below](#fidelity-evaluation-current-data) |
| Runtime-ready | `prebuilt/master-*` AgentSkills, npm CLI, multi-platform hooks, and a FoJin runtime contract |

The v1.0 track prioritizes framework stability over adding more masters. See [docs/v1-framework-roadmap.md](docs/v1-framework-roadmap.md) and [docs/fojin-runtime-contract.md](docs/fojin-runtime-contract.md).

### Fidelity evaluation (current data)

The 211 fixtures (`prebuilt/*/tests/fidelity.jsonl`) run mechanical checks against real model answers: do the expected keywords and citations appear, and do the forbidden ones stay out. Every graded answer also goes through the offline citation audit. Read each number together with the model and the grading method that produced it:

| | Value | Basis |
|---|---|---|
| Latest full run | **199 / 211 graded** (94.3%) | DeepSeek `deepseek-v4-flash`, commit [`06b8142`](https://github.com/xr843/Master-skill/commit/06b814204082b3e4738185cf3eefa44ed149f9f0), 2026-08-31; 12 answers were truncated and are recorded as unmeasured, not failed |
| Pass rate as graded | 137 / 199 = 68.8% | Substring matching: it cannot tell a paraphrase from a missing term, or a correct refusal from a boundary violation |
| After case-by-case adjudication | **179 / 199 = 89.9%** | doctrine 94.3% · boundary 85.9% · citation-under-pressure 83.3%. 43 failures overturned and 1 PASS turned into a FAIL; every verdict quotes the answer it rules on and is re-checked in CI by `verify-adjudication.py` |
| Citation audit coverage | **574 / 619 = 93%**, 3 judged fabricated | The same stored answers re-audited offline with the current auditor, across the CBETA, BDRC / Toh, PTS / SuttaCentral, and compiled-teaching families. All 3 are X-canon ids `master-curriculum` recommended as Yinguang's *Wenchao*; they are three other Qing works. Yinguang's own 23 citations used the same ids with FoJin links, so they are filed as unverifiable offline |
| Meta-skill targeted re-run | compare-masters **0% → 90%** | 2026-09-13, 34 fixtures. After their output templates were fixed, `compare-masters` citations went from 0% to 90% checkable and `master-curriculum` from 0% to 100%; `master-debate` used to write sutra IDs in parentheses the audit could not see at all, and is now at 100% |
| Teaching modes with file tools | **455 citations, 0 fabricated**; 40 / 41 | 2026-09-25, all four teaching modes, 44 fixtures, DeepSeek `deepseek-v4-flash`, ¥2.61. The teaching modes could read their sibling masters' files as their instructions say for the first time (the eval used to give no tools, and six replies that wrote the tool call out as text had graded PASS); leaked tool calls fell to 0, and every fixture read files. A different instrument from the row above, so pass rates are not compared; 2 truncated and 1 at the tool-round cap are outside the 41. Report: [`0.12.15-df76fd2-deepseek-metaskills-tools.json`](eval/reports/0.12.15-df76fd2-deepseek-metaskills-tools.json) |

**This column cannot advance the v1.0 gate.** The gate is defined on the Anthropic (`claude-sonnet-4-6`) column; two models are two instruments and are never pooled. That column still holds only one partial run, from 2026-08-18 (84 / 211, stopped when the account ran out of credit), whose "zero fabricated citations" was retracted on 2026-08-31 — the audit had not actually run on a single case.

**These numbers belong to the tree at `06b8142`.** Persona content and the fixtures themselves have changed since (see the 0.12.x entries in the CHANGELOG: how sutta summaries are framed, where routing points, lineage sanitization), and nothing has been re-measured — that needs another paid full run. The fixture count is still 211, which does not mean their content is unchanged.

**The grader of that run did not check the teaching modes' output contracts.** Seven assertion kinds across the 44 teaching-mode fixtures — required sections, choosing the right masters, debate rounds, a source in every round or master's section, recommending a skill that exists — were never graded until 2026-09-23. Re-grading the stored answers above with the current grader moves 2 more `master-debate` cases from PASS to FAIL (#0 has no rounds; in #2, the closing round R4 cites nothing). They passed at the time, so no one adjudicated them, and the numbers above do not count them. In the 2026-09-13 teaching-mode re-run, 5 of `compare-masters`' 11 PASSes and 1 of `master-debate`'s 4 were leaked tool-call markup, not answers; all six now fail.

These are **keyword and citation-string coverage checks, not doctrinal correctness and not LLM-judged answer quality**. Details: [BASELINE-deepseek.md](eval/reports/BASELINE-deepseek.md) (the full run), [ADJUDICATION.md](eval/reports/ADJUDICATION.md) (case-by-case rulings), [BASELINE.md](eval/reports/BASELINE.md) (the Anthropic partial run and its retraction), and the [meta-skill re-run report](eval/reports/0.11.0-e97ded0-deepseek-metaskills.json).

---

## Developer Installation

> 👤 **Just want to try it?** Use [fojin.app/chat](https://fojin.app/chat) — no install needed.
> 🛠️ **This section is for** Claude Code / Cursor / Codex CLI / OpenCode / Gemini CLI users.

```bash
npx master-skill install --all          # all 20 skills at once
npx master-skill install master-huineng # or just one
npx master-skill list                   # see everything installable
npx master-skill recommend "how do I actually practice nianfo"   # not sure who to ask?
npx master-skill doctor                 # check the local install and runtime paths
npx master-skill update --all           # upgrade: reinstall everything, clearing stale files
```

Once installed, invoke `/master-huineng`, `/compare-masters`, etc. directly in chat. npx installs to `~/.claude/skills/`, which Claude Code and OpenCode read; **Codex CLI and Gemini CLI do not**, so use their sections in docs/install.en.md.

> Per-platform setup (Claude Code plugin / Cursor / OpenCode / Codex CLI / Gemini CLI),
> global install, teaching-mode usage, and `/create-master`
> → **[docs/install.en.md](docs/install.en.md)**

## Desktop Manager

A native desktop console (pure Rust, egui, single binary, no Electron) that unifies management of installation status, fidelity evaluation coverage, run tracing, and the quality gate across 18 skills (the 15 masters plus `master-debate`, `master-curriculum` and `master-help`):

![Master-skill Desktop Manager](https://raw.githubusercontent.com/xr843/Master-skill/main/docs/assets/desktop-manager.png)

**Download**: [Releases](https://github.com/xr843/Master-skill/releases) provides pre-built binaries for Linux / Windows / macOS; run them from the root of a local clone (they call the repository's `scripts/` and `bin/`). From v0.12.1, on Linux/macOS, prefer the matching `.tar.gz`, which keeps the executable bit when extracted; the raw binaries remain for compatibility and need `chmod +x`. Each release from v0.12.1 carries `SHA256SUMS` — check a download with `sha256sum --check --ignore-missing SHA256SUMS` — and build-provenance attestations, verifiable with `gh attestation verify <file> --repo xr843/Master-skill` (needs a recent gh CLI: 2.51 fails with `unsupported tlog public key type`, 2.100 works). **No working Windows desktop binary exists before v0.12.1** — earlier ones cannot launch Python or npm, and v0.12.0 failed to build one; from v0.12.1 it resolves them per platform, and from v0.12.2 the release workflow runs the packaged binary on Linux, Windows and macOS hosts (`--help` and `--baseline`); if it still fails to find them, set `MASTER_SKILL_PYTHON` / `MASTER_SKILL_NPM`. The Windows binary is a console program, so double-clicking it also opens a console window. A GUI-subsystem build would remove that window, but when tested it crashed as soon as PowerShell redirected or piped its command-line output. The macOS binary is unsigned, so first launch still requires right-click → Open or `xattr -d com.apple.quarantine <file>`.

**Build from source** (Rust 1.95+):

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
| `/master-yinguang` | Yinguang | Chinese · Pure Land | 1862-1940 |
| `/master-atisha` | Atiśa Dīpaṃkara | Tibetan · Kadam (lamrim) | 982-1054 |
| `/master-milarepa` | Milarepa | Tibetan · Kagyu (Mahāmudrā) | 1052-1135 |
| `/master-tsongkhapa` | Tsongkhapa | Tibetan · Gelug (Prāsaṅgika) | 1357-1419 |
| `/master-buddhaghosa` | Buddhaghosa | Theravāda · commentarial | 5th c. |
| `/master-mahasi-sayadaw` | Mahāsi Sayādaw | Theravāda · Burmese vipassanā | 1904-1982 |
| `/master-ajahn-chah` | Ajahn Chah | Theravāda · Thai Forest | 1918-1992 |

**Teaching modes**: `/compare-masters` · `/master-debate` · `/master-curriculum` · `/master-help` · **Generator**: `/create-master`

> Life, doctrine, and declared sources for each → **[docs/masters.en.md](docs/masters.en.md)**

## Architecture

Directory layout and data flow → **[docs/architecture.en.md](docs/architecture.en.md)**

## Relationship to FoJin

[FoJin](https://fojin.app) is a Buddhist text aggregation platform holding 10K+ texts (about 9K of them in full text), 678K+ semantic vector embeddings, and a knowledge graph of 110K+ entities. It registers 600+ data sources, but **only four supply full text** — the CBETA Chinese Buddhist Canon, the SuttaCentral Pali Canon and translations, 84000's Tibetan Buddhist translations, and the GRETIL Sanskrit library; the rest are metadata records.

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

New masters must follow the v0.3 layout: `prebuilt/<name>/` containing SKILL.md (with provenance routing and a decision tree), `meta.json` (declared sources plus citation contract), `references/teaching.md` and `references/voice.md` (loaded on demand), `sources/*.md` (offline declared-source passages), and `tests/fidelity.jsonl` (5+ Q&A fidelity samples, at least one of them a boundary case). Run `python3 scripts/validate.py --strict`, `python3 scripts/validate-fidelity.py` and `python3 scripts/validate-citation-contract.py` for zero errors, and make sure the CI fidelity dry-run passes before opening a PR.

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
