<h1 align="center">Master-skill</h1>

<p align="center">
  <em>「一切有为法，如梦幻泡影，如露亦如电，应作如是观。」</em><br>
  <sub>——《金刚般若波罗蜜经》</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/Python-3.9+-green.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/Claude%20Code-Skill-purple.svg" alt="Claude Code Skill">
  <img src="https://img.shields.io/badge/AgentSkills-Standard-orange.svg" alt="AgentSkills Standard">
</p>

<p align="center">
  翻开《瑜伽师地论》百卷，不知从何读起？<br>
  想学禅宗，不知应当亲近哪位祖师？<br>
  读白话译注总隔一层，又难以直入文言？<br>
  学术研究想引用祖师原文，苦于找不到权威出处？
</p>

<p align="center">
  <strong>依据三大佛教传统祖师大德的教学风格，通达 AI 学习伙伴</strong><br>
  10 位祖师 · 汉传 / 藏传 / 南传跨传统 · CBETA / BDRC / SuttaCentral 真实出处 · AgentSkills 标准
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

在 AI 问答页面左下角点击「法师模式」，从 10 位三大传统祖师中选一位即可开始对话。

- 无需安装、无需注册
- 所有 `/compare-masters` 多祖师对比功能同样可用（含跨传统对比）
- 内置 FoJin 的 503 个数据源、678K+ 语义向量做实时经证检索
- 每条回答附原典出处（CBETA 经号 / BDRC 藏文典籍号 / SuttaCentral 巴利经号）

**如果你不确定该找谁问，可以这样开始：**

| 你的状况 | 推荐法师 |
|---|---|
| "妄念纷飞坐不住" | `/虚云` `/智顗` `/ajahn-chah`（参话头 / 止观 / 正念观察） |
| "读经文看不懂逻辑" | `/玄奘`（唯识严密分析） |
| "学佛很久但无力感" | `/印光`（老实念佛） |
| "想了解空性" | `/鸠摩罗什` `/慧能` `/milarepa`（中观 / 禅直指 / 大手印明空） |
| "想系统学华严 / 天台" | `/法藏` `/智顗`（判教与哲学体系） |
| "在禅与净土之间犹豫" | `/蕅益`（跨宗派融通） |
| "对苦行 / 闭关好奇" | `/milarepa`（雪山闭关 · 噶举派典范） |
| "想学最朴素的禅修" | `/ajahn-chah`（南传森林禅 · 出入息念） |
| "想跨传统比较看一个问题" | `/compare-masters`（自动配对汉藏南传视角） |

