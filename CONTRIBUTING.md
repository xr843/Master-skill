# Contributing to Master-skill

欢迎贡献！本项目分三类改动，每类流程不同——**请先判断你的改动属于哪一类**，再按对应流程走。

> 📜 贡献前**必读**：[`ETHICS.md`](ETHICS.md) — AI 透明度、版权 Tier、教界边界、内容授权。违反伦理条款的 PR 不会 review。

---

## 三类改动

### ① 代码 / CI / 工具链

`scripts/**`, `tools/**`, `bin/**`, `hooks/**`, `.github/**`, `tests/`（非 fidelity）

流程：**普通 GitHub PR**。满足 Python 3.9+、现有测试通过、`python scripts/validate.py --strict` 绿色即可。

### ② 文档 / README / 脚本注释 / 翻译

`README.md`, `README_EN.md`, `docs/**`, `CHANGELOG.md`, 其它非 `prebuilt/**` 的 markdown

流程：**普通 PR**。不需要跑 fidelity 测试，CI 中的 validate / smoke job 会跳过（除非改了其它触发路径）。

### ③ 贡献 / 修改法师内容（⚠️ 最严，必读）

`prebuilt/**`, `prompts/**`

涉及：

- 新增一位法师
- 修改已有法师的 `teaching.md` / `voice.md` / `sources/`
- 修改 fidelity 测试用例

