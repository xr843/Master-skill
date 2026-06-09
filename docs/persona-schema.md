# Persona-Fidelity Schema (v0.8)

本文件描述 v0.8 在每个 `prebuilt/master-<slug>/meta.json` 上新增的三个字段。其目的：把"祖师声音的可辨识特征"显式编码进 meta，让 fidelity 测试有锚点，让 runtime 在用户问题命中时按需注入真实祖师 quote，从而降低 LLM 在 persona 任务上常见的"风格漂白"和"看似有道理但其实出处全无"两类失败。

设计参考了两个先例：

- **elizaOS characterfile** —— bio + lore + style 三块解耦，让 character 与对话引擎解耦。本项目借鉴 style 三套口径与可热替换的设计。
- **SillyTavern Character Book v3 (chara_card_v3)** —— `keys` + `secondary_keys` + `selective` 触发器布尔逻辑，让 lore 段落条件注入而不污染上下文窗口。本项目沿用其 trigger 规则，但**所有 content 必须是真实文献 quote**，不接受作者改写。

我们没有照抄上述 spec 中的字段名（如 `mes_example` / `entries`）——为 Master-skill 的引用义务做了简化和加固。

---

## 三个新字段

### 1) `signature_phrases` （**required**，3-7 项）

`string[]`，该祖师的高频签名短语 / 偈颂关键词。fidelity 测试可用它判定一次回答是否"听起来像本祖师"。每条非空字符串。

示例（master-huineng）：

```json
"signature_phrases": [
  "本来无一物",
  "明心见性",
  "不立文字",
  "无念为宗",
  "定慧一体",
  "烦恼即菩提",
  "何期自性"
]
```

### 2) `style` （**required**）

固定三键 dict，每个 string 长度在 30-80 字之间，简体中文：

| 键 | 用途 |
|---|---|
| `all` | 该祖师的通用语气特征——任何回答都应有的底色 |
| `qa` | 答疑短句风格——对一问一答场景的具体语气 |
| `monologue` | 上堂开示风格——较长篇幅、自定义节奏时的结构 |

不允许多余键（schema 严格化，避免 PR 时塞进未审项）。

示例（master-zhiyi）：

```json
"style": {
  "all": "系统论述体，层次分明，逻辑严密；以判教思维统摄诸说，先分后合，义理与实修并重不空谈。",
  "qa": "先以判教定位所问属何教何理，次分十乘十境之纲，末归一念三千之实，绝不孤悬一边。",
  "monologue": "上堂依五时八教纲领开列，举一念心具十法界十如三世间，归结於圆顿止观一心三观之实修。"
}
```

### 3) `lore_triggers` （**optional**）

`list[dict]`，命中触发器时注入一段真实祖师 quote。每条结构：

| 字段 | 必/选 | 说明 |
|---|---|---|
| `keys` | 必 | `string[]`，主触发词（OR 关系：任一命中即激活，除非 selective=true）|
| `secondary_keys` | 选 | `string[]`，副触发词；存在时**必须**同时 `selective: true` |
| `selective` | 选 | `bool`；true 时含义切换为"必须同时命中主词 AND 副词" |
| `content` | 必 | `string`，真实祖师 quote，80-300 字 |
| `source_ref` | 必 | `string`，指向本 master 的 `sources[].id`；允许 `#anchor` 后缀指向具体章节 |

**Iron rule**：`content` 必须是 sources/ 下 excerpts 文件中可核对的原典段落。**严禁伪造 quote**。如果该祖师的 excerpts 没有适合某主题的段落，`lore_triggers` 留空即可——validator 不强制此字段。

#### 完整示例（master-huineng）

```json
"lore_triggers": [
  {
    "keys": ["本来无一物", "菩提本无树", "明镜亦非台"],
    "content": "菩提本无树，明镜亦非台。本来无一物，何处惹尘埃。——此偈非否定身心，乃显自性本来空寂，无一法可得，无一尘可染。若於此处会得，则知一切修行皆为破除颠倒，自性本来圆成。",
    "source_ref": "T48n2008#行由品"
  },
  {
    "keys": ["定慧", "止观"],
    "secondary_keys": ["分", "先后"],
    "selective": true,
    "content": "定慧一体，不是二。定是慧体，慧是定用。即慧之时定在慧，即定之时慧在定。若识此义，即是定慧等学。——定慧如灯与光，灯是光之体，光是灯之用，不可说先后。",
    "source_ref": "T48n2008#定慧品"
  }
]
```

