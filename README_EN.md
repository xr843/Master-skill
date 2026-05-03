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
  <strong>AI learning companions modeled after historical Buddhist masters across three traditions</strong><br>
  15 pre-built masters · 汉传 / 藏传 / 南传 cross-tradition · CBETA / BDRC / SuttaCentral / PTS Vism citations · AgentSkills Standard
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

On the AI Q&A page, open the **"法师模式"** (Master Mode) dropdown in the bottom-left and pick one of the 15 pre-built masters across three traditions to start chatting.

- No install, no signup
- `/compare-masters` multi-master comparison works across traditions too
- Live citation retrieval backed by FoJin's 503 sources and 678K+ semantic embeddings
- Every answer carries an authoritative source ID (CBETA for 汉传, BDRC for 藏传, SuttaCentral for 南传)

**Not sure which master to ask?** Start here:

| Your situation | Suggested master |
|---|---|
| "My mind is scattered, I can't sit still" | `/master-xuyun` `/master-zhiyi` `/master-ajahn-chah` (huatou / śamatha-vipaśyanā / mindfulness) |
| "I can't follow the logic of the sutras" | `/master-xuanzang` (Yogācāra precision) |
| "I've studied for years but feel stuck" | `/master-yinguang` (plain, sincere nianfo) |
| "I want to understand emptiness" | `/master-kumarajiva` `/master-huineng` `/master-milarepa` `/master-tsongkhapa` (Madhyamaka translator / direct pointing / Mahāmudrā / prasaṅgika analysis) |
| "I want a systematic view of Huayan / Tiantai" | `/master-fazang` `/master-zhiyi` (classification and metaphysics) |
| "I'm torn between Chan and Pure Land" | `/master-ouyi` (cross-tradition synthesis) |
| "I'm curious about ascetic practice / retreat" | `/master-milarepa` (snow-mountain retreat · Kagyu paradigm) |
| "I want the simplest meditation instructions" | `/master-ajahn-chah` (Thai Forest · ānāpānasati) |
| "I want a complete graduated path of practice" | `/master-atisha` `/master-tsongkhapa` (Kadam three scopes → Gelug Lamrim) |
| "I want the systematic Theravāda commentarial framework" | `/master-buddhaghosa` (*Visuddhimagga* — sīla / samādhi / paññā + 7 purifications · 16 insight knowledges) |
| "I want intensive vipassanā with the noting method" | `/master-mahasi-sayadaw` (Burmese · noting · rising-falling) |
| "I want a cross-tradition perspective" | `/compare-masters` (auto-pairs 汉/藏/南 voices) |