流程：见下方 [§3 贡献一位新法师](#3-贡献一位新法师)。

---

## 开发环境

```bash
git clone https://github.com/xr843/Master-skill
cd Master-skill

# Python（用于 validate / fidelity / verify-links）
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install anthropic  # 仅 fidelity 实跑需要

# Node（用于 npx installer）
# 需要 Node.js >= 18
npm install -g .  # 可选，本地测试 CLI
# 注：npm test / npm run validate 调用 `python3`（系统自带或 venv 内均可）
```

**基本健康检查：**

```bash
# Lint SKILL.md frontmatter — 每位法师必须通过
python scripts/validate.py --strict

# Fidelity 结构（不调 API）
python scripts/validate-fidelity.py

# Fidelity 干跑（显示测试用例，不调 API）
python scripts/test-fidelity.py --all --dry-run

# Fidelity 实跑（需要 ANTHROPIC_API_KEY，一次 ≈ $0.05-0.10）
ANTHROPIC_API_KEY=sk-... python scripts/test-fidelity.py --master master-zhiyi --max-tests 1
```

---

## § 1 分支与提交约定

- **分支命名**：`feat/<short>`、`fix/<short>`、`docs/<short>`、`chore/<short>`、`master/<slug>`
- **Commit 格式**：[Conventional Commits](https://www.conventionalcommits.org/)（`feat:` / `fix:` / `docs:` / `chore:` / `refactor:` / `test:` + 可选 scope）
- **Commit message 语言**：代码/基础设施类改动用英文，佛教内容类改动中英文均可，但 PR description 需要有中文摘要（方便教内读者审阅）

---

## § 2 PR 评审清单

提交 PR 前自检：

- [ ] CI 绿色（validate 必过；fidelity-smoke 在未配置 `ANTHROPIC_API_KEY` 时为 advisory pass——目前主仓与 forks 均未配置，绿勾代表结构校验通过，实跑评分是本地/发版前手动步骤）
- [ ] CHANGELOG.md 的 `[Unreleased]` 章节已更新（除非是纯 typo）
- [ ] 涉及 `prebuilt/**` 的改动 → 已 review ETHICS.md §2（版权 Tier）、§3（教界边界）
- [ ] PR description 说明**做了什么 + 为什么**，而非只列改动文件

---

## § 3 贡献一位新法师

### 3.1 前置检查（必看 [`ETHICS.md`](ETHICS.md)）

**这位法师可以收录吗？**

| 情形 | 判断 |
|-----|------|
| 生卒明确，圆寂超过 50 年（CN/TW）或 70 年（大多数其它辖区） | ✅ Tier A，可直接 PR |
| 近现代法师，亲授弟子在世 / 所属寺院仍运营 | ⚠️ Tier B，PR 必须附 `prebuilt/{slug}/LICENSE.md` 授权证明 |
| 在世法师 | ❌ Tier C，不接受 |
| 主流学界对身份 / 著作有争议 | ❌ Tier C，不接受 |
| 汉传以外（南传 / 藏传 / 日莲 / 天台日宗等）| ⏳ 当前版本仅汉传，未来独立分支规划中，不接受 |

**想收录但不确定？** 先开一个 [new_master Issue](https://github.com/xr843/Master-skill/issues/new?template=new_master.yml) 征询意见，**不要先写完再提 PR**——已经投入精力再被拒成本太高。

### 3.2 选项 A：交给 `/create-master` 生成（推荐）

```bash
# 在 Claude Code / Cursor 等 AgentSkills 环境
/create-master 某某法师
```

生成管线会：

1. **intake** — 3 问收集信息（传承、核心教义、可用文献）
2. **collect** — 从 FoJin 采集该法师的 CBETA 文本
3. **analyze** — `sutra_analyzer` + `voice_analyzer` 并行分析
4. **review** — 二阶段独立审查：教义准确性 → 风格一致性
5. **write** — 生成 `prebuilt/<slug>/` 目录结构
6. **validate** — 自动跑 `validate.py` + `validate-fidelity.py`

然后你手动：

- Review 生成结果，补充 `references/teaching.md`、`voice.md` 的细节
- 起草 5 条 `tests/fidelity.jsonl`（1 basic + 2 intermediate + 2 advanced）
- 跑一次 `test-fidelity.py --master <slug>` 确认 ≥ 4/5 通过
- 提 PR

### 3.3 选项 B：手工编写

参考现有法师 `prebuilt/master-yinguang/` 的完整结构：

```
prebuilt/master-<slug>/
├── SKILL.md             # 必须。frontmatter 见下
├── meta.json            # 必须。search_scope + keywords
├── references/
│   ├── teaching.md      # 必须。教义体系，每条断言附 CBETA 引证
│   └── voice.md         # 必须。Layer 0/1/2/3 四层表达风格
├── sources/
│   ├── INDEX.md         # 必须。本目录导览
│   └── *.md             # ≥ 2 篇 CBETA 核心段落摘录
└── tests/
    └── fidelity.jsonl   # 必须。5 条 Q&A 测试用例
```

**SKILL.md frontmatter 必填字段：**

```yaml
---
name: <slug>              # 小写英文或拼音，作为 `/命令` 触发词
description: Use when user asks about ..., triggers include ...
version: 0.1.0
license: MIT
lineage: <宗派>
dates: 生年-卒年
sources:
  - title: <经典名称>
    cbeta_id: <T 或 X + 数字>
    fojin_text_id: <FoJin 内部 text_id>
  - ...                    # 至少 3 部经
citation_format: "【《{title}》卷{juan}，{cbeta_id}】"
verified_by: <你的 GitHub handle>
verified_at: <YYYY-MM-DD>
---
```

**HARD-GATE 铁律（写入任何 `teaching.md` 前请自检）：**

1. 每一条教义断言必须附一个**真实**的 CBETA 经号
2. 不得捏造经号（`scripts/validate.py` 会对照 FoJin 反查）
3. 不得为虚构 / 神话 / 未有史实记载的人物建角色
4. 不得大段抄录仍在版权期内的现代白话译本或学术校注

### 3.4 Voice.md 四层结构

见 `prebuilt/master-yinguang/references/voice.md` 作为参照。重点：

> ⚠️ **v0.6 命名约定**：所有新 master 目录与 frontmatter `name:` 必须以 `master-` 开头（如 `prebuilt/master-foo/` + `name: master-foo`）。两个 meta-skill 例外：`compare-masters` 与 `create-master` 保持原状（避免 `/master-compare-masters` 重复前缀）。详见 [CHANGELOG §0.6.0](CHANGELOG.md#060--2026-05-02)。


- **Layer 0 — 硬规则**：[`ETHICS.md` §3](ETHICS.md) 的禁止行为必须原文复制到此
- **Layer 1 — 身份**：生卒、传承、核心立场
- **Layer 2 — 表达风格**：常用比喻、开场方式、称呼
- **Layer 3 — 教学方法**：循序渐进的路径、遇困惑时的处理

### 3.5 Fidelity 测试用例怎么写

`tests/fidelity.jsonl` 每行一个 JSON，字段：

```json
{
  "q": "用户会问的典型问题",
  "must_cite": ["T48n2008", "某经号"],
  "must_mention": ["核心术语1", "核心术语2"],
  "must_not_contain_first_turn": ["学生啊", "师兄"],
  "difficulty": "basic|intermediate|advanced"
}
```

**5 条分布建议：**

- 1 条 `basic` — 宗派入门问题（smoke 会优先跑这条）
- 2 条 `intermediate` — 核心教义（如 "三性" / "信愿行"）
- 1 条 `advanced` — 跨宗派对话 / 批判性问题
- 1 条 boundary 测试 — 试探 "给我授戒 / 印证我开悟了吗" 一类，must_not_contain 检查 AI 是否正确拒绝

### 3.6 Review 过程

PR 提交后：

1. CI 自动跑 validate + fidelity-smoke（抽本 PR 修改的法师做 smoke）
2. 维护者 review 教义准确性 + 风格一致性 + 版权 Tier 判断
3. 如有佛学学者 / 教内法师愿意 review，欢迎在 PR 评论 tag 维护者协调
4. Review 周期：7-14 天（含教内邀请意见）

---

## § 4 修改已有法师

- 小修（typo、措辞）：直接 PR
- 大修（新增教义章节、修改 Layer 1-3 风格）：先开 issue 讨论
- 修改 fidelity 测试用例：**PR description 必须说明新旧用例的差异以及为何新用例更能体现该法师风格**——不要为了让测试通过而放宽标准

---

## § 5 行为准则

见 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)。

本项目涉及佛教内容，请在讨论中：

- 不评判宗派高下
- 不借项目传播个人修行见解
- 不对其他贡献者做教学式 / 居高临下的发言
- 教理争议以学界主流共识 + CBETA 原文为准，而非个人修学经验

---

## § 6 为单 master 补 `lore_triggers`（v0.8）

v0.8 在 `meta.json` 引入 `lore_triggers`，让 runtime 在用户提问命中 keyword 时按需注入一段真实祖师 quote。详细 schema 见 [`docs/persona-schema.md`](docs/persona-schema.md)。

补 entry 的流程：

1. **先有原典**：打开 `prebuilt/master-<slug>/sources/<id>-excerpts.md`，找到一段你想暴露的真实段落。如果 excerpts 里没有合适段落，**不要为了补 entry 而新摘原典**——先开 PR 加 excerpts，再回头补 entry。
2. **content 必须是文献原文**（可在末尾加一句"——"开头的浅释，但不得改写经文本身）。长度 80-300 字。
3. **source_ref**：写本 master `sources[].id` 中的真实 id，可加 `#章名` 锚点（如 `T48n2008#般若品`）。validator 校对前缀。
4. **keys**：用户最自然会用到的提问词，3-6 个为佳。OR 语义。
5. **何时用 `selective: true`**：当 keys 容易在非本主题语境下命中（如"定慧"在大多数佛教讨论里都会出现），用 `secondary_keys` 加副词收窄。validator 强制 secondary_keys 存在时 selective 必须 true。
6. **本地验证**：
   ```bash
   python scripts/validate-persona-fidelity.py
   # 或
   npm run validate:persona-fidelity
   ```
7. **提交 lore_triggers PR 前的自检（v0.8 起强烈建议，v0.9 起 hard gate）**：
   ```bash
   # advisory 模式（与 CI 一致）
   python scripts/validate-lore-triggers-content.py --master master-<slug>
   # 或 npm
   npm run validate:lore-content

   # 强制硬失败（在 PR 提交前本地预演 v0.9 行为）
   python scripts/validate-lore-triggers-content.py --strict --master master-<slug>
   ```
   该 validator 在你的 `content` quote 上做归一化 LCS / SequenceMatcher
   匹配，校验是否真在 `sources/*-excerpts.md` 中找得到。三态：

   - `PASS`：在 sources/ 找到 → 直接提交
   - `WARN`：仅在 references/ 找到 → 强烈建议先扩展 sources/excerpts.md
     使 v0.9 hard gate 启用时仍 PASS
   - `FAIL`：两处都找不到 → **必须**改 content 或扩展 excerpts；这是
     伪造的明显信号

   详细阈值与原理见 [`docs/persona-schema.md`](docs/persona-schema.md#lore_triggers-content-完整性自动验证v08)。
8. PR description 必须列出 entry 数 + 引用来源章节，方便 maintainer 与 excerpts 文件对照。

**禁止**：

- 改写经文（无论"为了易读"还是"为了简洁"）
- 把 secondary teaching（讲记 / 现代释义）冒充原典
- entry > 5 条/master 一次性提交（一次 PR 限制 3-5 entry，保证 reviewer 能逐条核对）

---

## § 7 依赖 PR（Dependabot 自动开）

本仓库自 v0.8 起开启 [Dependabot](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates)，每周一自动开三类依赖升级 PR：

| 生态 | 监控目标 |
|------|---------|
| `github-actions` | `.github/workflows/*.yml` 中所有 SHA-pin 的 actions |
| `npm` | `package.json` 依赖 + workflow 中 `npm install -g promptfoo@<ver>` |
| `pip` | `requirements.txt`（validate / fidelity 工具链） |

**maintainer review 流程**（也欢迎贡献者帮忙跑）：

1. **CI 必须全绿**——所有 required status checks 是依赖更新最可靠的回归信号。
2. **SHA 真实性核对**（仅 github-actions PR）：
   ```bash
   gh api repos/actions/<name>/git/refs/tags/<new-version> --jq '.object.sha'
   ```
   与 Dependabot PR 里写的 SHA 比对，一致才合并。
3. **major bump 不可自动合并**：major 版本通常含 breaking change，必须人工读 release note + 跑 fidelity smoke 确认行为不变。
4. **minor / patch**：CI 绿即可合并，合并方式与本仓库其它 PR 一致——`gh pr merge --merge`（保留 commit 历史）。

如需手动触发一次扫描：仓库 Settings → Code security and analysis → Dependabot → "Check for updates"。

> 报告 Dependabot 误判 / 漏报：开普通 issue，标签选 `dependencies`。

---

## 问题？

- 技术问题 → [Bug Report](https://github.com/xr843/Master-skill/issues/new?template=bug_report.yml)
- 新法师建议 → [New Master Proposal](https://github.com/xr843/Master-skill/issues/new?template=new_master.yml)
- 教界边界疑虑 → [Boundary Violation](https://github.com/xr843/Master-skill/issues/new?template=boundary_violation.yml)（P0，优先处理）
- 一般讨论 → [GitHub Discussions](https://github.com/xr843/Master-skill/discussions)
- 紧急版权下架 → xianren843@protonmail.com（48 小时回复）

感谢你愿意为汉传佛教数字人文贡献一份力。合十。
