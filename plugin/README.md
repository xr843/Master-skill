# Master-skill

Master-skill gives Claude sixteen Buddhist teacher personas and four teaching
modes, each grounded in the teacher's own texts and bounded by an explicit
citation contract. Ask Huineng about sudden awakening, Xuanzang about the eight
consciousnesses, Tsongkhapa about the stages of the path, or Ajahn Chah about
letting go, and the answer cites canonical sources (CBETA, BDRC, SuttaCentral,
PTS) instead of paraphrasing from memory. When a question falls outside what
the sources support, the persona says so.

This folder is the plugin as Claude Code installs it. It is generated from the
[Master-skill repository](https://github.com/xr843/Master-skill) by
`scripts/build-plugin-bundle.py`; edit the sources there, not these copies.

## Install

In Claude Code 2.1.275 or later:

```
/plugin install master-skill --marketplace xr843/Master-skill
```

Or from a shell:

```bash
claude plugin marketplace add xr843/Master-skill
claude plugin install master-skill@master-skill
```

## What is included

Twenty-one skills:

- **Personas (16):** `master-nagarjuna`, `master-xuanzang`, `master-kumarajiva`,
  `master-huineng`, `master-zhiyi`, `master-daoxuan`, `master-fazang`,
  `master-yinguang`, `master-ouyi`, `master-xuyun`, `master-atisha`,
  `master-tsongkhapa`, `master-milarepa`, `master-buddhaghosa`,
  `master-mahasi-sayadaw`, `master-ajahn-chah`. Each ships its source excerpts
  and teaching notes, so it answers offline.
- **Teaching modes (4):** `compare-masters` (several traditions answer one
  question side by side), `master-debate` (a multi-round dialectic between two
  masters), `master-curriculum` (a staged study path within one tradition) and
  `master-help` (start here if you are unsure whom to ask).
- **Generator (1):** `create-master` drafts a new persona from the FoJin
  Buddhist knowledge graph and checks its citations before it is used.

Invoke a skill by name, for example `/master-huineng`, or simply ask a question
about a tradition and Claude will pick the matching persona.

## What it runs and what it contacts

- **SessionStart hook.** One `echo` of a fixed sentence that tells Claude the
  persona skills are available and to suggest `/master-help` when the user is
  unsure whom to ask. It reads nothing, writes nothing and contacts nothing.
- **Personas and teaching modes** answer from the files inside this plugin
  first. `scripts/cite.py` and `scripts/query.py` search the bundled source
  excerpts locally (`query.py` needs the `opencc` Python package).
- **Optional live lookup.** When the bundled excerpts do not cover a question,
  a persona's instructions tell Claude it may look the passage up in FoJin's
  public, read-only API under `https://fojin.app/api/` (full-text and semantic
  search, text lookup, and — in a few skills — the dictionary and
  knowledge-graph endpoints), using
  your host's normal web or shell tool — so your usual tool-permission prompt
  applies. Only the search terms for that passage are sent; no conversation
  content, personal data or credentials. If FoJin is unreachable the persona
  says so and answers from the bundled excerpts. Answers may also include
  links to fojin.app, CBETA or SuttaCentral for the reader to follow.
- **`create-master` only**, and only when you run it, uses Python tools in
  `skills/create-master/tools/` that send the master name and search keywords
  you give it to these public, read-only APIs: the FoJin REST API
  (`https://fojin.app`, overridable with `FOJIN_URL`), the CBETA API
  (`https://cbdata.dila.edu.tw`), SuttaCentral (`https://suttacentral.net`),
  BDRC (`https://ldspdi.bdrc.io`), and two public text mirrors
  (`raw.githubusercontent.com/daizhige-org`, `bookgb.bfnn.org`) used to verify
  quotations. No credentials, personal data or conversation content are sent,
  and nothing is collected by the author. The tools need `requests`, `pyyaml`
  and `pypinyin`; `tools/check_deps.py` tells you how to install them and never
  installs anything itself. Generated personas are written under
  `skills/create-master/masters/` on your machine.

The full privacy policy is [`PRIVACY.md`](https://github.com/xr843/Master-skill/blob/main/PRIVACY.md)
(also in this folder): the plugin collects nothing, and the only data that
leaves your machine is listed above.

## Scope and limits

This content is generated from historical Buddhist literature for study and
reference. It is not a substitute for a living teacher. See `ETHICS.md` in the
`create-master` skill for the source and attribution policy.

## License

Code (scripts, tools, hooks) is MIT. Original persona and teaching-mode content
is CC BY-NC-SA 4.0; prompt templates are CC BY 4.0. Third-party source excerpts
keep their own rights. Full terms are in `LICENSE`.

---

**中文简介：** Master-skill 为 Claude 提供 16 位佛教祖师人设与 4 种教学模式（对比、辩论、
学修次第、导航），每位祖师都依据自己的典籍作答并标注 CBETA / BDRC / SuttaCentral 出处，
超出文献支持范围时明说不知。`create-master` 可从 FoJin 知识图谱生成新的祖师人设。
本文件夹由仓库脚本自动生成，请修改仓库中的源文件。
