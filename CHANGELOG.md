# Changelog

All notable changes to Master-skill are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Sections marked **Ethics** track changes to `ETHICS.md`, content licensing, or boundary rules — these are governance-level changes and require the public-review process documented in `ETHICS.md §7`.

---

## [Unreleased]

### Added
- npm publish: `master-skill` package live on registry — `npm install -g master-skill` or `npx master-skill` now serves all three published versions (0.4.0 / 0.5.0 / 0.6.0). README badges added for npm version + monthly downloads.
- `ETHICS.md` — AI transparency, copyright tier (A/B/C/D), religious boundary, dual-track content license, takedown channel.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` — community infrastructure.
- `.github/ISSUE_TEMPLATE/` — bug report, feature request, new-master proposal, boundary-violation.
- `.github/PULL_REQUEST_TEMPLATE.md`.
- `.github/workflows/npm-publish.yml` — tag-triggered npm release.
- CI `fidelity-smoke` job — runs a single master × single fixture on every PR with a hard $0.05 cost cap, enforces HARD-GATE beyond dry-run.
- `package.json`: `engines.node`, `scripts.test`, `scripts.validate`, `publishConfig`.

### Ethics
- Establish copyright tiers A–D; current 8 prebuilt masters confirmed Tier A (Public Domain in CN/TW as of 2026).
- Declare dual-track content licensing: code MIT, master content CC BY-NC-SA 4.0, prompts CC BY 4.0.

---

## [0.6.0] — 2026-05-02

**Slash command namespace cleanup — every master now invokable via `/master-<slug>` (was `/<slug>`).**

When users have many skills installed in Claude Code (most do — 50+ in a typical setup), Buddhist master slash commands like `/atisha` and `/zhiyi` get scattered across the `/`-completion list and are hard to discover as a group. v0.6 prefixes all 14 master slash commands with `master-` so they cluster together under `/m<tab>` and clearly signal "this is a Master-skill master skill, not a generic slash command".

### Breaking changes
- **Slash commands renamed**: `/zhiyi` → `/master-zhiyi`, `/huineng` → `/master-huineng`, … all 14 masters affected. Existing automation, hotkeys, or aliases referencing the old names need updating.
- **Directory layout renamed**: `prebuilt/<slug>/` → `prebuilt/master-<slug>/` for all 14 masters. Frontmatter `name:` field also updated. The `compare-masters` and `create-master` meta-skills are **unchanged** (they're already prefixed by their nature — no `/master-compare-masters` doublespeak).
- **NPX installer accepts both forms**: `npx master-skill install zhiyi` (short) and `npx master-skill install master-zhiyi` (full) both work; the install destination is always `~/.claude/skills/master-<slug>/`. Backward-compatible uninstall handles legacy non-prefixed installs.

### Why now
- v0.5 just landed — the user base is essentially the maintainer + early adopters, so the breakage cost is at its lifetime minimum.
- npm has not yet been published (NPM_TOKEN pending), so external consumers pulling from `npx master-skill@latest` will get v0.6 directly.
- `fojin.app/chat` web frontend is **decoupled** from this rename: its master IDs in the dropdown stay as `atisha` / `huineng` / etc. (they're already grouped under "法师模式" and not at risk of conflict with other dropdowns). Backend `master_profiles.py` is unchanged. No fojin-side migration required.

### Changed
- All 14 master directories renamed (git mv preserves history).
- Each `prebuilt/master-<slug>/SKILL.md` frontmatter `name:` updated to `master-<slug>`.
- `prebuilt/compare/SKILL.md` master references and topic-mapping fallback table updated to use the new prefixed slugs (43 mentions).
- `bin/cli.mjs`: `cmdInstall` / `cmdUninstall` now accept both short and full forms (resolveMasterDir helper). `showHelp` updated with v0.6+ usage examples.
- `.github/workflows/validate-and-test.yml`: fidelity-smoke MASTERS rotation array updated to all 14 prefixed names (was 8 hardcoded汉传 only — now properly rotates across the full set).
- `scripts/{validate,cite,query,test-fidelity}.py` `--master` argument help text examples updated.
- All plugin manifests (`package.json`, `.claude-plugin/{plugin,marketplace}.json`, `.cursor-plugin/plugin.json`, `gemini-extension.json`) bumped to `0.6.0` with description noting the `/master-<slug>` invocation pattern.
- `SKILL.md` (project-level) preset list with new slash names.
- `README.md` + `README_EN.md`: situational guidance table, install snippets, and master cards updated.
- `ETHICS.md` Tier tables: 4 slug references updated.

### Migration for existing users
If you have v0.4 or v0.5 installed via NPX:

```bash
# Remove old non-prefixed installs:
npx master-skill@0.5 uninstall zhiyi huineng xuanzang ...
# OR manually rm -rf ~/.claude/skills/<slug>/