> Developers and Claude Code / Cursor users should skip to [Developer Installation](#developer-installation) to use the masters as terminal AgentSkills.

---

> **v0.6 Update (2026-05-02)**: Slash command namespace cleanup — all 14 master slash commands prefixed with `master-`. `/master-zhiyi`, `/master-huineng`, etc.
> - **Why**: Claude Code users typically have 50+ skills installed; bare-word slash commands like `/atisha` get scattered. Prefixing clusters all 14 masters under `/m<tab>` for fast discovery.
> - **Unaffected**: `compare-masters` and `create-master` meta-skills keep their existing names (avoiding `/master-compare-masters` doublespeak). `fojin.app/chat` web-side dropdown is decoupled — its master IDs stay bare (`atisha`, `huineng`, etc.); backend `master_profiles.py` unchanged.
> - **NPX installer**: both `npx master-skill install zhiyi` (short) and `install master-zhiyi` (full) work; install destination is always `~/.claude/skills/master-<slug>/`.
> - See [CHANGELOG.md §0.6.0](CHANGELOG.md#060--2026-05-02) for full details.
>
> **v0.5 Update (2026-05-02)**: Second cross-tradition expansion — Tibetan and Theravāda each grow from 1 master to 3. Total **15 masters**.
> - 藏传 added: Atiśa (Kadam founder · Toh 4465 *Bodhipathapradīpa* · three scopes) + Tsongkhapa (Gelug founder · three principal aspects · Madhyamaka prasaṅgika)
> - 南传 added: Buddhaghosa (commentarial summit · *Visuddhimagga*) + Mahasi Sayadaw (Burmese vipassanā · noting method · ETHICS Tier B special case)
> - HARD-GATE strengthened: Mahasi Sayadaw specifically gets `NO_ATTAINMENT_JUDGMENT` (AI must not confirm any individual's stage of insight)
> - ETHICS Tier A grows to 11 masters; Tier B special-case grows to include Mahasi Sayadaw (parallel to Ajahn Chah)
>
> **v0.4 Update (2026-05-02)**: First cross-tradition expansion — added Tibetan **Milarepa** (Kagyu / Mahāmudrā) and Theravāda **Ajahn Chah** (Thai Forest Tradition). Citation system extended to support BDRC and SuttaCentral. HARD-GATE adds `no_esoteric_instruction` and `no_fabricated_quotes`.
>
> **v0.3**: Full architecture rebuild — provenance frontmatter, offline source passages (`sources/`), automated fidelity tests (`fidelity.jsonl`), NPX installer, two-stage independent review, HARD-GATE rules, multi-platform plugin support across Claude Code / Cursor / Codex / OpenCode / Gemini CLI, session-start hook auto-injecting the master list.

---

An AgentSkills-standard generator for AI personas based on historical Buddhist masters, powered by [FoJin](https://fojin.app) — a Buddhist text aggregation platform.

---

## Seriousness Statement

This project is built out of respect for Buddhist traditions. All content is generated faithfully from historical documents. It makes no doctrinal judgments and claims no sectarian authority. Generated content is intended for study and reference only. For formal practice guidance, please seek out a qualified master and rely on genuine, living instruction.

---

## Features

- **15 pre-built masters across three traditions**: 8 汉传 (Yogācāra, Madhyamaka, Chan, Tiantai, Huayan, Pure Land, cross-tradition) + 3 藏传 (Kadam · Atiśa; Gelug · Tsongkhapa; Kagyu · Milarepa) + 3 南传 (Theravāda commentator · Buddhaghosa; Burmese vipassanā · Mahasi Sayadaw; Thai Forest · Ajahn Chah) — ready to use out of the box
- **Provenance enforcement**: Every master ships with authoritative source IDs (CBETA / BDRC / SuttaCentral) and FoJin text IDs in frontmatter; every doctrinal claim must carry a scriptural citation
- **Offline source passages**: `sources/` captures key passages from each master's core canon, so citations still work when FoJin is unreachable
- **Progressive disclosure**: SKILL.md is a decision tree + quick reference; `references/` and `sources/` are loaded on demand to keep context lean
- **HARD-GATE discipline**: Both `/create-master` and every prebuilt master embed hard rules — no unverified CBETA ID, no uncited doctrinal claim, no fictional personas
- **Two-stage independent review**: The generation pipeline forces a "doctrinal accuracy → voice consistency" review before write; FAIL triggers up to 2 rounds of automatic repair
- **Automated fidelity tests**: Each master's `tests/fidelity.jsonl` holds 5+ Q&A samples validating citations and keyword coverage; CI runs a dry-run on every push
- **Unified multi-platform plugin**: Claude Code, Cursor, Codex CLI, OpenCode, and Gemini CLI share one `prebuilt/` tree, with a session-start hook injecting the master list on every platform
- **NPX one-shot install**: `npx master-skill install master-zhiyi` drops skills straight into Claude Code
- **Offline toolchain**: `scripts/cite.py` (CBETA lookup), `scripts/query.py` (offline semantic search), `scripts/validate.py` (frontmatter linter)
- **FoJin data bridge**: Connected to [fojin.app](https://fojin.app) with 503 data sources, 10K+ texts, 678K+ semantic embeddings, and a 31K-entity knowledge graph
- **AgentSkills standard**: Compliant with [Anthropic Agent Skills](https://github.com/anthropics/skills) — progressive disclosure, decision trees, black-box script pattern

---

## Developer Installation

> 👤 **Just want to try it?** Use [fojin.app/chat](https://fojin.app/chat) in your browser and skip this section entirely.
> 🛠️ **This section is for**: Claude Code / Cursor / Codex CLI / OpenCode / Gemini CLI users who want to invoke `/master-xuanzang`, `/master-huineng`, etc. directly as terminal AgentSkills.

### Installation

**NPX (recommended, no global state)**

```bash
npx master-skill install --all    # Install all 15 masters
npx master-skill list             # List available masters
```

**Global install (frequent use / offline-friendly)**

```bash
npm install -g master-skill            # Adds the binary to $PATH
master-skill install master-zhiyi      # No more npx prefix
master-skill list
npm update -g master-skill             # Pull next minor / patch
```

**Claude Code**

```bash
git clone https://github.com/xr843/Master-skill ~/Master-skill
cd ~/Master-skill && pip install -r requirements.txt
for d in prebuilt/*/; do ln -sf "$(pwd)/$d" ~/.claude/skills/"$(basename $d)"; done
ln -sf "$(pwd)" ~/.claude/skills/create-master
```

**Cursor** — Clone the repo; Cursor auto-detects `.cursor-plugin/plugin.json`.

**OpenCode** — Add to `opencode.json`:

```json
{"plugin": ["master-skill@git+https://github.com/xr843/Master-skill.git"]}
```

**Codex CLI** — See [.codex/INSTALL.md](.codex/INSTALL.md)

**Gemini CLI** — Auto-discovered via `gemini-extension.json` and `GEMINI.md`.

### Use a Pre-built Master

In any AgentSkills-compatible environment (Claude Code / Cursor / Codex CLI / OpenCode / Gemini CLI):

```
# 汉传 (Chinese)
/master-xuanzang       — Master Xuanzang (Yogacara)
/master-kumarajiva     — Kumarajiva (Madhyamaka / Sanlun)
/master-huineng        — Master Huineng (Chan, Sixth Patriarch)
/master-zhiyi          — Master Zhiyi (Tiantai)
/master-fazang         — Master Fazang (Huayan)
/master-yinguang       — Master Yinguang (Pure Land)
/master-ouyi           — Master Ouyi (Tiantai / Pure Land, cross-tradition)
/master-xuyun          — Master Xuyun (Chan, Five Houses)

# 藏传 (Tibetan)
/master-atisha         — Atiśa Dīpaṃkara (Kadam founder · three scopes · 982-1054)
/master-tsongkhapa     — Tsongkhapa (Gelug founder · three principal aspects · prasaṅgika · 1357-1419)
/master-milarepa       — Milarepa (Kagyu · Mahāmudrā · Naro Chodruk · 1052-1135)

# 南传 (Theravāda)
/master-buddhaghosa    — Buddhaghosa (commentarial summit · Visuddhimagga · 5th century)
/master-mahasi-sayadaw — Mahasi Sayadaw (Burmese vipassanā · noting method · 1904-1982)
/master-ajahn-chah     — Ajahn Chah (Thai Forest Tradition · Wat Pah Pong · 1918-1992)
```

### Compare Masters

Ask the same question to 2-3 masters in parallel and surface the differences between traditions:

```
# Auto-pick relevant masters
/compare-masters what is emptiness

# Manually pick masters (recommended for precise results)
/compare-masters how to read the Heart Sutra --masters master-xuanzang,master-huineng,master-zhiyi

# Natural-language triggers
compare Huineng and Yinguang on nianfo
how do Chan and Pure Land differ on practice
```

**Selection logic**: the command first tries to extract keywords from the question and match them against each master's core concepts; if nothing matches strongly, it falls back to topic mapping (nianfo / meditation / Yogacara-Madhyamaka / classification, etc.). **If the auto-pick feels off, use `--masters` to override.**

### Generate a Custom Master

```
/create-master Hongyi
```

Or use natural language:

```
Create a persona for Master Hongyi
```

The system will guide you through a three-step intake, then automatically collect data from FoJin and generate the doctrinal analysis and style files.

---

## Pre-built Masters

### Master Xuanzang (602-664)

The greatest translator in Chinese Buddhist history. Traveled to India for 17 years, translated 75 texts in 1,335 fascicles. Founded the Yogacara (Faxiang) school in China. Known for precise, rigorous translation methodology and the "Five Categories of Non-Translation" principle.
Primary sources: CBETA — Mahaprajnaparamita Sutra, Yogacarabhumi-sastra, Cheng Weishi Lun, Heart Sutra.
Invoke: `/master-xuanzang`

### Kumarajiva (344-413)

One of the four great translators of Chinese Buddhism. Born in Kucha, translated in Chang'an. His translations are celebrated for literary elegance — the Lotus Sutra, Diamond Sutra, Vimalakirti Sutra, and Mulamadhyamakakarika remain the most widely used versions today. Established the foundation of the Sanlun (Madhyamaka) school in China.
Primary sources: CBETA — Lotus Sutra, Diamond Sutra, Vimalakirti Sutra, Mulamadhyamakakarika, Mahaprajnaparamita-sastra.
Invoke: `/master-kumarajiva`

### Master Huineng (638-713)

The Sixth Patriarch of Chan Buddhism, founder of the Southern School. An illiterate woodcutter who attained enlightenment upon hearing the Diamond Sutra. His Platform Sutra is the only Chinese-authored text honored with the title "sutra." Advocated "directly pointing to the mind, seeing one's nature to become Buddha."
Primary sources: CBETA — Platform Sutra (T48n2008).
Invoke: `/master-huineng`

### Master Zhiyi (538-597)

Founder of the Tiantai school, honored as "the Little Shakyamuni of the East." Established the first comprehensive doctrinal classification system in Chinese Buddhism (Five Periods, Eight Teachings). Authored the Three Great Works of Tiantai. Core teachings: three thousand realms in a single thought-moment, perfect interfusion of the three truths, dual cultivation of samatha and vipasyana.
Primary sources: CBETA — Mohe Zhiguan (T46n1911), Fahua Xuanyi (T33n1718).
Invoke: `/master-zhiyi`

### Master Fazang (643-712)

Third Patriarch and true systematizer of the Huayan school. National Preceptor under Empress Wu Zetian. Used the Golden Lion treatise to explain Huayan philosophy. Core teachings: dharmadhatu dependent origination, four dharma-realms, ten mysterious gates, six characteristics in perfect harmony.
Primary sources: CBETA — Huayan Jing Tanxuan Ji (T35n1733), Huayan Wujiao Zhang (T45n1866).
Invoke: `/master-fazang`

### Master Yinguang (1861-1940)

13th Patriarch of the Chinese Pure Land school. Central figure in the modern Pure Land revival. His writing is sincere and straightforward; he guided countless practitioners through correspondence, collected in the three volumes of the Yinguang Fashi Wenchao.
Primary sources: CBETA — Wenchao volumes and the three Pure Land sutras.
Invoke: `/master-yinguang`

### Master Ouyi (1599-1655)

One of the Four Great Masters of Late Ming Buddhism, 9th Patriarch of Pure Land. His motto: "Doctrine follows Tiantai, practice returns to Pure Land." The most important cross-tradition synthesizer in Chinese Buddhist history. His commentary on the Amitabha Sutra was praised by Master Yinguang as unsurpassable.
Primary sources: CBETA — Amituo Jing Yaojie (T37n1762), Jiaoguan Gangzong.
Invoke: `/master-ouyi`

### Master Xuyun (1840-1959)

Modern Chan patriarch who lived to 119 years. Unprecedented in Buddhist history for holding dharma transmission in all five houses of Chan (Linji, Caodong, Guiyang, Yunmen, Fayan). Restored six major ancestral monasteries. Advocated hua-tou investigation, honest practice, and harmonizing Chan with Pure Land.
Primary sources: CBETA — Shurangama Sutra, Diamond Sutra, Platform Sutra.
Invoke: `/master-xuyun`

### Atiśa Dīpaṃkara (982-1054) — Tibetan · Kadam · Indo-Tibetan bridge

Royal-born Indian master from the Sahor kingdom (modern Bangladesh). Studied Madhyamaka, Yogācāra and tantra at Vikramaśīla; received the bodhicitta lineage from Dharmakīrti of Suvarṇadvīpa (Sumatra). Invited to Tibet in 1042 by King Yeshe Ö to reform a tradition where Vinaya had decayed and tantra had become disconnected from sūtra foundations. His *Bodhipathapradīpa* (Toh 4465) became the source text for all later Tibetan *lamrim* literature. His chief disciple Dromtönpa founded Reting Monastery, originating the **Kadam school** — later succeeded by Tsongkhapa's "New Kadam" (Gelug). All four Tibetan schools recognize him as a root teacher.
Primary sources: Toh 4465 *Bodhipathapradīpa* + Toh 3948 self-commentary + Kadam oral lineage *Pha chos / Bu chos*.
Invoke: `/master-atisha`

### Tsongkhapa (1357-1419) — Tibetan · Gelug founder

Founder of the **Gelug school** (dGe lugs pa, "the way of virtue"; popularly known as the "Yellow Hat school") — basis of the Dalai Lama and Panchen Lama lineages. Born in Tsongkha (Qinghai). Studied with masters across all major schools, particularly the Sakya scholar Rendawa for prasaṅgika Madhyamaka. Reformed lax monastic discipline, integrated sūtra and tantra into a strict graduated path, and produced the great triology: *Lamrim Chenmo* (Great Treatise on the Stages of the Path), *sNgags rim chen mo* (Great Treatise on Tantra), and *Drang nges legs bshad snying po* (Essence of True Eloquence — definitive vs interpretable meaning). Founded Ganden Monastery (1409) — the seat of the school.
Primary sources: Tsongkhapa's collected works (*gsung 'bum*, searchable on BDRC.io). Chinese translation by Dharma-master Faxun is the standard Sinophone reference.
Invoke: `/master-tsongkhapa`

> ⚠️ Tantric practice steps, empowerment liturgy, generation- and completion-stage details, deity mantras, and channels-and-drops practice are introduced **only at the level of name and historical context — concrete practice instructions are never given**.

### Milarepa (1052-1135) — Tibetan · Kagyu

Spiritual ancestor of the Tibetan Kagyu lineage and the paradigm of the "yogi tradition" (no monastery, mountain retreat, teaching through song). After committing serious harm in his youth through black magic, he sought purification under Marpa the Translator, who put him through severe trials before transmitting the complete Mahāmudrā and Naro Chodruk lineages. He spent decades in Himalayan retreat, surviving on nettles, and taught through extemporaneous **mGur** (songs of realization) — shaping the entire later Tibetan tradition.
Primary sources: BDRC — *The Hundred Thousand Songs of Milarepa* (mGur 'bum, W1KG14334) and *The Life of Milarepa* (rNam thar, W22272).
Invoke: `/master-milarepa`

> ⚠️ Naro Chodruk (Six Yogas), tummo, generation/completion stages and other esoteric practices are introduced **only at the level of name and historical context — concrete practice instructions are never given**. Authentic transmission requires direct empowerment from a qualified teacher.

### Buddhaghosa (5th century) — Theravāda · commentarial summit

The most influential commentator and śāstra master in Theravāda history. Born a brahmin scholar in southern India, he travelled to the Mahāvihāra in Anurādhapura (Sri Lanka) to translate the old Sinhala commentaries (*Sīhaḷa-aṭṭhakathā*) into Pali. To prove his competence, he first composed the *Visuddhimagga* — a 23-chapter encyclopedia of Theravāda meditation and doctrine organized around the threefold training of **sīla, samādhi, paññā**. He then translated the four Nikāya commentaries, the Vinaya commentary *Samantapāsādikā*, and the Abhidhamma commentaries. His framework defines orthodox Theravāda exegesis to this day across Sri Lanka, Burma, Thailand, Cambodia, and Laos.
Primary sources: PTS edition *Visuddhimagga* + four Nikāya *aṭṭhakathā* (Sumaṅgalavilāsinī, Papañcasūdanī, Sāratthappakāsinī, Manorathapūraṇī) + *Samantapāsādikā* (Vinaya) + *Atthasālinī* (Abhidhamma).
Invoke: `/master-buddhaghosa`

### Mahāsi Sayādaw U Sobhana (1904-1982) — Theravāda · Burmese vipassanā

One of the most internationally influential meditation masters of modern Burma. Recognized as a *Pariyatti Sāsanahita* — the highest scriptural qualification in Burmese monasticism — by age 27. Studied four-foundations vipassanā with U Nārada (Mingun Sayadaw) from 1932. Established the **Mahasi Sasana Yeiktha** retreat center in Yangon in 1947, formalizing the **noting method** (rising-falling at the abdomen as primary object) tied to Visuddhimagga's seven purifications and sixteen insight knowledges. Served as *Final Editor* of the Sixth Buddhist Council (1954-1956) — the largest modern revision of the Pali Canon. His lineage profoundly shaped the founders of America's Insight Meditation Society (Goldstein, Salzberg, Kornfield).
Primary sources: *Manual of Insight* (Wisdom Publications, 2016 English ed.), *The Progress of Insight* (BPS Sri Lanka Wheel No. 280), *Practical Vipassanā Meditation Exercises* (Mahasi Sasana Yeiktha).
Invoke: `/master-mahasi-sayadaw`

> ⚠️ **The AI must never confirm any individual's stage of insight or attainment of fruition.** Verification requires face-to-face interview with a qualified teacher. This is the strictest guardrail in this skill — the Mahasi tradition's "fruition is attainable" framing is famous for inducing self-attainment delusions, and the AI is forbidden from playing that role.

### Ajahn Chah Subhaddo (1918-1992) — Theravāda · Thai Forest

One of the most internationally influential masters of the Thai Forest Tradition. Renowned for strict Vinaya observance, four-foundations-of-mindfulness practice, and plain, life-grounded teaching style. His Western disciples (Ajahn Sumedho, Ajahn Pasanno, Ajahn Amaro and others) established Abhayagiri (California), Amaravati (UK), Cittaviveka (UK) and other branch monasteries, carrying the forest tradition to the West. Most-quoted line: *"If you let go a little, you have a little peace; if you let go completely, you have complete peace."*
Primary sources: Pali Canon (SuttaCentral) + authorized English collections — *Food for the Heart*, *A Still Forest Pool*, *Living Dhamma*.
Invoke: `/master-ajahn-chah`

---

## Architecture

```
User request
    |
    v
session-start hook ──> auto-injects master list (5 platforms, unified)
    |
    v
SKILL.md (AgentSkills entry: decision tree + quick reference)
    |
    +-- Pre-built masters --> prebuilt/{slug}/
    |                           +-- SKILL.md          (decision tree + <HARD-GATE>)
    |                           +-- meta.json         (version / lineage / provenance)
    |                           +-- references/       (loaded on demand)
    |                           |   +-- teaching.md
    |                           |   +-- voice.md
    |                           +-- sources/          (offline CBETA passages)
    |                           |   +-- *.md
    |                           +-- tests/
    |                               +-- fidelity.jsonl  (CI dry-run samples)
    |
    +-- Offline toolchain
    |   +-- scripts/validate.py         (frontmatter linter)
    |   +-- scripts/cite.py             (CBETA lookup)
    |   +-- scripts/query.py            (offline semantic search)
    |   +-- scripts/test-fidelity.py    (fidelity runner)
    |   +-- scripts/validate-fidelity.py
    |   +-- bin/cli.mjs                 (NPX installer)
    |
    +-- Custom generation (/create-master, HARD-GATE enforced)
          +-- Step 1-2  prompts/intake.md → tools/sutra_collector.py
          |             └─> FoJin API (KG + semantic search + text)
          +-- Step 3    prompts/{sutra,voice}_analyzer.md → two-stage analysis
          +-- Step 3.5  two-stage independent review ──┬─ prompts/doctrine_reviewer.md
          |                                            └─ prompts/voice_reviewer.md
          +-- Step 4-5  tools/master_builder.py → tools/skill_writer.py
                        └─> tools/verify_sources.py (final pre-write check)

Unified multi-platform manifests:
  .claude-plugin/      → Claude Code    (hooks/run-hook.cmd → session-start)
  .cursor-plugin/      → Cursor         (hooks/hooks-cursor.json)
  .codex/              → Codex CLI      (.codex/INSTALL.md)
  .opencode/           → OpenCode       (referenced from opencode.json)
  gemini-extension.json → Gemini CLI    (auto-loaded with GEMINI.md)
```

---

## Relationship to FoJin

[FoJin](https://fojin.app) is a Buddhist text aggregation platform integrating 503 data sources, 10K+ texts, 678K+ semantic vector embeddings, and a knowledge graph of 31K entities. It covers major corpora including CBETA Chinese Buddhist Canon, SuttaCentral Pali Canon and translations, and 84000 Tibetan Buddhist translations.

Master-skill connects to the FoJin API via `tools/fojin_bridge.py` to enable:

- Knowledge graph entity retrieval (master biography, lineage, school)
- Semantic similarity search (doctrinally relevant sutras)
- Runtime RAG retrieval for grounding answers in real texts
- Source passage extraction with provenance tracking

All citations include traceable FoJin links to ensure transparency of sources.

---

## Sensitivity Boundaries

**Will not:**

- Pass judgment on the relative merits of different schools or traditions
- Provide personal practice diagnoses (karma readings, past lives, etc.)
- Claim supernatural powers or auspicious experiences
- Engage with politically charged religious topics
- Offer medical advice

**Will:**

- Cite source texts faithfully, with FoJin links on every response
- Retrieve real texts via runtime RAG, not relying solely on AI training data
- Acknowledge clearly when a question falls outside scope
- Encourage users to seek out qualified masters and authentic practice

---

## Troubleshooting

**Q: Does it still work when the FoJin API is unreachable?**

Yes. Each prebuilt master ships with `prebuilt/<name>/sources/` — key passages from that master's core canon, stored offline. When FoJin is down, the master degrades to offline mode and declares "currently running on offline passages" in the reply. The `/create-master` pipeline asks the user to switch to manual-input mode when the API fails, so you can paste source text and continue.

**Q: What does a valid CBETA citation look like, and how is it verified?**

Every CBETA citation must carry a `Txxn####` identifier (for example, the Lotus Sutra is `T9n262`). `scripts/validate.py` lints the frontmatter `sources` block; `tools/verify_sources.py` checks every FoJin `text_id` against the live API before writing. Broken links are downgraded to FoJin search URLs — no dead references make it into the final file.

**Q: `npx master-skill install` fails with ENOTEMPTY or a permission error — what now?**

Clean up any leftover `~/.claude/skills/master-<name>/` directories before retrying. For npm-cache weirdness, run `npm cache clean --force` and rerun NPX. Windows users should execute from Git Bash or WSL to avoid cmd.exe path-escaping issues.

**Q: The generated master says things that don't match the historical record — how do I correct it?**

Just tell the master in-chat: "he wouldn't phrase it like that" or "he should sound more stern." The `/create-master` correction mode classifies the fix (doctrinal → appended to `teaching.md`; stylistic → appended to `voice.md`), writes it as a `## Correction` block with timestamp, and bumps the patch version. Correction blocks take priority over analysis-generated content at runtime.

**Q: How do I contribute a new prebuilt master?**

See "Contributing" below. The short version: follow the v0.3 layout under `prebuilt/<name>/`, pass `scripts/validate.py --strict` with zero errors, ship at least 5 fidelity Q&A samples in `tests/fidelity.jsonl`, then open a PR.

---

## Contributing

Contributions are welcome: new prebuilt masters, corrections to source attributions, offline passage additions, or toolchain improvements.

New masters must follow the v0.3 layout: `prebuilt/<name>/` containing SKILL.md (with provenance frontmatter and a decision tree), `references/teaching.md` and `references/voice.md` (loaded on demand), `sources/*.md` (offline CBETA passages), and `tests/fidelity.jsonl` (5+ Q&A fidelity samples). Run `python3 scripts/validate.py --strict` for zero errors, and make sure the CI fidelity dry-run passes before opening a PR.

Before submitting, verify that sources trace back to CBETA, content is faithful to historical documents, and no sectarian bias is introduced.

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
