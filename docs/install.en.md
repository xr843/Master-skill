# Developer installation and usage

> Full per-platform setup, teaching modes, and custom generation. Quick start: [README_EN](../README_EN.md#developer-installation).

---

> 👤 **Just want to try it?** Use [fojin.app/chat](https://fojin.app/chat) in your browser and skip this section entirely.
> 🛠️ **This section is for**: Claude Code / Cursor / Codex CLI / OpenCode / Gemini CLI users who want to invoke `/master-xuanzang`, `/master-huineng`, etc. directly as terminal AgentSkills.

### Installation

**NPX (recommended, no global state)**

`npx master-skill install --all` installs all 20 skills: 15 personas, 4 teaching modes (including the `/master-help` router), and the `create-master` generator. The generator is copied as a self-contained runtime, so it remains usable after the transient npx package directory is removed; reinstall and `update --all` refresh the runtime while preserving user-generated personas under `create-master/masters/`.

```bash
# Install individual public skills
npx master-skill install master-zhiyi
npx master-skill install compare-masters
npx master-skill install create-master

# Install or list the complete 20-skill catalog
npx master-skill install --all
npx master-skill list

# Not sure who to ask? Describe the question and let it route
npx master-skill recommend "念佛怎么念才算老实"
npx master-skill recommend "禅宗从哪开始学"
```

**Not sure which master or teaching mode to use?**

Two entry points share one routing table (`routing.json` at the repo root, plus
each persona's `meta.json` `search_scope.keywords`):

| Entry point | Where |
|-------------|-------|
| `master-skill recommend "<question>"` | Terminal; deterministic scoring, supports `--json` |
| `/master-help` | In-chat; just ask "who should I ask?" |

Resolution short-circuits in order: **learning path → debate → comparison →
single master → plain-language situation → topic pairing.** It names a destination
and stops — the master it routes to answers under its own `citation_contract`
and boundary rules.

The situation layer exists because `search_scope.keywords` are doctrinal
retrieval terms: a beginner does not type 四念处, they type 坐不住 ("can't sit
still"). Every row of the README's 「你的状况」 table is pinned by
`tests/cli.test.mjs` — editing that table without updating the routing data
fails the suite.

```bash
$ master-skill recommend "十六观智是什么"

推荐祖师：
  /master-buddhaghosa  [南传]  命中 十六观智
  /master-mahasi-sayadaw  [南传]  命中 十六观智、观智
```

> Only keywords of length ≥ 2 score. The seven single-character doctrinal atoms
> (空 戒 定 慧 苦 禅 业) fire inside ordinary Chinese — "有空吗" ("are you free?")
> used to route to Madhyamaka — so they are excluded; queries carrying only a bare
> atom fall through to the topic-pairing fallback.

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
for d in prebuilt/master-*/; do ln -sf "$(pwd)/$d" ~/.claude/skills/"$(basename $d)"; done
ln -sf "$(pwd)/prebuilt/compare-masters" ~/.claude/skills/compare-masters
ln -sf "$(pwd)" ~/.claude/skills/create-master
```

**Cursor** — Clone the repo; Cursor auto-detects `.cursor-plugin/plugin.json`.

**OpenCode** — Add to `opencode.json`:

```json
{"plugin": ["master-skill@git+https://github.com/xr843/Master-skill.git"]}
```

**Codex CLI** — See [.codex/INSTALL.md](../.codex/INSTALL.md)

**Gemini CLI** — Auto-discovered via `gemini-extension.json` and `GEMINI.md`.

### Use a Pre-built Master

In any AgentSkills-compatible environment (Claude Code / Cursor / Codex CLI / OpenCode / Gemini CLI):

```
# 印度 (Indian)
/master-nagarjuna      — Nāgārjuna (Indian · Madhyamaka | root of the eight schools)

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

### Teaching Modes (v0.7)

- **`/compare-masters`** — multiple masters answer the same question side-by-side (horizontal, single-turn)
- **`/master-debate`** — masters from different traditions engage in a 4-round adversarial dialectic (claim → rebut → respond → synthesize + remaining disagreements)
- **`/master-curriculum`** — given your target tradition and current level (L0-L3), get a time-sequenced study path (foundation → intermediate → advanced + likely blind spots)

**`/compare-masters` usage examples:**

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