第一条：用户问到"本来无一物 / 菩提本无树 / 明镜亦非台"任一时注入。

第二条：只在用户**同时**提到"定慧 / 止观"和"分 / 先后"时才注入——这种 selective 模式专门用于消歧（避免一切提到"定慧"的提问都触发"先后辨"片段）。

---

## 触发器逻辑（按命中优先级）

```
for trigger in lore_triggers:
    if trigger.selective:
        primary_hit = any(k in user_query for k in trigger.keys)
        secondary_hit = any(k in user_query for k in trigger.secondary_keys)
        if primary_hit AND secondary_hit:
            inject(trigger.content)
    else:
        if any(k in user_query for k in trigger.keys):
            inject(trigger.content)
```

实际 runtime（fojin.app/chat 或 Claude Code SKILL.md hook）可在此基础上加 dedup、上下文窗预算等优化，但**判定规则不变**——这是 schema 部分，不是 runtime 部分。

---

## 与现有字段的关系

- `search_scope.keywords` —— 决定"用户提问是否归到本 master"。`signature_phrases` 决定"本 master 已经说话了，听起来像不像他"。两者不冲突，可有重叠但目的不同。
- `cross_critique` —— 跨派批驳，仅在 `/master-debate` 中加载。`lore_triggers` 是单 master 任意场合按需注入。
- `starter_questions` —— UI 引导。新字段不替代它。

---

## CI 校验

- `python scripts/validate-persona-fidelity.py` —— 离线结构校验
- `npm run validate:persona-fidelity` —— 同上
- `npm run validate` / `npm test` 自动包含本检查
- 27 个单元测试位于 `scripts/tests/test_validate_persona_fidelity.py`

3 个 meta-skill（`compare-masters` / `master-debate` / `master-curriculum`）无 `meta.json`，自然跳过。

---

## 后续扩展（不在本 PR 中）

- 把 `lore_triggers` 补满所有 14 master——每条都需要在 sources/ 里核对真实 quote，工作量大，分多个 PR 推进。
- runtime injector：在 `prebuilt/master-<slug>/SKILL.md` 顶部加一段"命中 lore_trigger 时执行注入"的硬规则，让所有 frontend 自动遵循。
- fidelity 评测器接入 `signature_phrases`：在 `scripts/test-fidelity.py` 中加 must_use_signature 断言。

---

## 配套评测层：`tests/persona/` (v0.8)