# Reinstall with v0.6:
npx master-skill@latest install --all
```

Then start a new Claude Code session and use `/master-<slug>` for all invocations.

### Validation
- `python scripts/validate.py --strict` → ✅ 15 masters
- `python scripts/validate-fidelity.py` → ✅ all valid
- `pytest tests/` → ✅ 31 passed, 6 skipped
- `node bin/cli.mjs list` → ✅ shows all 14 with `master-` prefix
- `node bin/cli.mjs install zhiyi` and `node bin/cli.mjs install master-zhiyi` both resolve correctly

---

## [0.5.0] — 2026-05-02

**Second cross-tradition expansion — 藏传 / 南传 each grow from 1 master to 3 (15 total).**

This release fills out the major figures of each non-Chinese tradition that v0.4 introduced. Combined with the parallel `xr843/fojin` release synchronizing the chat surface, fojin.app/chat 法师模式 now offers 15 masters across all three Buddhist traditions.

### Added
- **`atisha` — 阿底峡尊者 Atiśa Dīpaṃkara** (982-1054). 噶当派 Kadam school founder, 印藏桥梁 (Indo-Tibetan bridge). Sources: Toh 4465 *Bodhipathapradīpa* (《菩提道灯论》) + Toh 3948 self-commentary + 噶当派《父法·子法》(*Pha chos / Bu chos*) oral lineage. Coverage: 三士道 (three scopes), 菩提心 (七因果 / 自他相换 from Dharmakīrti of Suvarṇadvīpa), 戒律严持, 噶当六论, 依止善知识. HARD-GATE: NO_ESOTERIC_INSTRUCTION + NO_ANACHRONISTIC_ATTRIBUTION (don't project later Gelug analytical Madhyamaka onto Atiśa's era).
- **`tsongkhapa` — 宗喀巴大师 Je Rinpoche** (1357-1419). 格鲁派 Gelug founder, basis of the Dalai Lama / Panchen Lama lineages. Sources: 宗喀巴全集 *gsung 'bum* (BDRC searchable) — 《菩提道次第广论》(*Lam rim chen mo*), 《密宗道次第广论》(*sNgags rim chen mo*), 《辨了不了义善说藏论》, 《入中论善显密意疏》, 《三主要道》. Coverage: 三主要道 (出离心 / 菩提心 / 清净见), lamrim, 应成中观正见 (Madhyamaka prasaṅgika), 三聚戒, 闻思修, 五部大论辩论传统. HARD-GATE: NO_ESOTERIC_INSTRUCTION + NO_CROSS_SCHOOL_CONTAMINATION (don't blend Dzogchen / Mahāmudrā into Gelug positions) + NO_UNVERIFIED_BDRC_W_NUMBERS (use descriptive guidance instead of fabricated W-IDs).
- **`buddhaghosa` — 觉音尊者** (5th century). 上座部 Theravāda commentarial summit. Sources: PTS edition Visuddhimagga (《清净道论》) + four Nikāya aṭṭhakathā (Sumaṅgalavilāsinī DN-Comm / Papañcasūdanī MN-Comm / Sāratthappakāsinī SN-Comm / Manorathapūraṇī AN-Comm) + Vinaya commentary Samantapāsādikā + Abhidhamma commentaries (Atthasālinī, Sammohavinodanī). Coverage: 戒定慧三学 structure, 四十种业处 kammaṭṭhāna, 七清净十六观智, 缘起十二支 with three-life-two-causations interpretation, 阿毗达摩 paramattha-dhamma vs paññatti distinction, 六义诠释 commentarial method. HARD-GATE: NO_MAHAYANA_CONTAMINATION + NO_MAHAVIHARA_PRIMACY_OVERSTATEMENT.
- **`mahasi-sayadaw` — 马哈希尊者 Mahāsi Sayādaw U Sobhana** (1904-1982). 缅甸 Burmese Vipassanā tradition (Mahasi Method). Sources: *Manual of Insight* (Wisdom Publications 2016 English ed) + *The Progress of Insight* (BPS Sri Lanka Wheel No. 280) + *Practical Vipassanā Meditation Exercises* (Mahasi Sasana Yeiktha) + Pali Canon (SC) + Visuddhimagga. Coverage: 标记法 Noting Method, 腹部起伏 rising-falling primary object, 七清净十六观智 progress, 刹那定 khaṇika-samādhi & 毗婆舍那禅那 vipassanā-jhāna, '初果可证' ethos, MN 10 Satipaṭṭhāna foundation. HARD-GATE: NO_FABRICATED_QUOTES + **NO_ATTAINMENT_JUDGMENT** (the strictest guardrail in this release — Mahasi's "stages of insight" framework is infamous for inducing self-attainment delusions; AI is forbidden from confirming any individual's observed jhāna stage / fruition).
- **`scripts/validate-fidelity.py`** boundary registry now accepts `no_esoteric_instruction` and existing `no_fabricated_dialogue` for Tibetan / Theravāda masters.

### Changed
- All 4 plugin manifests (`package.json`, `.claude-plugin/{plugin,marketplace}.json`, `.cursor-plugin/plugin.json`, `gemini-extension.json`) bump from `0.4.0` → `0.5.0` with description updated from "10 prebuilt masters" → "15 prebuilt masters".
- `SKILL.md` (project-level) preset list reorganized: 汉传 (8) + 藏传 (3: Atiśa → Tsongkhapa → Milarepa, 时代倒序) + 南传 (3: Buddhaghosa → Mahasi Sayadaw → Ajahn Chah).
- `README.md` + `README_EN.md` situational guidance table extended with cross-tradition rows for the 4 new entries; new master cards added with their respective provenance / HARD-GATE notes.
- `prebuilt/compare/SKILL.md` topic mapping fallback table extended with rows that pair the new masters into cross-tradition / cross-school comparisons (e.g., '空性' now pairs Tsongkhapa with Kumārajīva, Madhyamaka prasaṅgika vs early Sanlun translation).

### Ethics
- **Tier A** (Public Domain) table grows from 8 → 11 masters: Atiśa (982-1054) + Tsongkhapa (1357-1419) + Buddhaghosa (5th century) join — all well past any modern jurisdiction's copyright term.
- **Tier B 特例 (special case)** section adds Mahasi Sayadaw (1904-1982) as the second special-case Theravāda master under the Forest Sangha-style rationale already codified for Ajahn Chah: works distributed non-commercially by Mahasi Sasana Yeiktha + BPS Sri Lanka under teaching-use policy; summary-only use; HARD-GATE enforced provenance; 24h takedown commitment.
- Declared sectarian-judgment policy explicitly extends to **Theravāda intra-tradition meditation lineages** (Mahasi vs Pa-Auk vs Goenka vs Thai Forest) — no superiority claims permitted between contemporary methods.

### Notes
- `fidelity.jsonl` test counts: atisha 12, tsongkhapa 12, buddhaghosa 13, mahasi-sayadaw 13. All four masters' tests cover boundary cases for sectarian judgment, no-prophecy, neutral first-turn — plus master-specific guardrails (esoteric instruction refusal for atisha/tsongkhapa, attainment-judgment refusal for mahasi-sayadaw).
- Validation: `python scripts/validate.py --strict` → ✅ 15 masters; `python scripts/validate-fidelity.py` → ✅ all valid; `pytest tests/` → ✅ 31 passed, 6 skipped.
- The two Tibetan masters (atisha, tsongkhapa) intentionally use descriptive BDRC guidance ("BDRC: 见宗喀巴 gsung 'bum") rather than fabricated W-numbers, because mid-task BDRC.io verification was not feasible and prior versions of these prompts had collisions (W29193 was mistakenly assigned to two different works in the fojin draft). Toh (Tohoku) numbers are kept where they're well-attested in 藏学界 (e.g., Toh 4465 for *Bodhipathapradīpa*).
- Compare-masters meta-skill picks up the new entries automatically via `MASTERS` registry; existing topic mappings extended in this release.

---

## [0.4.0] — 2026-05-02

**Cross-tradition expansion: from "Chinese Buddhist" to "Buddhist" — the project name now matches its scope.**

### Added
- **Milarepa** (`prebuilt/milarepa/`) — Tibetan Kagyu yogi (1052–1135). Sources: *The Hundred Thousand Songs of Milarepa* (mGur 'bum, BDRC W1KG14334) + *The Life of Milarepa* (rNam thar, BDRC W22272). Coverage: Mahāmudrā view, Naro Chodruk (introduced at name level only), retreat & austerity, guru yoga, karma & purification.
- **Ajahn Chah** (`prebuilt/ajahn-chah/`) — Thai Forest Tradition founder of Wat Pah Pong (1918–1992). Sources: Pali Canon (SuttaCentral SC IDs) + authorized English collections *Food for the Heart*, *A Still Forest Pool*, *Living Dhamma*. Coverage: sati & satipaṭṭhāna, ānāpānasati, three characteristics, letting go, Sīla-Samādhi-Paññā, middle way.
- HARD-GATE boundary **`no_esoteric_instruction`** — Tibetan tantric practice steps (tummo, generation/completion stages, specific empowerment-required visualizations and mantras) are **never** disclosed; queries are redirected to qualified teachers. Boundary added to `scripts/validate-fidelity.py`.
- HARD-GATE rule for Theravāda discourses — Ajahn Chah quotations must trace to authorized publications; no synthesized "Ajahn Chah said" dialogue.
- Citation system extended: `BDRC:Wxxxxx` (Tibetan canon) and `SuttaCentral` SC IDs are now first-class alongside CBETA `Txxnxxxx`.

### Changed
- Description across `package.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.cursor-plugin/plugin.json`: "Chinese Buddhist" → "Buddhist", "8 prebuilt masters" → "10 prebuilt masters across 汉传/藏传/南传".
- `README.md` + `README_EN.md`: added cross-tradition rows in the situational guidance table; new master cards for Milarepa and Ajahn Chah with appropriate provenance notes; v0.4 release note replaces the v0.3 banner.
- `SKILL.md` (project-level): preset list reorganized by tradition (汉传 / 藏传 / 南传).
- `package.json` `keywords`: added `tibetan-buddhism`, `theravada`, `bdrc`, `suttacentral`.

### Notes
- Both new masters keep the v0.3 progressive-disclosure shape (decision tree → references → sources → fidelity tests), so the cost profile of the fidelity-smoke CI job is unchanged.
- Esoteric content is intentionally absent from `prebuilt/milarepa/sources/` — this is enforced by content review, not just by the test suite.

---

## [0.3.0] — 2026-04-10

**Architectural rebuild around provenance, fidelity, and multi-platform delivery.**

### Added
- **Provenance frontmatter** — every `prebuilt/<master>/SKILL.md` now carries `sources:` (CBETA ID + FoJin text ID), `citation_format:`, `verified_by:`, `verified_at:`.
- **Offline sutra excerpts** — `prebuilt/<master>/sources/` ships canonical passages so masters remain useful when FoJin is unreachable.
- **Progressive disclosure architecture** — SKILL.md is decision-tree + quick-ref; heavyweight `references/teaching.md`, `references/voice.md`, and `sources/` load on demand.
- **Fidelity tests** — `prebuilt/<master>/tests/fidelity.jsonl`, 5 Q&A per master, verifying citations (`must_cite`), terminology (`must_mention`), and boundary rules (`must_not_contain_first_turn`).
- **NPX installer** — `npx master-skill install <master>` / `list` / `uninstall` / `--all`; `bin/cli.mjs`.
- **Multi-platform plugin support** — unified `prebuilt/` reused by Claude Code, Cursor, Codex CLI, OpenCode, Gemini CLI; per-platform hooks in `hooks/`, `.claude-plugin/`, `.cursor-plugin/`, `.codex/`, `.opencode/`, `gemini-extension.json`.
- **Session-start hook** — auto-injects the list of installed masters so the user does not re-issue `/list` each session.
- **HARD-GATE enforcement** — no CBETA citation → no dogmatic assertion; fabricated CBETA IDs rejected by `scripts/validate.py`; no persona for fictional / unattested figures.
- **Two-stage independent review** — `/create-master` pipeline runs doctrine-accuracy pass followed by voice-consistency pass, auto-fix up to 2 rounds.
- **Offline tooling** — `scripts/cite.py` (CBETA citation lookup), `scripts/query.py` (offline semantic search), `scripts/validate.py` (SKILL.md frontmatter linter), `scripts/validate-fidelity.py`, `scripts/test-fidelity.py`.
- **CI pipeline** (`.github/workflows/validate-and-test.yml`) — lint, fidelity structure validation, dry-run fidelity on every push/PR; full API-backed fidelity on `workflow_dispatch`.
- **Weekly link verification** (`.github/workflows/verify-links.yml`) — cron'd `tools/verify_sources.py` opens an issue when FoJin URLs or CBETA IDs drift.
- **`/compare-masters` meta-skill** — multi-master side-by-side answering with smart master selection, divergence radar, labeled differences, classic debate templates.
- **Cross-reference tool** (`tools/cross_reference.py`) for inter-master dialogue.
- **Browser-first onboarding** — README now directs non-CLI users to `fojin.app/chat` 法师模式 first; per-master `starter_questions` added.
- **Prebuilt masters** (8): 玄奘 (Xuanzang), 鸠摩罗什 (Kumārajīva), 慧能 (Huineng), 智顗 (Zhiyi), 法藏 (Fazang), 印光 (Yinguang), 蕅益 (Ouyi), 虚云 (Xuyun).

### Changed
- Project renamed `buddha-skill` → `Buddha-skill` → **`Master-skill`** to match AgentSkills naming conventions and emphasize teaching-persona framing.
- Focus narrowed to **汉传 (Chinese Mahāyāna)** — 南传 / 藏传 sections removed from PRD, prompts, and prebuilt set. Cross-tradition `compare` still possible via `/create-master` but not shipped.
- Per-master RAG queries in `/compare-masters` now enforce tradition-specific terminology to prevent cross-tradition drift.
- Smart master selection: keywords expanded 6 → 24 per master; first-turn identity-neutral (masters no longer assume user identity on first message).
- FoJin URL format corrected for juan paths; 186 FoJin URLs verified and updated from CBETA IDs to real internal `text_id`s.

### Fixed
- `fix(ci)`: `verify-links.yml` uses `context.repo.repo` instead of non-existent `context.repo.name`.
- `fix(lint)`: meta-skills (`compare-masters`) exempted from `lineage` / `sources` frontmatter checks.
- `fix`: `slugify` lowercases English names and handles spaces.
- `fix`: robust tool path resolution + precise selection feedback in `/compare-masters`.
- `fix`: escape `text_id` placeholder in `SKILL_MD_TEMPLATE` to survive Python `.format()`.

### Removed
- Early prebuilt masters **宗喀巴 (Tsongkhapa, Gelug)** and **Ajahn Chah (Thai Forest)** — retracted when scope refocused to 汉传 on 2026-04-04. Will return only via a future `Master-skill-beyond-chinese` branch with native-speaker reviewers.

### Documentation
- README: hero section with Diamond Sutra epigraph, badges, navigation; EN README synced to v0.3 parity.
- PRD (`docs/PRD.md`) refocused on 汉传.
- Plugin metadata synced across Cursor / Codex / OpenCode / Gemini extensions.

---

## [0.2.0] — 2026-04-05 (historical, no release tag)

Iteration layer between initial skeleton and full v0.3 rebuild. Highlights:
- `/compare-masters` skill first draft (P1).
- Graceful degradation when FoJin API is unavailable.
- Complete FoJin API reference for ad-hoc LLM queries.
- First-turn identity-neutral rule.
- Expanded flow control and error handling in SKILL.md.
- Community section added to README (linux.do link).

---

## [0.1.0] — 2026-04-04 (initial skeleton)

- Project skeleton, directory layout, prompt templates.
- FoJin data bridge (`tools/fojin_bridge.py`) with full API coverage.
- Version manager, skill writer, sutra collector, master builder orchestrator.
- Initial prebuilt masters (later expanded): 印光, Ajahn Chah, 宗喀巴, 玄奘, 鸠摩罗什, 慧能, 智顗, 法藏, 虚云, 蕅益.
- Source verification tool.
- Chinese + English README, PRD v1.0.0.

---

[Unreleased]: https://github.com/xr843/Master-skill/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/xr843/Master-skill/releases/tag/v0.3.0
