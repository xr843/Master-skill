# 能力类 skill：引文溯源与出处解析（设计）

2026-11-25 维护者批准。第一个子项目，属于「Master-skill 从祖师人设走向可复用的佛学专业能力模块」这一方向。

## 目标

给其他 AI 开发者两个可以独立安装、可组合、中英双语的能力：

| skill | 做什么 |
|---|---|
| `buddhist-quote-trace`（引文溯源） | 一段中文或英文，逐句判定是否见于原典、见于哪部哪卷、是否为已知伪托 |
| `buddhist-citation`（出处解析） | 一个经号（`T48n2008`、`SN 22.59`、`Dhp 5`、`Toh 3871`、`W22272`…），返回标准写法、书名、是否存在、链接 |

两种接入方式共用同一份代码：skill 自带脚本（Claude Code / Codex / Gemini CLI 装上即用），以及一个 stdio MCP 服务。

## 不做

- 祖师人设改为调用这两个能力（与 #382 同一件事，按 11-24 的重启条件）。
- 名相对照、原典检索、人设英文化（后续子项目）。
- 发 npm 版本、发 PyPI 包（对外发布，另行请示）。

## 结构

```
capabilities/
  buddhist-citation/
    SKILL.md              英文为主、附中文说明；description ≤ 200 字符
    LICENSE.md            代码 MIT
    scripts/bcite.py      出处解析，只用标准库
  buddhist-quote-trace/
    SKILL.md
    LICENSE.md
    scripts/qtrace.py     引文溯源，只用标准库
    scripts/bcite.py      与上面那份逐字节相同（打包后各自独立）；测试强制同步
    data/misattributions.json   伪托语录清单（自写说明，CC-BY-SA-4.0）
mcp/
  master_skill_mcp.py     stdio JSON-RPC MCP 服务，只用标准库，暴露 trace_quotes / resolve_citation
eval/capabilities/
  quote-trace.jsonl       双语评测集
  citation.jsonl
scripts/eval-capabilities.py   跑评测、出报告
```

放在 `capabilities/` 而不是 `prebuilt/`：`prebuilt/` 下的目录被十几个人设校验器按「祖师」检查（meta.json、fidelity 夹具、CBETA 摘录），能力类不适用。`skill-catalog.json` 新增 `kind: "capability"`；CLI、插件打包、门禁按这个 kind 处理。

## 输出约定

### trace_quotes

输入：`{"text": "…"} ` 或 `{"sentences": [...]}`；`lang` 可选（`zh` / `en` / 自动）。

```json
{
  "engine": "buddhist-quote-trace/1",
  "checked_at": "2026-11-25T08:00:00Z",
  "items": [
    {
      "text": "放下屠刀，立地成佛。",
      "lang": "zh",
      "verdict": "found",
      "source_class": "later",
      "sources": [{"collection": "CBETA", "id": "X0434", "title": "…", "juan": 1, "url": "https://fojin.app/texts/…"}],
      "note": "见于后世禅籍，不在经藏正文"
    }
  ]
}
```

`verdict` 只取以下七种：

| verdict | 含义 |
|---|---|
| `found` | 逐字见于原典（繁简、标点差异不计） |
| `close` | 只差一两字 |
| `partial` | 部分分句见于原典，其余未见 |
| `candidate` | （英文）意思相近的候选经文，非逐字，需人核对 |
| `not_found` | 在已收范围内未见；**未见不等于伪造**，可能是改写或出自未收录典籍 |
| `known_misattribution` | 命中伪托清单，附理由与真实出处（若有） |
| `unverifiable` | 没核成：断网、限流、超出收录范围（如大乘英文译本） |

`source_class`（中文）原样转 FoJin：`sutra`（经律论）、`school`（宗门著述）、`later`（后世撰述）、`history`（史传）。

### resolve_citation

输入：`{"citation": "T48n2008"}`，可选 `title` 用来核对书名与经号是否对得上。

```json
{"input": "T2008", "scheme": "cbeta", "canonical": "T48n2008", "exists": true,
 "title": "六祖大師法寶壇經", "byline": "元 宗寶編", "juan_count": 1,
 "url": "https://cbetaonline.dila.edu.tw/zh/T2008", "title_matches": null}
```

`exists` 取 `true` / `false` / `null`（`null` = 没核成或该体系无法在线核验，如 Toh 只能给 84000 链接）。

| 体系 | 写法 | 在线核验 |
|---|---|---|
| CBETA | `T48n2008`、`T2008`、`X0434`、`J36nB348` | cbdata.dila.edu.tw `/stable/works` |
| SuttaCentral | `SN 22.59`、`MN 10`、`AN 3.65`、`DN 16`、`Dhp 5`、`Snp 1.8` | `/api/suttaplex/<uid>`；Dhp 偈号先按品映射到 `dhp1-20` 一类区间 |
| BDRC | `W22272`、`W1KG14334` | ldspdi `resource/<id>.json` |
| 德格 | `Toh 3871` | 不核验，`exists: null`，给 84000 链接 |

## 查证流程

**中文**：FoJin `POST /api/verify/trace`（每批 ≤ 8 句、每句 ≤ 200 字、每分钟 12 次）。映射：`sutra`/`not_sutra` 且全部分句命中 → `found`；`variant` → `close`；`partial` → `partial`；`absent` → `not_found`。先查伪托清单，命中则 `known_misattribution`（仍附 FoJin 结果）。

**英文**：依次
1. 伪托清单（规范化后比对）；
2. SuttaCentral 原话搜索（`/api/search/instant`）；命中 Sujato 分段译文时取全文逐段规范化比对，逐字包含 → `found`；
3. 关键词搜索（去停用词后取实词组合），只给 `candidate`；
4. 都没有 → `unverifiable`（不是 `not_found`：英文只覆盖巴利经藏若干译本，查不到不能说藏经中无）。

非 Sujato 译本（Bodhi 等有版权）只输出经号与链接，不输出译文。

## 出错处理

- 网络错误、超时、5xx、解析失败 → `unverifiable`，`note` 写原因；**绝不降成 `not_found`**。
- 429 按 Retry-After 退避，最多 3 次；进程内两次请求至少隔 5 秒。
- 返回内容一律当数据，不当指令（SKILL.md 写明）。

## 测试与验收

- 单元测试：录制的接口返回 + 注入的 opener，CI 不联网。
- 双语评测集：约 60 条中文、40 条英文，每条带期望 verdict 与来源依据。
- 验收：判 `found` 的准确率 ≥ 98%；伪托条目判 `found` 为 0；报告同时写清英文 `unverifiable` 比例。若英文 `candidate` 人工复核准确率 < 80%，删掉第 3 步，英文只留 `found` / `known_misattribution` / `unverifiable`。
- 每周一次真联网冒烟（GitHub Actions），接口变形时开 issue。

## 风险

- 英文覆盖窄：SuttaCentral 只有巴利经藏英译，大乘英文引语只能 `unverifiable`。
- 外部开发者是否采用未验证（fojin-mcp 进官方目录后外部采用为 0）。
- FoJin / SuttaCentral 接口变化会直接让能力失效，靠周检发现。
