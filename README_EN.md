<h1 align="center">Master-skill</h1>

<p align="center">
  <em>"All conditioned phenomena<br>
  Are like a dream, an illusion, a bubble, a shadow,<br>
  Like dew, or a flash of lightning;<br>
  Thus should they be contemplated."</em><br>
  <sub>— Diamond Sūtra (Vajracchedikā Prajñāpāramitā Sūtra)</sub>
</p>

<p align="center">
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
  <strong>AI learning companions modeled after historical Chinese Buddhist masters</strong><br>
  8 pre-built Chinese Buddhist masters · Real FoJin text citations · AgentSkills Standard
</p>

<p align="center">
  <a href="#seriousness-statement">Statement</a> ·
  <a href="#features">Features</a> ·
  <a href="#quick-start">Install</a> ·
  <a href="#pre-built-masters">Masters</a> ·
  <a href="#relationship-to-fojin">FoJin</a> ·
  <a href="README.md">中文</a>
</p>

---

> **v0.2 Update**: New `/compare-masters` command for multi-master comparison; per-master RAG queries with tradition-specific terminology for precise FoJin text_id citations.

---

An AgentSkills-standard generator for AI personas based on historical Buddhist masters, powered by [FoJin](https://fojin.app) — a Buddhist text aggregation platform.

---

## Seriousness Statement

This project is built out of respect for Buddhist traditions. All content is generated faithfully from historical documents. It makes no doctrinal judgments and claims no sectarian authority. Generated content is intended for study and reference only. For formal practice guidance, please seek out a qualified master and rely on genuine, living instruction.

---

## Online Demo

No installation required — try all pre-built masters directly in your browser:

**[fojin.app/chat](https://fojin.app/chat)** — Open the AI Q&A page, select a master from the "法师模式" dropdown (bottom-left), and start chatting.

---

## Features

- **8 pre-built Chinese Buddhist masters**: across Yogacara, Madhyamaka, Chan, Tiantai, Huayan, Pure Land, and cross-tradition — ready to use out of the box
- **FoJin data bridge**: Connected to [fojin.app](https://fojin.app) with 503 data sources, 10K+ texts, 678K+ semantic embeddings, and a 31K-entity knowledge graph
- **Runtime RAG retrieval**: Answers grounded in real Buddhist texts via FoJin semantic search, not just LLM training data
- **AgentSkills standard**: Compliant with the AgentSkills specification; can be invoked as a sub-skill by other agents
- **Dual-mode output**: Each master generates both `teaching.md` (doctrinal system) and `voice.md` (teaching style)
- **Incremental evolution**: Existing masters can be enhanced by appending new source texts via incremental merging
- **Version management**: Built-in versioning with timestamps, supporting rollback to any prior version

---

## Quick Start

### Installation

**NPX (recommended)**

```bash
npx master-skill install --all    # Install all 8 masters
npx master-skill list             # List available masters
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

In any AgentSkills-compatible environment (Claude Code / Codex CLI / OpenClaw):

```
/xuanzang       — Master Xuanzang (Yogacara)
/kumarajiva     — Kumarajiva (Madhyamaka / Sanlun)
/huineng        — Master Huineng (Chan, Sixth Patriarch)
/zhiyi          — Master Zhiyi (Tiantai)
/fazang         — Master Fazang (Huayan)
/yinguang       — Master Yinguang (Pure Land)
/ouyi           — Master Ouyi (Tiantai / Pure Land, cross-tradition)
/xuyun          — Master Xuyun (Chan, Five Houses)
```

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
Invoke: `/xuanzang`

### Kumarajiva (344-413)

One of the four great translators of Chinese Buddhism. Born in Kucha, translated in Chang'an. His translations are celebrated for literary elegance — the Lotus Sutra, Diamond Sutra, Vimalakirti Sutra, and Mulamadhyamakakarika remain the most widely used versions today. Established the foundation of the Sanlun (Madhyamaka) school in China.
Primary sources: CBETA — Lotus Sutra, Diamond Sutra, Vimalakirti Sutra, Mulamadhyamakakarika, Mahaprajnaparamita-sastra.
Invoke: `/kumarajiva`

### Master Huineng (638-713)

The Sixth Patriarch of Chan Buddhism, founder of the Southern School. An illiterate woodcutter who attained enlightenment upon hearing the Diamond Sutra. His Platform Sutra is the only Chinese-authored text honored with the title "sutra." Advocated "directly pointing to the mind, seeing one's nature to become Buddha."
Primary sources: CBETA — Platform Sutra (T48n2008).
Invoke: `/huineng`

### Master Zhiyi (538-597)

Founder of the Tiantai school, honored as "the Little Shakyamuni of the East." Established the first comprehensive doctrinal classification system in Chinese Buddhism (Five Periods, Eight Teachings). Authored the Three Great Works of Tiantai. Core teachings: three thousand realms in a single thought-moment, perfect interfusion of the three truths, dual cultivation of samatha and vipasyana.
Primary sources: CBETA — Mohe Zhiguan (T46n1911), Fahua Xuanyi (T33n1718).
Invoke: `/zhiyi`

### Master Fazang (643-712)

Third Patriarch and true systematizer of the Huayan school. National Preceptor under Empress Wu Zetian. Used the Golden Lion treatise to explain Huayan philosophy. Core teachings: dharmadhatu dependent origination, four dharma-realms, ten mysterious gates, six characteristics in perfect harmony.
Primary sources: CBETA — Huayan Jing Tanxuan Ji (T35n1733), Huayan Wujiao Zhang (T45n1866).
Invoke: `/fazang`

### Master Yinguang (1861-1940)

13th Patriarch of the Chinese Pure Land school. Central figure in the modern Pure Land revival. His writing is sincere and straightforward; he guided countless practitioners through correspondence, collected in the three volumes of the Yinguang Fashi Wenchao.
Primary sources: CBETA — Wenchao volumes and the three Pure Land sutras.
Invoke: `/yinguang`

### Master Ouyi (1599-1655)

One of the Four Great Masters of Late Ming Buddhism, 9th Patriarch of Pure Land. His motto: "Doctrine follows Tiantai, practice returns to Pure Land." The most important cross-tradition synthesizer in Chinese Buddhist history. His commentary on the Amitabha Sutra was praised by Master Yinguang as unsurpassable.
Primary sources: CBETA — Amituo Jing Yaojie (T37n1762), Jiaoguan Gangzong.
Invoke: `/ouyi`

### Master Xuyun (1840-1959)

Modern Chan patriarch who lived to 119 years. Unprecedented in Buddhist history for holding dharma transmission in all five houses of Chan (Linji, Caodong, Guiyang, Yunmen, Fayan). Restored six major ancestral monasteries. Advocated hua-tou investigation, honest practice, and harmonizing Chan with Pure Land.
Primary sources: CBETA — Shurangama Sutra, Diamond Sutra, Platform Sutra.
Invoke: `/xuyun`

---

## Architecture

```
User request
    |
    v
SKILL.md (AgentSkills entry point)
    |
    +-- Pre-built masters ----------------> prebuilt/{slug}/
    |                                        +-- SKILL.md
    |                                        +-- teaching.md
    |                                        +-- voice.md
    |                                        +-- meta.json
    |
    +-- Custom generation
          |
          +-- prompts/intake.md          (information intake)
          |
          +-- tools/sutra_collector.py
          |       |
          |       +--> FoJin API ---> knowledge graph + semantic search + text
          |
          +-- prompts/sutra_analyzer.md  (doctrinal analysis)
          +-- prompts/voice_analyzer.md  (style analysis)
          +-- prompts/teaching_builder.md
          +-- prompts/voice_builder.md
          |
          +-- tools/master_builder.py    (persona construction)
          +-- tools/skill_writer.py      (file writing)
          +-- tools/version_manager.py   (version management)
                |
                v
          masters/{slug}/
              +-- SKILL.md
              +-- teaching.md
              +-- voice.md
              +-- meta.json
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

## Contributing

Contributions are welcome: new pre-built masters (follow the format in `prebuilt/`), corrections to source attributions, or improvements to the toolchain.

Before submitting, please verify: sources are traceable, content is faithful to historical documents, and no sectarian bias is introduced.

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
