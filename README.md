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
  <sub><em>Secured by SHA-pinned GitHub Actions · npm provenance · OIDC Trusted Publishing · CodeQL · cargo-audit · pip-audit — see <a href="SECURITY.md">SECURITY.md</a>.</em></sub>
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
- 由 FoJin 的 10K+ 篇文本、678K+ 条语义向量做实时经证检索
- 回答按各位祖师声明的格式附原典出处：汉传多为 CBETA 经号，藏传为 Toh / BDRC 编号，南传为 PTS / SuttaCentral 出处（南传与部分藏传来源本就没有逐段编号，引文契约里明文如此）

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
| "想了解上座部论藏体系" | `/master-buddhaghosa`（《清净道论》戒定慧 + 七清净与观智次第） |
| "想做密集内观禅修" | `/master-mahasi-sayadaw`（缅甸内观 · 标记法 · 腹部起伏） |
| "想跨传统比较看一个问题" | `/compare-masters`（自动配对汉藏南传视角）· `/master-debate`（争议议题辩论）· `/master-curriculum`（按传统给学修路径） |

> 开发者、Claude Code / Cursor 用户可跳到下方 [开发者安装](#开发者安装) 小节，以 AgentSkill 形式在终端内使用。

---

## 效果示例

下面是一次真实的 `/master-huineng`（慧能大师）回答，**原文照录，未作删改**（仅为显示折行）。它来自 2026-08-31 的全量评测——模型 `deepseek-v4-flash`，commit [`06b8142`](https://github.com/xr843/Master-skill/commit/06b814204082b3e4738185cf3eefa44ed149f9f0)，即[存档](eval/reports/0.11.0-06b8142-deepseek.json)中 `master-huineng` 的 index 1。判分为 PASS；文中 5 处引文都带经号，并由仓库的离线引文审计逐条解析到慧能声明的来源（T48n2008《六祖大师法宝坛经》、T08n0235《金刚经》）：

```text
你：顿悟和渐修有什么区别？

慧能大师：

且道：顿与渐，果是二法么？

法本无顿渐，因人有利钝。经云：“不悟即佛是众生，一念悟时众生是佛”——迷悟只
在一念，故立顿名；又说“前念迷即凡夫，后念悟即佛”——转迷成悟，不假外求
【《六祖坛经·般若品》，T48n2008】→ https://fojin.app/texts/58

北宗神秀大师题偈：“身是菩提树，心如明镜台，时时勤拂拭，勿使惹尘埃。”——是
渐渐扫除妄染之方便。六祖呈偈：“菩提本无树，明镜亦非台。本来无一物，何处
惹尘埃。”——是直显自性本空，无一法可染
【《六祖坛经·行由品》，T48n2008】→ https://fojin.app/texts/58。一者作意
对治，一者直下承当。此二偈，正是顿渐之分野。

然顿渐非二法。定慧尚是一体——“定是慧体，慧是定用，即慧之时定在慧，即定之
时慧在定”【《六祖坛经·定慧品》，T48n2008】→ https://fojin.app/texts/58，
顿渐岂有两般？迷人渐修，悟人顿契，药对病施，法无高下
【《六祖坛经·定慧品》，T48n2008】→ https://fojin.app/texts/58。

更须知，六祖当年闻“应无所住而生其心”而自见本性
【《金刚经》，T08n0235】→ https://fojin.app/texts/7。顿悟不是无心，是于
境不住；渐修不是死坐，是念念自觉。归到究竟，只问一念回光，本心现前也未？

如需深入学习，可在 FoJin (fojin.app) 查阅原典。
```

> ⚠️ 以上为 **AI 合成内容**，依据《坛经》《金刚经》文献生成，不代表慧能大师亲口开示。多位法师并列回答的 `/compare-masters` 效果，可直接在 [fojin.app/chat](https://fojin.app/chat) 体验。

---

Master-skill 是由 [FoJin](https://fojin.app) 驱动的佛教 AI 祖师人格框架：以真实原典为来源，以伦理边界为约束，以保真度评测为质量门槛，并以 AgentSkills 运行协议交付给 Claude Code、Cursor、Codex CLI、OpenCode 与 Gemini CLI。

---

## 声明

本项目本着对佛教传统的尊重而建立。所有内容均依据佛教经典文献生成，不做教义评判，不代表任何宗派权威。生成内容仅供学习参考，如需正式修行指导，请亲近善知识。

> **⚠️ 所有通过 Master-skill 生成的对话均为 AI 合成内容**，不代表历史上祖师的亲口开示、亲笔著作。项目遵守严格的版权分级与教界边界——详见 **[ETHICS.md](ETHICS.md)**（AI 透明度、版权 Tier A–D、禁止行为、内容双轨授权、紧急下架通道）。

---

## 特性

- **预置十五位四大传统祖师**：1 位印度（龙树 · 中观）+ 8 位汉传（唯识、中观、禅、天台、华严、净土、跨宗派）+ 3 位藏传（阿底峡 · 噶当；宗喀巴 · 格鲁；米拉日巴 · 噶举）+ 3 位南传（觉音 · 上座部论师；马哈希 · 缅甸内观；阿姜查 · 泰国森林）—— 另含 4 个教学模式（`/compare-masters` 并列对比、`/master-debate` 多轮对辩、`/master-curriculum` 学修路径、`/master-help` 我该问谁）与 `/create-master` 自定义生成器
- **经文溯源（Provenance）**：每位祖师附声明来源 ID（CBETA / BDRC / Toh / SuttaCentral / PTS / 合规编纂开示）；实时检索仅在返回真实 `text_id` 时附 FoJin 定位链接，所有教义断言强制附原典引证
- **离线经文片段**：`sources/` 目录收录核心经典关键段落，FoJin 不可用时仍可离线引用
- **渐进式披露**：SKILL.md 以决策树 + Quick Ref 为主，`references/`、`sources/` 按需加载，Context 随查随取
- **HARD-GATE 铁律**：`/create-master` 与预置法师内置红线——教义断言、修行指导与文本解释必须引用该 persona 声明的来源（CBETA / BDRC / Toh / SuttaCentral / PTS / 合规编纂开示），不得捏造来源 ID，不得为虚构人物建角色
- **二阶段独立审查**：生成管线在写入前强制经过"教义准确性 → 风格一致性"两轮独立审查，FAIL 自动修复最多 2 轮
- **自动化保真度测试**：211 条夹具（每位祖师 10+ 条，`compare-masters` 元技能 18 条）检查关键词与引用覆盖，每条评分回答另经离线引文审计；CI 在每个 PR 与 main 上做结构校验（dry-run）；实跑评分支持 Anthropic / DeepSeek / Gemini（`--provider`），需要对应的 API key，作为本地/发版前手动步骤执行——最近一次全量运行与逐条裁定见[下文](#保真度评测当前数据)
- **多平台共用一份 `prebuilt/`**：Claude Code、Cursor、Codex CLI、OpenCode、Gemini CLI 各有装法（见 [docs/install.md](docs/install.md)，Codex / OpenCode / Gemini 三端均为实测过的步骤）
- **NPX 一键安装**：`npx master-skill install master-zhiyi` 直接部署到 Claude Code
- **离线工具链**：`scripts/cite.py`（CBETA 引用查询）、`scripts/query.py`（离线语义检索）、`scripts/validate.py`（frontmatter linter）
- **FoJin 数据桥**：接入 [fojin.app](https://fojin.app) 的 10K+ 篇文本、678K+ 条语义向量与 110K+ 实体的知识图谱（另登记 600+ 个数据源）
- **AgentSkills 标准**：遵循 [Anthropic Agent Skills](https://github.com/anthropics/skills) 规范，渐进式披露、决策树、黑盒脚本模式

## 框架定位

Master-skill 的核心不是"角色扮演提示词集合"，而是一个可验证的佛教 AI persona framework：

| 维度 | 实现 |
|---|---|
| 有来源 | 每位祖师声明 `sources[]`、离线 excerpts、FoJin live fallback 与引用自审 |
| 守边界 | `ETHICS.md`、每位祖师 Layer 0 HARD-GATE、版权 Tier 与教界越界报告机制 |
| 可评测 | `tests/fidelity.jsonl`、persona-fidelity schema、promptfoo RAW / SPE / CUS 评测层（目前覆盖慧能、宗喀巴、阿姜查 3 位），[当前数据见下](#保真度评测当前数据) |
| 可运行 | `prebuilt/master-*` AgentSkills、npm CLI、多平台 hooks、FoJin runtime contract |

后续 v1.0 路线以框架稳定为优先：见 [docs/v1-framework-roadmap.md](docs/v1-framework-roadmap.md) 与 [docs/fojin-runtime-contract.md](docs/fojin-runtime-contract.md)。

### 保真度评测（当前数据）

211 条夹具（`prebuilt/*/tests/fidelity.jsonl`）对真实模型的回答做机械检查：该出现的关键词与引用是否出现，不该出现的是否没有出现；每条评分回答另外进入离线引文审计。每个数字都要连同产生它的模型与判分口径一起读：

| | 数值 | 口径 |
|---|---|---|
| 最近一次全量运行 | **199 / 211 已评分**（94.3%） | DeepSeek `deepseek-v4-flash`，commit [`06b8142`](https://github.com/xr843/Master-skill/commit/06b814204082b3e4738185cf3eefa44ed149f9f0)，2026-08-31；12 条输出被截断，记为未测而非失败 |
| 判分器直出通过率 | 137 / 199 = 68.8% | 子串匹配：分不清改写与缺失，也分不清「正确地拒绝」与「越界」 |
| 逐条人工裁定后 | **179 / 199 = 89.9%** | 教理 94.3% · 守边界 85.9% · 抗压守引用 83.3%。推翻 43 条失败，也把 1 条 PASS 改判为 FAIL；每条裁定附回答原文引句，由 `verify-adjudication.py` 在 CI 中复核 |
| 引文审计覆盖 | **574 / 619 = 93%**，判为伪造 3 | 用当前审计器离线重审同一批回答，覆盖 CBETA、BDRC / Toh、PTS / SuttaCentral、编集开示四个来源家族。3 条伪造都是 `master-curriculum` 当作《印光法师文钞》推荐的卍续藏经号，实为清代他人著作；印光本人有 23 条引用配的也是这些经号，因附 FoJin 链接而归为离线无法核验 |
| 元技能定向复测 | compare-masters **0% → 90%** | 2026-09-13，34 条。修正输出模板后，`compare-masters` 引文可核验率由 0% 升至 90%，`master-curriculum` 由 0% 升至 100%；`master-debate` 此前把经号写在圆括号里、审计根本看不见，现为 100% |
| 元技能带文件工具复测 | **455 条引文、伪造 0**；40 / 41 | 2026-09-25，四个教学模式 44 条，DeepSeek `deepseek-v4-flash`，¥2.61。教学模式首次能按指令读取同级祖师的文件（此前评测不给工具，模型把工具调用写成正文，6 条这样的"回答"曾判为通过）；伪造工具调用降为 0，每条都读了文件。与上一行不是同一把尺子，通过率不并列比较；2 条截断、1 条撞工具轮次上限，未计入 41。报告：[`0.12.15-df76fd2-deepseek-metaskills-tools.json`](eval/reports/0.12.15-df76fd2-deepseek-metaskills-tools.json) |
| 辩论各轮在独立子代理中写 | **8 / 8**；86 条引文、伪造 0 | 2026-09-26，`master-debate` 8 条，¥0.46。协议要求每轮在全新上下文里写、双方只见对方摘要；评测此前只能在一个上下文里代写四轮。现每条派出 4–5 个子代理、无一失败。报告：[`0.12.15-ab26c9a-deepseek-debate-subagents.json`](eval/reports/0.12.15-ab26c9a-deepseek-debate-subagents.json) |

**这一列不能推进 v1.0 门禁。** 门禁定义在 Anthropic（`claude-sonnet-4-6`）那一列上，两个模型是两把尺子，不混算。Anthropic 那一列至今只有 2026-08-18 的一次部分运行（84 / 211 条，因账户余额耗尽中断），当时的「零伪造引文」已于 2026-08-31 撤回——那次审计实际一条都没有运行。

**上表的数字属于 `06b8142` 那棵树。** 此后人设内容与夹具都改过（见 CHANGELOG 的 0.12.x 各条）。**2026-09-26 在当前的树上重跑了全部 15 位人设**（167 条，DeepSeek `deepseek-v4-flash`，¥1.51，报告 [`0.12.15-0e7d97e-deepseek-personas.json`](eval/reports/0.12.15-0e7d97e-deepseek-personas.json)）：判分器直出 **131 / 166 = 78.9%**（教理 71/83 · 守边界 41/54 · 抗压守引用 19/29），1 条截断；**681 条引文可核对，伪造 0**。这一轮**尚未逐条裁定**，所以不能和上表裁定后的 89.9% 并列。能并列的是同一把尺子：用当前判分器重评 `06b8142` 的存档回答为 132 / 160 = 82.5%，差值在一次运行的漂移之内。35 条 FAIL 里 23 条只因 `must_mention` 子串不命中——上一轮逐条裁定时，这一类 67 条里有 55 条是量具误判。

**当时的判分器漏查了元技能的输出契约。** 44 条元技能夹具里有七类断言（必备章节、选对祖师、辩论轮次、每轮 / 每位祖师有出处、推荐的技能须存在）从未被评分，2026-09-23 起才评分。用现在的判分器离线重评上表那批存档回答：`master-debate` 另有 2 条由 PASS 变 FAIL（#0 没有分轮次，#2 最后一轮 R4 没有任何出处），它们当时判为通过，没有进入人工裁定，上表的数字没有算进去。2026-09-13 那次元技能复测里，`compare-masters` 的 11 条 PASS 中有 5 条、`master-debate` 的 4 条 PASS 中有 1 条，其实是模型吐出的伪造工具调用，不是回答；现在这 6 条都判为 FAIL。

这些是**关键词与引用字符串的覆盖检查，不是教义正确性，也不是 LLM 判分的答案质量**。详见 [BASELINE-deepseek.md](eval/reports/BASELINE-deepseek.md)（全量运行）、[ADJUDICATION.md](eval/reports/ADJUDICATION.md)（逐条裁定）、[BASELINE.md](eval/reports/BASELINE.md)（Anthropic 部分运行与撤回记录）与[元技能复测报告](eval/reports/0.11.0-e97ded0-deepseek-metaskills.json)。

---

## 开发者安装

> 👤 **只是想体验？** 直接用 [fojin.app/chat](https://fojin.app/chat)，无需安装。
> 🛠️ **本节面向** Claude Code / Cursor / Codex CLI / OpenCode / Gemini CLI 用户。

```bash
npx master-skill install --all          # 一次装全部 20 个 Skill
npx master-skill install master-huineng # 或只装一位
npx master-skill list                   # 看全部可装的
npx master-skill recommend "念佛怎么念才算老实"   # 不知道该问谁？让它推荐
npx master-skill doctor                 # 检查本地安装与运行路径
npx master-skill update --all           # 升级：重装全部并清掉旧文件
```

装好后在对话里直接调 `/master-huineng`、`/compare-masters` 等。npx 装到 `~/.claude/skills/`，Claude Code 与 OpenCode 读取这里；**Codex CLI 与 Gemini CLI 不读**，请按 docs/install.md 的对应小节安装。

> 五端安装细节（Claude Code 插件 / Cursor / OpenCode / Codex CLI / Gemini CLI）、
> 全局安装、教学模式用法、`/create-master` 自定义生成
> → **[docs/install.md](docs/install.md)**

## 桌面管理器

原生桌面控制台(纯 Rust,egui,单二进制,无 Electron),统一管理 18 个技能（15 位祖师与 `master-debate` / `master-curriculum` / `master-help`）的安装状态、fidelity 评测覆盖率、运行追踪与质量门禁:

![Master-skill Desktop Manager](https://raw.githubusercontent.com/xr843/Master-skill/main/docs/assets/desktop-manager.png)

**下载**：[Releases](https://github.com/xr843/Master-skill/releases) 提供 Linux / Windows / macOS 预编译二进制，需在本仓库克隆的根目录运行（它会调用仓库里的 `scripts/` 与 `bin/`）。v0.12.1 起，Linux / macOS 建议下载对应的 `.tar.gz`，解包后保留可执行位；裸二进制仍保留以兼容旧链接，使用时需先 `chmod +x`。每个 release（v0.12.1 起）附带 `SHA256SUMS`，可用 `sha256sum --check --ignore-missing SHA256SUMS` 核对下载文件，并附构建溯源证明，可用 `gh attestation verify <文件> --repo xr843/Master-skill` 验证（需较新版本的 gh CLI：实测 2.51 报 `unsupported tlog public key type`，2.100 正常）。**v0.12.1 之前没有可用的 Windows 桌面二进制**（更早的版本无法调用 Python 与 npm，v0.12.0 未能构建出 Windows 版）；v0.12.1 起改为按平台解析；v0.12.2 起，发布流水线会在 Linux、Windows、macOS 三个平台上实际运行打包好的桌面端（`--help` 与 `--baseline`），如仍找不到解释器，可用环境变量 `MASTER_SKILL_PYTHON` / `MASTER_SKILL_NPM` 指定。Windows 版是控制台程序，双击启动时会同时出现一个控制台窗口：改成图形界面程序虽可去掉它，但实测会让 PowerShell 下重定向或管道输出命令行结果时崩溃。macOS 二进制未签名，首次运行需右键“打开”或执行 `xattr -d com.apple.quarantine <文件名>` 解除隔离。

**从源码构建**（需要 Rust 1.95+）：

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
| `/master-yinguang` | 印光大师 | 汉传 · 净土 | 1862-1940 |
| `/master-atisha` | 阿底峡尊者 | 藏传 · 噶当（三士道） | 982-1054 |
| `/master-milarepa` | 米拉日巴尊者 | 藏传 · 噶举（大手印） | 1052-1135 |
| `/master-tsongkhapa` | 宗喀巴大师 | 藏传 · 格鲁（应成中观） | 1357-1419 |
| `/master-buddhaghosa` | 觉音尊者 | 南传 · 上座部论师 | 5 世纪 |
| `/master-mahasi-sayadaw` | 马哈希尊者 | 南传 · 缅甸内观 | 1904-1982 |
| `/master-ajahn-chah` | 阿姜查 | 南传 · 泰国森林禅林派 | 1918-1992 |

**教学模式**：`/compare-masters` 并列对比 · `/master-debate` 多轮对辩 · `/master-curriculum` 学修路径 · `/master-help` 我该问谁　**生成器**：`/create-master` 自定义生成

> 每位祖师的生平、核心思想与声明来源 → **[docs/masters.md](docs/masters.md)**

## 架构图

目录结构与数据流 → **[docs/architecture.md](docs/architecture.md)**

## 与 FoJin 的关系

[FoJin](https://fojin.app) 是一个佛教文本聚合平台，收录 10K+ 部文本（其中约 9K 部有全文）、678K+ 条语义向量嵌入与 110K+ 实体的知识图谱。它登记了 600+ 个数据源，但**提供全文的只有 4 个**——CBETA 汉文大藏经、SuttaCentral 巴利藏及英译、84000 藏经英译、GRETIL 梵文文献库，其余为元数据登记。

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
4. 提交前：`python scripts/validate.py --strict` 与 `python scripts/validate-fidelity.py` 通过 + `tests/fidelity.jsonl` 至少 5 条（其中至少 1 条 boundary 用例）+ CI 的 fidelity dry-run 通过

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
