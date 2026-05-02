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

- [ ] CI 绿色（validate / fidelity-smoke 必过；forks 无 API key 会 skip 并 warning，OK）
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

## 问题？

- 技术问题 → [Bug Report](https://github.com/xr843/Master-skill/issues/new?template=bug_report.yml)
- 新法师建议 → [New Master Proposal](https://github.com/xr843/Master-skill/issues/new?template=new_master.yml)
- 教界边界疑虑 → [Boundary Violation](https://github.com/xr843/Master-skill/issues/new?template=boundary_violation.yml)（P0，优先处理）
- 一般讨论 → [GitHub Discussions](https://github.com/xr843/Master-skill/discussions)
- 紧急版权下架 → xianren843@protonmail.com（48 小时回复）

感谢你愿意为汉传佛教数字人文贡献一份力。合十。
