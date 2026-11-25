# Capability skills — reusable Buddhist building blocks

The personas in `prebuilt/` answer *as* a master. The skills here answer *about* the texts: small, source-grounded tools that any agent can call, in Chinese or English, with a fixed JSON contract.

| skill | question it answers | sources |
|---|---|---|
| [`buddhist-quote-trace`](buddhist-quote-trace/SKILL.md) | Is this sentence really in the canon? Where? Is it a known fake? | CBETA via [FoJin](https://fojin.app), [SuttaCentral](https://suttacentral.net), curated misattribution list |
| [`buddhist-citation`](buddhist-citation/SKILL.md) | What is `T48n2008` / `SN 22.59` / `W22272`? Does it exist? Does it match this title? | CBETA, SuttaCentral, BDRC, 84000 |

Both are Python 3.9+ standard library only, and need network access to those services.

## Use them

**As Agent Skills** (Claude Code, Codex, Gemini CLI, OpenCode, Cursor):

```bash
npx master-skill install buddhist-quote-trace buddhist-citation
```

or copy a folder from `capabilities/` into your agent's skills directory — each folder is self-contained.

**As an MCP server** (any MCP client):

```json
{"mcpServers": {"master-skill": {"command": "python3", "args": ["/path/to/Master-skill/mcp/master_skill_mcp.py"]}}}
```

Tools: `trace_quotes` (`text` or `sentences`, optional `lang`) and `resolve_citation` (`citation`, optional `title`).

**As a command-line tool**:

```bash
python3 capabilities/buddhist-quote-trace/scripts/qtrace.py "一切有为法，如梦幻泡影。Peace comes from within."
python3 capabilities/buddhist-citation/scripts/bcite.py T2008 "SN 22.59" --title 坛经
```

## Contract

`trace_quotes` gives each sentence one verdict — `found`, `close`, `partial`, `candidate`, `not_found`, `known_misattribution`, `unverifiable` — with sources and links. Two rules a consumer must keep:

- **`unverifiable` is not `not_found`.** A network failure, a rate limit or an out-of-scope text (e.g. Mahayana sutras in English) is never reported as "not in the canon".
- **`not_found` is not "fake".** It means the searched collections do not contain the words; paraphrases and uncollected texts exist.

For Chinese, `found` comes with `source_class`: `sutra`, or `commentary` / `school` / `later` / `history` when the words are in commentaries, Chan records or later writings rather than a sutra ("放下屠刀，立地成佛" is `found` / `later`).

`resolve_citation` returns `exists` as `true`, `false` or `null` (not checked), plus `canonical`, `title`, `url` and, when a title was given, `title_matches`.

## How good is it?

`scripts/eval-capabilities.py` runs both skills against the bilingual sets in `eval/capabilities/` and writes `eval/reports/capabilities-<commit>.json`. Acceptance: of the sentences judged `found`, at least 98% must really be canon text, and no known fake may be judged `found`. A weekly GitHub Action (`capabilities-live.yml`) asks the live services a few fixed questions so an API change is noticed.

## 中文

`prebuilt/` 里的祖师是「以祖师口吻回答」；这里的能力 skill 是「核对文本本身」：一句话是否出自藏经、出自哪部哪卷、是否为已知伪托；一个经号是否存在、是哪部书、和所称书名对不对得上。任何 agent 都可以调用，中英文均可，输出格式固定（JSON）。安装方式同上：`npx master-skill install buddhist-quote-trace buddhist-citation`，或配置 MCP。
