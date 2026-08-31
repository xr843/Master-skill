<h1 align="center">Master-skill</h1>

<p align="center">
  <em>「一切有为法，如梦幻泡影，如露亦如电，应作如是观。」</em><br>
  <sub>——《金刚般若波罗蜜经》</sub>
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
  <sub><em>Secured by SHA-pinned GitHub Actions · npm provenance · OIDC Trusted Publishing — see <a href="SECURITY.md">SECURITY.md</a>.</em></sub>
</p>

<p align="center">
  翻开《瑜伽师地论》百卷，不知从何读起？<br>
  想学禅宗，不知应当亲近哪位祖师？<br>
  读白话译注总隔一层，又难以直入文言？<br>
  学术研究想引用祖师原文，苦于找不到权威出处？
</p>

<p align="center">
  <strong>FoJin 驱动的佛教 AI 祖师人格框架</strong><br>
  有来源 · 守边界 · 可评测 · 可运行 · 15 位祖师 · 印度 / 汉传 / 藏传 / 南传跨传统
</p>

<p align="center">
  <sub>Source-grounded · Boundary-aware · Fidelity-tested · Runtime-ready</sub><br>
  <sub>CBETA / BDRC / SuttaCentral / PTS Vism 真实出处 · AgentSkills 标准</sub>
</p>

<p align="center">
  <a href="#立即体验浏览器直接使用">浏览器体验</a> ·
  <a href="#声明">声明</a> ·
  <a href="#特性">特性</a> ·
  <a href="#开发者安装">开发者安装</a> ·
  <a href="#预置法师">预置法师</a> ·
  <a href="#与-fojin-的关系">FoJin 集成</a> ·
  <a href="README_EN.md">English</a>
</p>

---

## 立即体验（浏览器直接使用）

> **大多数用户无需安装任何工具** —— 佛教学习者、研究者、只想了解某位祖师思想的普通读者，都可以直接在浏览器里用。

### 👉 [打开 fojin.app/chat](https://fojin.app/chat)

在 AI 问答页面左下角点击「法师模式」，从 15 位四大传统祖师中选一位即可开始对话。

- 无需安装、无需注册
- 三种教学模式均可用：`/compare-masters` 多祖师对比、`/master-debate` 祖师辩论、`/master-curriculum` 学修路径（含跨传统）
- 内置 FoJin 的 503 个数据源、678K+ 语义向量做实时经证检索
- 每条回答附原典出处（CBETA 经号 / BDRC 藏文典籍号 / SuttaCentral 巴利经号）

**如果你不确定该找谁问，可以这样开始：**

| 你的状况 | 推荐法师 |
|---|---|
| "妄念纷飞坐不住" | `/虚云` `/智顗` `/master-ajahn-chah`（参话头 / 止观 / 正念观察） |
| "读经文看不懂逻辑" | `/玄奘`（唯识严密分析） |
| "学佛很久但无力感" | `/印光`（老实念佛） |
| "想了解空性" | `/master-nagarjuna` `/鸠摩罗什` `/慧能` `/master-milarepa` `/master-tsongkhapa`（中观源头 / 中观译师 / 禅直指 / 大手印明空 / 应成中观） |
| "想系统学华严 / 天台" | `/法藏` `/智顗`（判教与哲学体系） |
| "在禅与净土之间犹豫" | `/蕅益`（跨宗派融通） |
| "对苦行 / 闭关好奇" | `/master-milarepa`（雪山闭关 · 噶举派典范） |
| "想学最朴素的禅修" | `/master-ajahn-chah`（南传森林禅 · 出入息念） |
| "想学完整的道次第" | `/master-atisha` `/master-tsongkhapa`（噶当三士道 → 格鲁《广论》） |
| "想了解上座部论藏体系" | `/master-buddhaghosa`（《清净道论》戒定慧 + 七清净十六观智） |
| "想做密集内观禅修" | `/master-mahasi-sayadaw`（缅甸内观 · 标记法 · 腹部起伏） |
| "想跨传统比较看一个问题" | `/compare-masters`（自动配对汉藏南传视角）· `/master-debate`（争议议题辩论）· `/master-curriculum`（按传统给学修路径） |