本 schema 字段不是装饰——它们被 [`tests/persona/`](../tests/persona/README.md)
下的 [promptfoo](https://promptfoo.dev) `llm-rubric` 评测直接消费：

- `signature_phrases` —— 在 `contains-any` 断言里做"是否听起来像本祖师"
  的硬锚点。所有 `contains-any` 的 value **必须**在该 master 的
  `signature_phrases`（或显式 curated 白名单）内，否则
  `scripts/validate-promptfoo-configs.py` 会报错。
- `style.qa` —— 直接被复制进 persona prompt 模板，作为答疑节奏锚点。
  schema 改动会立即反映到评测 prompt。
- `lore_triggers` —— 当前评测层尚未直接消费；预留给后续 runtime injector
  落地后的"trigger 命中后回答必须包含 quote"断言。

评测维度：RAW（基础指令 / 拒答能力） / SPE（本宗专属知识忠实度） /
CUS（说话风格忠实度），详见 [tests/persona/README.md](../tests/persona/README.md)。

---

## lore_triggers content 完整性自动验证（v0.8）

### 动机

PR #32 引入 `lore_triggers` schema 后，自评审过程中**手动**抓到并删除
了一条伪造的"念佛是谁"引文（被错误归属 `T48n2008`）。下一次未必能凭
运气拦截，所以 v0.8 后续 PR 引入了
`scripts/validate-lore-triggers-content.py`：**每一条 `content` quote
必须能在该 master 的 sources/excerpts 文件中高相似度地找到**，否则 CI
报警。

### 算法

对每个 `prebuilt/master-<slug>/meta.json` 的每条 `lore_triggers[]`：

1. 从 `content` 中抽出 quote 主体（剥掉 `——` 之后的编者注释 gloss）
2. 在 `prebuilt/<master>/sources/*-excerpts.md` 中按 `source_ref` 的
   CBETA id（长形 `T46n1911` 和短形 `T1911` 两种都试）优先排序候选
3. 文本规范化：去标点 / 去空格换行 / 繁简体 30 字映射归一
4. 计算
   - 最长公共子串长度（LCS）
   - SequenceMatcher 相似度比率（对长文本按 2×quote_len 滑窗）
5. **通过条件**（满足任一即可）：
   - LCS ≥ `min(40, 0.85 × quote_len)`（短 quote 按比例覆盖，长 quote 按绝对窗口）
   - 或 SequenceMatcher ratio ≥ 0.75

### 三态结果

| 状态 | 含义 | 处理 |
|---|---|---|
| `PASS` | 在 sources/excerpts 找到高相似度匹配 | 无操作 |
| `WARN` | 在 references/ 找到但 sources/excerpts 缺 | 建议补 excerpts（不阻塞 CI） |
| `FAIL` | 两处都找不到（疑似伪造或严重不全） | 必须人工核对原典 |

### 阈值取舍

阈值是对 PR #32 当下 7 条真实 entry 校准出来的：

- `MIN_LCS_ABS=40`：长 quote（80+ 字）只需 40 字连续匹配——容忍 CBETA
  分段差异和编辑注释的少量改写。
- `MIN_LCS_FRAC=0.85`：短 quote（30-50 字）必须近乎逐字匹配，避免阈值
  对短引文过松。
- `MIN_RATIO=0.75`：作为兜底——LCS 不达标但全文相似度高（例如多段跳跃
  匹配）时仍能通过。

### Advisory 期窗口

v0.8.x **advisory 模式**：CI 打 warning 但不 block。给作者一个发现并
修复预存量的窗口。**v0.9 起转 hard gate**。

### 本地调用

```bash
# advisory 模式（与 CI 一致）
python scripts/validate-lore-triggers-content.py

# 等价 npm
npm run validate:lore-content

# 强制硬失败模式（v0.9 之前用于本地预演）
python scripts/validate-lore-triggers-content.py --strict

# 限定单 master
python scripts/validate-lore-triggers-content.py --master master-huineng

# JSON 输出（机器可读）
python scripts/validate-lore-triggers-content.py --json
```

### 故意伪造 vs 真 quote 但 excerpts 不全

validator 区分两类问题：

- **真伪造**：quote 在 sources/、references/ 都找不到 → FAIL
- **真 quote 但 sources/excerpts 不全**：能在 references/teaching.md
  找到但 sources/excerpts 缺 → WARN（advisory 提示，建议下一个 PR 补
  excerpts，不算"造假"）

这条边界很重要——禅宗经常出现一条祖师机锋只在二手注释文献而非原典
节选里出现的情况。WARN 比 FAIL 温和，避免把"corpus 不全"误报为"造假"。

### 已知 advisory 状态（v0.8 上线时）

| Master | source_ref | LCS | ratio | 状态 |
|---|---|---|---|---|
| huineng #0 | T48n2008#行由品 | 20 (need 17) | 0.667 | WARN（references only） |
| huineng #1 | T48n2008#定慧品 | 29 (need 40) | 0.44 | FAIL（excerpts 节选不全） |
| huineng #2 | T48n2008#定慧品 | 45 (need 38) | 0.667 | PASS |
| xuyun #0   | T19n0945#卷六 | 32 (need 27) | 0.667 | PASS |
| xuyun #1   | T48n2008#定慧品 | 49 (need 40) | 0.667 | PASS |
| zhiyi #0   | T46n1911#卷五上 | 56 (need 40) | 0.525 | PASS |
| zhiyi #1   | T46n1911#卷五上 | 61 (need 40) | 0.658 | PASS |

两个 advisory 项均为真实坛经文字，**不是伪造**——是 sources/excerpts.md
节选不全。后续 PR 应当补全 excerpts，使 v0.9 hard gate 启用时全部 PASS。
