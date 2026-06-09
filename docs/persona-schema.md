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