> 开发者、Claude Code / Cursor 用户可跳到下方 [开发者安装](#开发者安装) 小节，以 AgentSkill 形式在终端内使用。

---

> **v0.4 更新（2026-05）**：跨传统扩展——新增藏传米拉日巴尊者（噶举派 · 大手印 · 那洛六法）与南传阿姜查（泰国森林禅林派）。引用体系扩展支持 BDRC（藏文典籍）与 SuttaCentral（巴利三藏）。HARD-GATE 新增 `no_esoteric_instruction` 边界（密法不传授步骤）与 `no_fabricated_quotes`（南传开示不可代笔虚构）。
>
> **v0.3**：全面架构重构——CBETA 经文溯源、离线经文片段、自动化保真度测试、NPX 一键安装、cite.py/query.py 离线工具链、二阶段独立审查、HARD-GATE 铁律、多平台插件（Claude Code / Cursor / Codex / OpenCode / Gemini CLI 五端统一）、session-start hook 自动注入法师列表。

---

基于佛教经典文献的法师教学角色生成器，遵循 AgentSkills 标准，由 [FoJin](https://fojin.app) 驱动。

---

## 声明

本项目本着对佛教传统的尊重而建立。所有内容均依据佛教经典文献生成，不做教义评判，不代表任何宗派权威。生成内容仅供学习参考，如需正式修行指导，请亲近善知识。

> **⚠️ 所有通过 Master-skill 生成的对话均为 AI 合成内容**，不代表历史上祖师的亲口开示、亲笔著作。项目遵守严格的版权分级与教界边界——详见 **[ETHICS.md](ETHICS.md)**（AI 透明度、版权 Tier A–D、禁止行为、内容双轨授权、紧急下架通道）。

---

## 特性

- **预置十位三大传统祖师**：8 位汉传（唯识、中观、禅、天台、华严、净土、跨宗派）+ 1 位藏传（噶举派 · 米拉日巴）+ 1 位南传（森林禅林派 · 阿姜查），开箱即用
- **经文溯源（Provenance）**：每位祖师附原典标识（CBETA / BDRC / SuttaCentral）+ FoJin text ID，所有教义断言强制附原典引证
- **离线经文片段**：`sources/` 目录收录核心经典关键段落，FoJin 不可用时仍可离线引用
- **渐进式披露**：SKILL.md 以决策树 + Quick Ref 为主，`references/`、`sources/` 按需加载，Context 随查随取
- **HARD-GATE 铁律**：`/create-master` 与预置法师内置红线——无 CBETA 引证的教义断言不得写入、不得捏造经号、不得为虚构人物建角色
- **二阶段独立审查**：生成管线在写入前强制经过"教义准确性 → 风格一致性"两轮独立审查，FAIL 自动修复最多 2 轮
- **自动化保真度测试**：每位祖师 `tests/fidelity.jsonl` 5 条 Q&A，验证引用和关键词覆盖；CI 在每次推送时 dry-run 验证
- **多平台统一插件**：Claude Code、Cursor、Codex CLI、OpenCode、Gemini CLI 共用一份 `prebuilt/`，session-start hook 跨平台注入法师列表
- **NPX 一键安装**：`npx master-skill install zhiyi` 直接部署到 Claude Code
- **离线工具链**：`scripts/cite.py`（CBETA 引用查询）、`scripts/query.py`（离线语义检索）、`scripts/validate.py`（frontmatter linter）
- **FoJin 数据桥**：接入 [fojin.app](https://fojin.app) 的 503 个数据源、10K+ 文本、678K+ 语义向量和 31K 实体知识图谱
- **AgentSkills 标准**：遵循 [Anthropic Agent Skills](https://github.com/anthropics/skills) 规范，渐进式披露、决策树、黑盒脚本模式

---

## 开发者安装

> 👤 **只是想体验？** 直接用 [fojin.app/chat](https://fojin.app/chat)，跳过下面的安装步骤。
> 🛠️ **本节面向**：Claude Code / Cursor / Codex CLI / OpenCode / Gemini CLI 用户，希望在终端 AgentSkill 环境中直接调用 `/xuanzang` `/huineng` 等命令。

### 安装

**NPX 一键安装（推荐）**

```bash
# 安装指定祖师
npx master-skill install zhiyi fazang huineng

# 安装全部 10 位（三大传统）
npx master-skill install --all

# 查看可用祖师
npx master-skill list
```

**Claude Code（插件方式）**

```bash
# 即将上线插件市场，目前使用手动安装：
git clone https://github.com/xr843/Master-skill ~/Master-skill
cd ~/Master-skill && pip install -r requirements.txt
for d in prebuilt/*/; do ln -sf "$(pwd)/$d" ~/.claude/skills/"$(basename $d)"; done
ln -sf "$(pwd)" ~/.claude/skills/create-master
```

**Cursor**

```bash
git clone https://github.com/xr843/Master-skill ~/Master-skill
# Cursor 自动检测 .cursor-plugin/plugin.json 并注册技能
```

**OpenCode**

在 `opencode.json` 中添加：

```json
{
  "plugin": ["master-skill@git+https://github.com/xr843/Master-skill.git"]
}
```

**Codex CLI**

参见 [.codex/INSTALL.md](.codex/INSTALL.md)

**Gemini CLI**

本项目包含 `gemini-extension.json` 和 `GEMINI.md`，Gemini CLI 自动发现并加载。

### 使用预置法师

在支持 AgentSkills 的环境（Claude Code / Cursor / Codex CLI / OpenCode / Gemini CLI）中直接调用：

```
# 汉传
/xuanzang       — 玄奘法师（法相唯识宗）
/kumarajiva     — 鸠摩罗什（三论宗/中观）
/huineng        — 慧能大师（禅宗六祖）
/zhiyi          — 智顗大师（天台宗）
/fazang         — 法藏大师（华严宗）
/yinguang       — 印光大师（净土宗）
/ouyi           — 蕅益大师（天台/净土·跨宗派）
/xuyun          — 虚云老和尚（禅宗·五宗兼嗣）

# 藏传
/milarepa       — 米拉日巴尊者（噶举派 · 大手印 · 那洛六法）

# 南传
/ajahn-chah     — 阿姜查（泰国森林禅林派 · 巴蓬寺传承）
```

### 多法师对比

同一问题由 2-3 位法师并列回答，展现宗派视角差异：

```
# 自动选择相关法师
/compare-masters 什么是空性

# 手动指定法师（推荐，结果更精准）
/compare-masters 什么是遍行因 --masters xuanzang,zhiyi,ouyi

# 自然语言触发
请慧能和印光对比回答"如何看待念佛"
比较禅宗和净土宗对修行的看法
```

**选择逻辑**：系统先尝试从用户提问中提取关键词，与每位法师的核心概念匹配；若无强匹配，则按主题映射兜底（念佛/禅修/唯识中观/判教等）。**如果自动选的法师不符合预期，直接用 `--masters` 手动指定**。

### 自定义生成

```
/create-master 弘一大师
```

或自然语言触发：

```
帮我创建一个弘一大师的教学角色
```

系统将引导完成三步信息录入，然后自动从 FoJin 采集数据、生成教义分析与风格文件。

---

## 预置法师

### 玄奘法师（602-664）

唐代高僧，中国佛教史上最伟大的译经家。西行求法十七年，遍学印度诸部，归国后主持译经事业，译出经论七十五部一千三百三十五卷。创立法相唯识宗，以严谨精确的翻译风格著称，确立"五种不翻"原则。
主要来源：CBETA《大般若经》《瑜伽师地论》《成唯识论》《心经》等。
调用命令：`/xuanzang`

### 鸠摩罗什（Kumarajiva，344-413）

龟兹出身，后秦长安译经，中国四大译经家之一。其译文以文学性和流畅度著称，《妙法莲华经》《金刚经》《维摩诘经》《中论》等译本至今最为通行。奠定了三论宗（中观）在中国的基础。
主要来源：CBETA《妙法莲华经》《金刚经》《维摩诘经》《中论》《大智度论》等。
调用命令：`/kumarajiva`

### 慧能大师（638-713）

禅宗六祖，南宗禅创立者。不识文字的卖柴樵夫，闻《金刚经》而开悟，得五祖弘忍传法。著《六祖坛经》——中国人著作中唯一被尊为"经"者。主张"直指人心，见性成佛"，开顿悟法门。
主要来源：CBETA《六祖大师法宝坛经》T48n2008。
调用命令：`/huineng`

### 智顗大师（538-597）

天台宗创始人，被尊为"东土小释迦"。建立中国佛教第一个完整的判教体系（五时八教），著天台三大部《摩诃止观》《法华玄义》《法华文句》。核心思想：一念三千、三谛圆融、止观双修。
主要来源：CBETA《摩诃止观》T46n1911、《法华玄义》T33n1718 等。
调用命令：`/zhiyi`

### 法藏大师（643-712）

华严宗三祖，华严哲学体系的实际创立者。武则天国师，以"金师子章"为武后说华严义。核心思想：法界缘起、四法界、十玄门、六相圆融——一切现象互含互摄，事事无碍。
主要来源：CBETA《华严经探玄记》T35n1733、《华严五教章》T45n1866 等。
调用命令：`/fazang`

### 印光大师（1861-1940）

汉传净土宗第十三代祖师，近代净土复兴的核心人物。
文字平实恳切，戒行严谨，以书信形式广度众生，著有《印光法师文钞》三编。
主要来源：CBETA 汉文大藏经，含文钞正编、续编、三编及净土三经。
调用命令：`/yinguang`

### 蕅益大师（1599-1655）

明末四大高僧之一，净土宗九祖。"教宗天台，行归净土"——融通禅、教、律、净四宗，是中国佛教史上最重要的跨宗派综合者。其《阿弥陀经要解》被印光大师赞为"即使古佛再来，也不能超过其上"。
主要来源：CBETA《阿弥陀经要解》T37n1762、《教观纲宗》等。
调用命令：`/ouyi`

### 虚云老和尚（1840-1959）

近代禅宗泰斗，世寿一百二十岁，一身兼嗣禅门五宗（临济、曹洞、沩仰、云门、法眼）法脉——佛教史上绝无仅有。复兴六大祖庭，历经清末、民国、新中国三个时代。主张参话头、老实修行、禅净双修。
主要来源：CBETA《楞严经》《金刚经》《六祖坛经》等。
调用命令：`/xuyun`

### 米拉日巴尊者（Milarepa, 1052-1135） — 藏传 · 噶举派

藏传佛教噶举派精神祖师，"瑜伽士"传统（不入寺院、山中闭关、以歌教化）的典范。早年咒杀仇家造重业，依止玛尔巴译师净罪求法，于雪山闭关数十年以荨麻为食。以**道歌（mGur）**说法，影响后世整个藏传佛教。
主要来源：BDRC《米拉日巴道歌集》（W1KG14334，《十万歌集》mGur 'bum）、《密勒日巴尊者传》（W22272）。
调用命令：`/milarepa`

> ⚠️ 那洛六法、拙火、生起／圆满次第等密法**只介绍历史与原理，不传授具体修法步骤**。具体修持必须依止具格上师亲传与灌顶。

### 阿姜查 Ajahn Chah Subhaddo（1918-1992） — 南传 · 泰国森林禅林派

泰国森林禅林派最具国际影响力的禅师之一。以巴利戒律严格持守、四念处禅修、朴素生活化教学著称。其英语弟子（阿姜苏美多、阿姜帕沙诺等）建立了无畏山林、阿马罗筏底、奇泰罗等海外分院，将森林禅林派传至欧美。代表名言："如果你少放下一点，你就少一点苦。"
主要来源：巴利三藏（SuttaCentral）+ 公开开示集《Food for the Heart》《A Still Forest Pool》《Living Dhamma》。
调用命令：`/ajahn-chah`

---

## 架构图

```
用户请求
    |
    v
session-start hook ──> 自动注入法师列表（5 端统一）
    |
    v
SKILL.md (AgentSkills 入口：决策树 + Quick Ref)
    |
    +-- 预置法师 --> prebuilt/{slug}/
    |                   +-- SKILL.md          (决策树 + <HARD-GATE> 铁律)
    |                   +-- meta.json         (version / lineage / provenance)
    |                   +-- references/       (按需加载)
    |                   |   +-- teaching.md
    |                   |   +-- voice.md
    |                   +-- sources/          (离线经文片段)
    |                   |   +-- *.md (CBETA 段落)
    |                   +-- tests/
    |                       +-- fidelity.jsonl  (保真度样例, CI dry-run)
    |
    +-- 工具链
    |   +-- scripts/validate.py         (frontmatter linter)
    |   +-- scripts/cite.py             (CBETA 引用查询)
    |   +-- scripts/query.py            (离线语义检索)
    |   +-- scripts/test-fidelity.py    (保真度测试)
    |   +-- scripts/validate-fidelity.py
    |   +-- bin/cli.mjs                 (NPX installer)
    |
    +-- 自定义生成 (/create-master, 带 HARD-GATE)
          +-- Step 1-2  prompts/intake.md → tools/sutra_collector.py
          |             └─> FoJin API (KG + 语义检索 + 文本)
          +-- Step 3    prompts/{sutra,voice}_analyzer.md → 两阶段分析
          +-- Step 3.5  二阶段独立审查 ──┬─ prompts/doctrine_reviewer.md
          |                             └─ prompts/voice_reviewer.md
          +-- Step 4-5  tools/master_builder.py → tools/skill_writer.py
                        └─> tools/verify_sources.py (写入前最终验证)

多平台插件统一入口：
  .claude-plugin/    → Claude Code      (hooks/run-hook.cmd → session-start)
  .cursor-plugin/    → Cursor           (hooks/hooks-cursor.json)
  .codex/            → Codex CLI        (.codex/INSTALL.md)
  .opencode/         → OpenCode         (opencode.json 引用)
  gemini-extension.json → Gemini CLI    (GEMINI.md 自动加载)
```

---

## 与 FoJin 的关系

[FoJin](https://fojin.app) 是一个佛教文本聚合平台，整合了 503 个数据源、10K+ 篇文本、678K+ 条语义向量嵌入，以及涵盖 31K 实体的知识图谱，覆盖 CBETA 汉文大藏经、SuttaCentral 巴利藏及英译、84000 藏经英译等主要语料库。

Master-skill 通过 `tools/fojin_bridge.py` 接入 FoJin API，实现：

- 知识图谱实体检索（法师生平、师承、宗派）
- 语义向量相似度搜索（教义相关经文）
- 原文段落提取与出处追踪

所有引用均附带可追溯的 FoJin 链接，确保内容来源透明。

---

## 敏感性边界

**不做：**

- 不对宗派优劣进行评判
- 不宣称神通感应
- 不涉及政治化宗教议题

**要做：**

- 忠实依据经文原文，所有回答附 FoJin 出处链接
- 通过运行时 RAG 检索真实经文，而非仅依赖 AI 自身知识
- 遇到超出范围的问题坦诚说明

---

## 常见问题

**Q：FoJin API 不可达时还能用吗？**

能。每位预置法师的 `prebuilt/<name>/sources/` 收录了该法师核心经典的关键段落（离线经文片段）。FoJin 不可用时，法师会降级到离线模式并在回答中声明"当前使用离线片段"。`/create-master` 管线遇到 API 故障会提示用户切换手动输入模式，由用户粘贴经文原文继续生成。

**Q：CBETA 引用格式是什么样的？怎么验证？**

所有 CBETA 引证必须带 `Txxn####` 形式的经号（例如《妙法蓮華經》→ `T9n262`）。`scripts/validate.py` 会检查 frontmatter 的 `sources` 字段格式；`tools/verify_sources.py` 在写入前会逐条核对 FoJin `text_id` 的有效性，失效链接自动降级为 FoJin 搜索链接，不会留下死链。

**Q：`npx master-skill install` 执行失败、报 ENOTEMPTY 或权限错误怎么办？**

先清理 `~/.claude/skills/master-<name>/` 残留目录再重试。如果是 npm 缓存问题，`npm cache clean --force` 后重跑 NPX。Windows 用户请在 Git Bash 或 WSL 中执行，避免 cmd.exe 的路径转义问题。

**Q：生成的法师内容和历史记载不符，怎么纠正？**

直接在对话中告诉法师"他不会这样说话"或"他应该更严厉一些"。`/create-master` 的纠正模式会识别纠正类型（教义纠正 → 追加到 `teaching.md`；风格纠正 → 追加到 `voice.md`），以 `## Correction` 块形式记录并自动递增 patch 版本号。纠正记录的优先级高于分析生成的内容。

**Q：如何贡献一位新的预置法师？**

见下方「贡献指南」。基本流程：遵循 v0.3 目录结构生成 `prebuilt/<name>/`、跑通 `scripts/validate.py --strict`、补齐 `tests/fidelity.jsonl` 的 5 条以上样例，然后提 PR。

---

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