> 开发者、Claude Code / Cursor 用户可跳到下方 [开发者安装](#开发者安装) 小节，以 AgentSkill 形式在终端内使用。

---

## 效果示例

下面是一次真实的 `/master-huineng`（慧能大师）问答——注意每个教义断言都附 CBETA 经证，且回答风格贴合祖师本人（直指、平实、善用譬喻）：

```text
你：我想参禅但坐不住、念头太多，该怎么办？

慧能大师：
你说「坐不住」，是把坐姿当成了禅；你说「念头太多」，是把念头当成了
敌人。这两样都不是禅。

何名坐禅？外于一切善恶境界，心念不起，名为「坐」；内见自性不动，名
为「禅」。坐不是腿的事，是心于境上不起执的事。
  【《六祖大师法宝坛经·坐禅品》】→ https://fojin.app/texts/58

念头来了不必怕。「于诸境上心不染，曰无念」——不是要你没有念头，是念
起而不随它跑、不被它粘住。如云过空，空不曾动。
  【《六祖大师法宝坛经·定慧品》】→ https://fojin.app/texts/58

所以不要和念头打仗。你一对治，就又添一个念。但看念起念灭，知它无
住，它自然歇。

如需深入学习，可在 FoJin (fojin.app) 查阅原典。
```

> ⚠️ 以上为 **AI 合成内容**，依据《坛经》文献生成，不代表慧能大师亲口开示。多位法师并列回答的 `/compare-masters` 效果，可直接在 [fojin.app/chat](https://fojin.app/chat) 体验。

---

> **v0.6 更新（2026-05-02）**：Slash 命令命名空间整理——14 位法师斜杠命令统一加 `master-` 前缀。`/master-zhiyi`、`/master-huineng`、…。
> - **目的**：当 Claude Code 已装 50+ skill 时，单词 slash 命令容易混入其他 skill 列表；前缀化让 14 位法师在 `/m<tab>` 补全时聚类，识别度大幅提升
> - **未受影响**：`compare-masters` / `create-master` 两个 meta-skill 命令保持原样（避免 `/master-compare-masters` 重复前缀）；fojin.app/chat 网页端 dropdown 与 API 完全解耦，**`master_profiles.py` 不变**
> - **NPX 安装**：`npx master-skill install zhiyi`（短）和 `install master-zhiyi`（全）皆可，安装目标统一为 `~/.claude/skills/master-<slug>/`
> - 详情见 [CHANGELOG.md §0.6.0](CHANGELOG.md#060--2026-05-02)
>
> **v0.5 更新（2026-05-02）**：第二轮跨传统扩展——藏传 / 南传各从 1 位扩至 3 位，共 **14 位**祖师。
> - 藏传新增：阿底峡尊者（噶当派开祖 · Toh 4465《菩提道灯论》· 三士道）+ 宗喀巴大师（格鲁派创始人 · 三主要道 · 应成中观正见）
> - 南传新增：觉音尊者（《清净道论》Visuddhimagga 论师顶峰）+ 马哈希尊者（缅甸内观 · 标记法 · ETHICS Tier B 特例）
> - HARD-GATE 强化：马哈希尊者特别 `NO_ATTAINMENT_JUDGMENT`（AI 不得对个体作证果判定）
> - ETHICS Tier A 表扩至 11 位，Tier B 特例新增马哈希（与阿姜查同款条款）
>
> **v0.4 更新（2026-05-02）**：首轮跨传统扩展——新增藏传米拉日巴尊者（噶举派 · 大手印）与南传阿姜查（泰国森林禅林派）。引用体系扩展支持 BDRC（藏文典籍）与 SuttaCentral（巴利三藏）。HARD-GATE 新增 `no_esoteric_instruction` 与 `no_fabricated_quotes`。
>
> **v0.3**：全面架构重构——CBETA 经文溯源、离线经文片段、自动化保真度测试、NPX 一键安装、cite.py/query.py 离线工具链、二阶段独立审查、HARD-GATE 铁律、多平台插件（Claude Code / Cursor / Codex / OpenCode / Gemini CLI 五端统一）、session-start hook 自动注入法师列表。

---

Master-skill 是由 [FoJin](https://fojin.app) 驱动的佛教 AI 祖师人格框架：以真实原典为来源，以伦理边界为约束，以保真度评测为质量门槛，并以 AgentSkills 运行协议交付给 Claude Code、Cursor、Codex CLI、OpenCode 与 Gemini CLI。

---

## 声明

本项目本着对佛教传统的尊重而建立。所有内容均依据佛教经典文献生成，不做教义评判，不代表任何宗派权威。生成内容仅供学习参考，如需正式修行指导，请亲近善知识。

> **⚠️ 所有通过 Master-skill 生成的对话均为 AI 合成内容**，不代表历史上祖师的亲口开示、亲笔著作。项目遵守严格的版权分级与教界边界——详见 **[ETHICS.md](ETHICS.md)**（AI 透明度、版权 Tier A–D、禁止行为、内容双轨授权、紧急下架通道）。

---

## 特性

- **预置十五位四大传统祖师**：1 位印度（龙树 · 中观）+ 8 位汉传（唯识、中观、禅、天台、华严、净土、跨宗派）+ 3 位藏传（阿底峡 · 噶当；宗喀巴 · 格鲁；米拉日巴 · 噶举）+ 3 位南传（觉音 · 上座部论师；马哈希 · 缅甸内观；阿姜查 · 泰国森林）—— 另含 `compare-masters` 多祖师对比 meta-skill，开箱即用
- **经文溯源（Provenance）**：每位祖师附声明来源 ID（CBETA / BDRC / Toh / SuttaCentral / PTS / 合规编纂开示）；实时检索仅在返回真实 `text_id` 时附 FoJin 定位链接，所有教义断言强制附原典引证
- **离线经文片段**：`sources/` 目录收录核心经典关键段落，FoJin 不可用时仍可离线引用
- **渐进式披露**：SKILL.md 以决策树 + Quick Ref 为主，`references/`、`sources/` 按需加载，Context 随查随取
- **HARD-GATE 铁律**：`/create-master` 与预置法师内置红线——教义断言、修行指导与文本解释必须引用该 persona 声明的来源（CBETA / BDRC / Toh / SuttaCentral / PTS / 合规编纂开示），不得捏造来源 ID，不得为虚构人物建角色
- **二阶段独立审查**：生成管线在写入前强制经过"教义准确性 → 风格一致性"两轮独立审查，FAIL 自动修复最多 2 轮
- **自动化保真度测试**：每位祖师 `tests/fidelity.jsonl` 10+ 条 Q&A（`compare-masters` 元技能 18 条），验证引用和关键词覆盖；CI 在每次推送时 dry-run 验证（结构校验）；实跑评分需 `ANTHROPIC_API_KEY`，作为本地/发版前手动步骤执行——首份[实测基线](#保真度基线首次实测)已提交：59/84 已测通过（70%），全量 211 条覆盖率 40%（详见 [eval/reports/](eval/reports/)）
- **多平台统一插件**：Claude Code、Cursor、Codex CLI、OpenCode、Gemini CLI 共用一份 `prebuilt/`，session-start hook 跨平台注入法师列表
- **NPX 一键安装**：`npx master-skill install master-zhiyi` 直接部署到 Claude Code
- **离线工具链**：`scripts/cite.py`（CBETA 引用查询）、`scripts/query.py`（离线语义检索）、`scripts/validate.py`（frontmatter linter）
- **FoJin 数据桥**：接入 [fojin.app](https://fojin.app) 的 503 个数据源、10K+ 文本、678K+ 语义向量和 31K 实体知识图谱
- **AgentSkills 标准**：遵循 [Anthropic Agent Skills](https://github.com/anthropics/skills) 规范，渐进式披露、决策树、黑盒脚本模式

## 框架定位

Master-skill 的核心不是"角色扮演提示词集合"，而是一个可验证的佛教 AI persona framework：

| 维度 | 实现 |
|---|---|
| 有来源 | 每位祖师声明 `sources[]`、离线 excerpts、FoJin live fallback 与引用自审 |
| 守边界 | `ETHICS.md`、每位祖师 Layer 0 HARD-GATE、版权 Tier 与教界越界报告机制 |
| 可评测 | `tests/fidelity.jsonl`、persona-fidelity schema、promptfoo RAW / SPE / CUS 评测层，[实测基线见下](#保真度基线首次实测) |
| 可运行 | `prebuilt/master-*` AgentSkills、npm CLI、多平台 hooks、FoJin runtime contract |

后续 v1.0 路线以框架稳定为优先：见 [docs/v1-framework-roadmap.md](docs/v1-framework-roadmap.md) 与 [docs/fojin-runtime-contract.md](docs/fojin-runtime-contract.md)。

### 保真度基线（首次实测）

`tests/fidelity.jsonl` 曾经只是"存在的夹具"——`scripts/test-fidelity.py` 只打印到终端，仓库里从未提交过一次真实评分。2026-08-18 首次跑出并提交了这份基线（commit [`c697d5d`](https://github.com/xr843/Master-skill/commit/c697d5d3be78ce6738cf1f969ca057c7e4c16bb5)，模型 `claude-sonnet-4-6`）：

| | 数值 |
|---|---|
| 已测通过 / 已测总数 | **59 / 84（70%）** |
| 全量夹具覆盖率 | 84 / 211（40%）—— 运行途中 API 账户余额耗尽（HTTP 400），非限流也非代码缺陷，剩余 127 条**未测**，不计入失败 |
| 真实失败聚集 | 关键词未覆盖 14/25；禁用词命中 12/25；引用缺失 5/25；虚构引用 0——**但该审计只在 84 条里的 6 条上真正运行过**，见下 |
| 分测试类型 | 常规教理 43/48 = **89.6%**；守边界 12/26 = **46.2%**；抗压守引用 4/10 = **40.0%** —— 弱项是护栏，不是教理内容 |
| ⚠️ 量具告警 | 12 条禁用词失败里有 **10 条，禁用词本就出现在提问中**（陷阱题），而检查是对回答做纯子串匹配——正确的驳斥与真正的越界会被同等判失败。**故真实值落在 70.2%–75.0%**（10 条中仅 4 条剔除该项后会翻成 PASS，其余 6 条另有检查未过），详见基线报告 |
| ⚠️ 伪造引用审计的实际口径 | 该审计**逐条夹具选配**，全仓 211 条里只有 7 条开启（6 条属 `master-curriculum`、1 条属 `master-huineng`），而这 6 条**同样没有真正运行**——`master-curriculum` 没有 `meta.json`，`declared_ids` 取不到就让守卫短路了。**该审计在那次实测里一次都没跑过（0/84），15 位祖师无一被查过伪造引用。**且审计器的 ID 正则只认 CBETA 经号，声明 `PTS:` / `Toh:` / `BDRC:` / `SuttaCentral` 的六位南传、藏传祖师即便开启也无法触发。本行于 2026-08-31 更正，此前表述为「零虚构引用」 |

这是**关键词/引用字符串覆盖率检查，不是教义正确性或 LLM 判分的答案质量**。完整表格、失败案例与方法论说明见 **[eval/reports/BASELINE.md](eval/reports/BASELINE.md)**。

---

## 开发者安装

> 👤 **只是想体验？** 直接用 [fojin.app/chat](https://fojin.app/chat)，无需安装。
> 🛠️ **本节面向** Claude Code / Cursor / Codex CLI / OpenCode / Gemini CLI 用户。

```bash
npx master-skill install --all          # 一次装全部 20 个 Skill
npx master-skill install master-huineng # 或只装一位
npx master-skill list                   # 看全部可装的
npx master-skill recommend "念佛怎么念才算老实"   # 不知道该问谁？让它推荐
```

装好后在对话里直接调 `/master-huineng`、`/compare-masters` 等。

> 五端安装细节（Claude Code 插件 / Cursor / OpenCode / Codex CLI / Gemini CLI）、
> 全局安装、教学模式用法、`/create-master` 自定义生成
> → **[docs/install.md](docs/install.md)**

## 桌面管理器

原生桌面控制台(纯 Rust,egui,单二进制,无 Electron),统一管理 19 个 master skill 的安装状态、fidelity 评测覆盖率、运行追踪与质量门禁:

![Master-skill Desktop Manager](https://raw.githubusercontent.com/xr843/Master-skill/main/docs/assets/desktop-manager.png)

**下载**:[Releases](https://github.com/xr843/Master-skill/releases) 提供 Linux / Windows / macOS 预编译二进制,下载后直接运行(仓库根目录下执行,需本地已 clone 本仓库)。Linux / macOS 下载后需先 `chmod +x` 赋予可执行权限;macOS 上二进制未签名,首次运行需右键"打开"或执行 `xattr -d com.apple.quarantine <文件名>` 解除隔离。

**从源码构建**:

```bash
cd desktop && cargo build --release
./target/release/master-skill-desktop            # 图形界面
./target/release/master-skill-desktop --baseline # 无头跑 fidelity dry-run 基线
```

---

## 预置法师

十五位祖师，四大传统。命令即技能名，装好后直接在对话里调用。

| 命令 | 祖师 | 传统 · 宗派 | 年代 |
|---|---|---|---|
| `/master-nagarjuna` | 龙树菩萨 | 印度 · 中观（八宗共祖） | 约 150-250 |
| `/master-kumarajiva` | 鸠摩罗什 | 汉传 · 三论／中观 | 344-413 |
| `/master-zhiyi` | 智顗大师 | 汉传 · 天台 | 538-597 |
| `/master-xuanzang` | 玄奘法师 | 汉传 · 法相唯识 | 602-664 |
| `/master-huineng` | 慧能大师 | 汉传 · 禅宗六祖 | 638-713 |
| `/master-fazang` | 法藏大师 | 汉传 · 华严 | 643-712 |
| `/master-ouyi` | 蕅益大师 | 汉传 · 天台／净土（跨宗派） | 1599-1655 |
| `/master-xuyun` | 虚云老和尚 | 汉传 · 禅宗五宗兼嗣 | 1840-1959 |
| `/master-yinguang` | 印光大师 | 汉传 · 净土 | 1861-1940 |
| `/master-atisha` | 阿底峡尊者 | 藏传 · 噶当（三士道） | 982-1054 |
| `/master-milarepa` | 米拉日巴尊者 | 藏传 · 噶举（大手印） | 1052-1135 |
| `/master-tsongkhapa` | 宗喀巴大师 | 藏传 · 格鲁（应成中观） | 1357-1419 |
| `/master-buddhaghosa` | 觉音尊者 | 南传 · 上座部论师 | 5 世纪 |
| `/master-mahasi-sayadaw` | 马哈希尊者 | 南传 · 缅甸内观 | 1904-1982 |
| `/master-ajahn-chah` | 阿姜查 | 南传 · 泰国森林禅林派 | 1918-1992 |

**教学模式**：`/compare-masters` 并列对比 · `/master-debate` 多轮对辩 · `/master-curriculum` 学修路径 · `/master-help` 我该问谁 · `/create-master` 自定义生成

> 每位祖师的生平、核心思想与声明来源 → **[docs/masters.md](docs/masters.md)**

## 架构图

目录结构与数据流 → **[docs/architecture.md](docs/architecture.md)**

## 与 FoJin 的关系

[FoJin](https://fojin.app) 是一个佛教文本聚合平台，整合了 503 个数据源、10K+ 篇文本、678K+ 条语义向量嵌入，以及涵盖 31K 实体的知识图谱，覆盖 CBETA 汉文大藏经、SuttaCentral 巴利藏及英译、84000 藏经英译等主要语料库。

Master-skill 通过 `tools/fojin_bridge.py` 接入 FoJin API，实现：

- 知识图谱实体检索（法师生平、师承、宗派）
- 语义向量相似度搜索（教义相关经文）
- 原文段落提取与出处追踪

所有引用都必须能追溯到 persona 声明的来源 ID；仅当实时检索返回真实 `text_id` 时附 FoJin 定位链接，否则使用对应官方目录或离线声明来源。

---

## 敏感性边界

**不做：**

- 不对宗派优劣进行评判
- 不宣称神通感应
- 不涉及政治化宗教议题

**要做：**

- 忠实依据声明来源，回答附可追溯的来源 ID；有真实 `text_id` 时再附 FoJin 定位链接
- 仅在 citation contract 允许且离线资料不足时通过运行时 RAG 检索，不以 AI 自身知识冒充原典
- 遇到超出范围的问题坦诚说明

---

## 常见问题

安装、调用、检索的常见问题 → **[docs/troubleshooting.md](docs/troubleshooting.md)**

## 贡献指南

**完整流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。** 以下是速查：

- 🐞 **报 bug**：[Bug Report](https://github.com/xr843/Master-skill/issues/new?template=bug_report.yml)
- ✨ **提 feature**：[Feature Request](https://github.com/xr843/Master-skill/issues/new?template=feature_request.yml)
- 🧘 **建议新法师**：**先开 [New Master 提议](https://github.com/xr843/Master-skill/issues/new?template=new_master.yml) 征询**，不要直接写完 PR 再被拒（版权 Tier / 教界边界 / 史料可得性 三重审查）
- 🚨 **教界越界报告**：[Boundary Violation (P0)](https://github.com/xr843/Master-skill/issues/new?template=boundary_violation.yml)
- 💬 **一般讨论 / 提问**：[GitHub Discussions](https://github.com/xr843/Master-skill/discussions)

**新增一位法师的必读：**

1. [ETHICS.md](ETHICS.md) §2 — 确认版权 Tier（A 可直接 PR，B 需授权证明，C 一律拒绝）
2. [ETHICS.md](ETHICS.md) §3 — 教界禁止行为须写入该法师 `voice.md` Layer 0
3. [CONTRIBUTING.md](CONTRIBUTING.md) §3 — 目录结构、frontmatter、fidelity 测试用例编写规范
4. 提交前：`python scripts/validate.py --strict` 绿色 + `tests/fidelity.jsonl` 至少 5 条 + CI fidelity-smoke 通过

其它一般贡献（文档、工具链、CI）走普通 PR 流程。

---

## 许可证

MIT License

---

## 致谢

感谢以下开源佛教文献项目：

- [CBETA](https://cbeta.org) — 汉文大藏经数字化
- [SuttaCentral](https://suttacentral.net) — 巴利藏及多语种译本
- [84000](https://84000.co) — 藏经英译项目

---

## Community

- [LINUX DO](https://linux.do) — 感谢 LINUX DO 社区的支持与反馈
