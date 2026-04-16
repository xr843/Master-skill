# Changelog

All notable changes to Master-skill are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Sections marked **Ethics** track changes to `ETHICS.md`, content licensing, or boundary rules — these are governance-level changes and require the public-review process documented in `ETHICS.md §7`.

---

## [Unreleased]

### Added
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
