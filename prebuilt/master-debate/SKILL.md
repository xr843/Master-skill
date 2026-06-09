---
name: master-debate
description: Use when user explicitly asks for an adversarial / multi-round dialectic between masters — 祖师辩论, 各执一词, 谁更对, debate, 应成 vs 顿悟, 顿渐之争. Differs from /compare-masters (parallel single-round) by being adversarial multi-round via fresh-subagent orchestration. Topics 空有 / 禅净 / 性相 / 戒律 vs 内观 — trigger is adversarial framing: "禅净比较" → compare; "禅净辩论 / 谁更究竟" → here.
version: 0.8.0
license: MIT
kind: meta-skill
verified_by: xr843
verified_at: 2026-06-09
---

# 祖师辩论 (Master Debate) — 元 Skill v0.8

> 本对话依据历史佛教文献生成，对比旨在展现多元视角，不评判优劣。所有教义断言附经证。

## v0.8 执行范式：Orchestrator + Fresh Subagent

**为什么改：** v0.7.1 给 10 个 master 加了 `cross_critique` 字段（覆盖 8 对配对的双向 16 条），但当前 runtime 把 4 轮辩论装在**同一个 LLM context** 里，对方的原话和你自己的草稿同框，立场极易被对方论点污染漂移 —— 反稻草人弹药射不出去。

**怎么改：** 每一轮派**一个全新 subagent**（Task tool，`subagent_type` 用 `general-purpose`），只携带 `{role, opponent_position_summary_<=80字, cross_critique_弹药}`，**不传前序原文**。由外层 orchestrator（本 skill 调用方）维护轮次摘要 + 终止判断 + 最终收束。

这是 obra/superpowers 的 subagent-driven-development 模式 + AutoGen GroupChat selector 在祖师辩论上的落地。

## 决策树：选择哪两位祖师？

### 优先级 1 — 用户显式指定

用户指定 2 位祖师 → 直接使用。

### 优先级 2 — 议题→对立配对兜底表

| 议题关键词 | Master A | Master B |
|-----------|----------|----------|
| 禅净 / 念佛 vs 参禅 | huineng | yinguang |
| 空有 / 中观 vs 唯识 | kumarajiva | xuanzang |
| 顿渐 / 顿悟 vs 次第 | huineng | zhiyi |
| 应成 vs 顿悟 / 中观分判 vs 直指 | tsongkhapa | huineng |
| 戒律行持 vs 直观内观 | ajahn-chah | mahasi-sayadaw |
| 三士道 vs 自性见 | atisha | huineng |
| 教宗天台 vs 行归净土 | ouyi | yinguang |
| 教观纲宗 vs 应成中观 | ouyi | tsongkhapa |

### 优先级 3 — 关键词匹配兜底

从议题中提取关键词，与各 master 的 `meta.json.search_scope.keywords` 匹配，取 top-2 不同传统的 master。

## 名称解析

模板中的 `<Master A 全称>` / `<Master B 全称>` 占位符指**该祖师 `meta.json` 中的 `name` 字段**。例如：

- `huineng` → 慧能大师
- `yinguang` → 印光大师
- `kumarajiva` → 鸠摩罗什
- `xuanzang` → 玄奘法师
- `zhiyi` → 智顗大师
- `tsongkhapa` → 宗喀巴大师
- `ajahn-chah` → 阿姜查
- `mahasi-sayadaw` → 马哈希尊者
- `atisha` → 阿底峡尊者
- `ouyi` → 蕅益大师

未列出的 master 同样从 `prebuilt/master-<slug>/meta.json` 的 `name` 字段读取。

## 阶段 0 — 初始化（Orchestrator 执行）

输入：`{topic, master_A_slug, master_B_slug, max_rounds?}`

1. 读 `prebuilt/master-debate/meta.json` 的 `debate_protocol`：
   - 计算配对 key：把两个 slug **按字典序排序**后用 `-vs-` 拼接（例：`("yinguang", "huineng")` → `huineng-vs-yinguang`；`("tsongkhapa", "huineng")` → `huineng-vs-tsongkhapa`）。注意 slug 自身可含 `-`（如 `ajahn-chah`），lookup 时 **不要** 对 key 做 `split("-vs-")` 再排序，而应该是排好序之后**才**拼接。
   - 若 `per_pair_overrides[key]` 存在 → 用其 `default_rounds`，否则用 `debate_protocol.default_rounds`（=4）
   - `max_rounds` 用户传入则取 `min(用户值, debate_protocol.max_rounds)`，否则用上一步的 default
2. 读 `prebuilt/master-<A>/meta.json` 与 `prebuilt/master-<B>/meta.json` 的 `cross_critique`：
   - `ammo_A_vs_B` = A 的 cross_critique 中 `target_master == B` 的所有 entry
   - `ammo_B_vs_A` = B 的 cross_critique 中 `target_master == A` 的所有 entry
3. **覆盖检查**：若 `ammo_A_vs_B` 或 `ammo_B_vs_A` 为空 → orchestrator 在最终输出顶部打一条 `> ⚠️ 本配对 cross_critique 未双向覆盖，对辩力度可能降级。` **不阻塞流程**。
4. 初始化轮次摘要列表 `round_summaries: list[{round, speaker_slug, summary_<=80字}] = []`。

## 阶段 1..N — 每轮（Orchestrator 每轮派 fresh subagent）

每轮 Orchestrator **必须**通过 Task tool 派一个 fresh subagent，禁止在主 context 续写 master 的发言。

### Subagent prompt 模板

```
你扮演 {master_X_name}（slug: {master_X_slug}）。这是祖师辩论的第 {round_no} 轮。

【对方上一轮立场摘要】
{opponent_summary_<=80字}    # 第 1 轮此项写 "（首轮，对方尚未发言）"

【本轮你的任务】
- R1（立论）：表达本宗对议题「{topic}」的立场 + 3 条核心理由
- Rn 反驳：先**复述**对方上一轮三条原意，再逐条回应，不引新议题
- Rn 回应：接受/部分接受/坚持，并说明
- 末轮综合：双方共许 / 仍异 / 给读者的话

【弹药库 — 至少引用 1 条】
{cross_critique entries 中 target_master = 对方 slug 的所有条目，
 每条格式: position 文 + citation 经号}

【背景资料】（如果该 master meta.json 含 style.qa / signature_phrases，
此处拼入；否则忽略，由 subagent 自查 prebuilt/master-{slug}/references/voice.md）

【硬约束】
1. 300-500 字 zh-Hans
2. 立场坚定但不人身攻击
3. 至少 1 个本宗 citation（CBETA 经号 / Toh / SC uid）
4. 禁稻草人：反驳/回应轮必须先复述对方原意再回应
5. 禁裁决：不写 "X 赢了 / X 更究竟 / 你应该选 X"
6. 禁伪造对话：不虚构两位祖师互相打招呼或具体史实交锋
7. 引经必经查证：citation 必须真实存在于本 master 的 sources[].id

【输出格式】
只输出本轮发言正文（不要 frontmatter / 不要标题 / 不要圆桌叙述）。
```

### Orchestrator 处理

1. 接 subagent 返回的发言原文 → 追加进最终输出。
2. **写一句 ≤80 字的 `round_summary`** 喂给下一轮（该摘要只保留对方"说了什么立场 + 引了什么经"，不复制原文）。
3. 检查终止条件（下节）。

## 终止条件

满足任一即终止：

1. **达到 max_rounds**：默认 4 轮，由 `debate_protocol.default_rounds` 或 per-pair override 决定。
2. **stop_on_consensus**（可选，meta.json 默认 `false`）：双方上一轮都引用了对方关键术语 + 表达认可（启发式：摘要中同时含 "可"/"亦"/"诚然"/"许之" 等 + 对方 master 名 / 弹药关键词）。
3. 终止后 orchestrator 进入「阶段终」。

## 阶段终 — Compare-masters 中立观察

最终输出末尾**必须**调用 `/compare-masters` 风格的中立观察（不需要真的派 subagent，由 orchestrator 自己写 3 句话）：

- 句 1：**分歧本质**（在哪个层面分歧 — 行门 / 见地 / 判教 / 根机）
- 句 2：**共识点**（双方都承认的）
- 句 3：**留给读者**（这不是谁对谁错，而是两条都通的路）

禁止评判对错。

## 输出框架（统一骨架，voice 各自）

```markdown
> 本对话依据历史佛教文献生成，对比旨在展现多元视角，不评判优劣。

## 议题：<topic>

### R1｜<Master A 全称> 立论
（A 的 voice，立场 + 3 条理由 + 至少 1 条 citation）

### R2｜<Master B 全称> 反驳
（B 的 voice，**先复述 A 的三条原意**，再逐条回应 + citation）

### R3｜<Master A 全称> 回应
（A 的 voice，接受 / 部分接受 / 坚持 哪几条 + 说明 + citation）

### R4｜<Master B 全称> 综合
（B 的 voice，给读者的话 + citation）

### 教内余争 — 中立观察
- 分歧本质：<1 句>
- 共识点：<1 句>
- 留给读者：<1 句>
```

## 硬约束（贯穿所有轮）

1. **禁稻草人**：R2 / R3 / 后续反驳/回应轮必须**先复述对方原意**再回应。复述缺失即不合格。
2. **禁裁决**：不写 "X 赢了" / "X 更究竟" / "你应该选 X"。综合环节明示分歧不抹平。
3. **禁伪造对话**：不虚构两位祖师互相打招呼或具体史实交锋（沿用 compare-masters `no_fabricated_dialogue` 边界）。
4. **底部免责**：固定挂在输出顶部（见上方引用框）。
5. **引经必经查证**：所有 CBETA 经号 / SC uid / Toh / 集成开示 id 必须真实，禁止造编号。
6. **Subagent 隔离**：每轮独立 context，禁止在主 context 续写任一 master 的发言。

## 完整样例：顿悟与渐修（huineng vs yinguang，4 轮）

**输入**：`{topic: "顿悟与渐修", master_A_slug: "huineng", master_B_slug: "yinguang"}`

### 阶段 0 — 初始化（orchestrator）

读 `prebuilt/master-debate/meta.json`：
- 配对 key = `huineng-vs-yinguang` → `default_rounds = 4`
- `max_rounds` 用户未指定 → 取 4

读弹药：
- `ammo_A_vs_B`（慧能对印光）：1 条 — `{position: "对净土：本性弥陀，唯心净土；念佛不离自心，即心见佛，何须外求？以无心为有心是诳。", citation: "T48n2008"}`
- `ammo_B_vs_A`（印光对慧能）：1 条 — `{position: "对禅宗：见性须现量证悟，末法众生根机陋劣，难当此任；信愿持名是阿弥陀佛大悲普被，老实念佛即是真见性。", citation: "X62n1182"}`

覆盖完整，不打降级警告。

### 阶段 1 — R1 立论（派 fresh subagent #1：慧能）

Subagent prompt（要点）：

```
你扮演 慧能大师（slug: huineng）。第 1 轮。
【对方上一轮立场摘要】（首轮，对方尚未发言）
【本轮你的任务】R1 立论 — 对议题「顿悟与渐修」给立场 + 3 条核心理由。
【弹药库】
- 对净土：本性弥陀，唯心净土；念佛不离自心，即心见佛，何须外求？以无心为有心是诳。[T48n2008]
【硬约束 略】
```

Subagent 返回正文（300-500 字）→ orchestrator 追加进输出。

Orchestrator 写 R1 摘要（≤80 字）：
> "慧能立顿悟：自性本具菩提，于诸境心不染即见性，渐修是初机假名。引《坛经》。"

### 阶段 2 — R2 反驳（派 fresh subagent #2：印光）

Subagent prompt（要点）：

```
你扮演 印光大师（slug: yinguang）。第 2 轮。
【对方上一轮立场摘要】
慧能立顿悟：自性本具菩提，于诸境心不染即见性，渐修是初机假名。引《坛经》。
【本轮你的任务】R2 反驳 — 先复述慧能三条原意，再逐条回应，不引新议题。
【弹药库】
- 对禅宗：见性须现量证悟，末法众生根机陋劣，难当此任；信愿持名是阿弥陀佛大悲普被，老实念佛即是真见性。[X62n1182]
【硬约束 略】
```

Subagent 返回 → 追加。

Orchestrator 写 R2 摘要：
> "印光承认顿悟为上根直门，然指末法根机陋劣不堪现量证悟；唯老实念佛仗佛力可稳达。引《文钞》。"

### 阶段 3 — R3 回应（派 fresh subagent #3：慧能）

Subagent prompt（要点）：

```
你扮演 慧能大师。第 3 轮。
【对方上一轮立场摘要】
印光承认顿悟为上根直门，然指末法根机陋劣不堪现量证悟；唯老实念佛仗佛力可稳达。引《文钞》。
【本轮你的任务】R3 回应 — 接受 / 部分接受 / 坚持 哪几条 + 说明。
【弹药库】
- 对净土：本性弥陀，唯心净土；念佛不离自心，即心见佛，何须外求？以无心为有心是诳。[T48n2008]
【硬约束 略】
```

Subagent 返回 → 追加。

Orchestrator 写 R3 摘要：
> "慧能部分接受末法根机说，但坚持念佛不离自心，'外求'即非真念，唯心净土与持名不二。"

### 阶段 4 — R4 综合（派 fresh subagent #4：印光）

Subagent prompt（要点）：

```
你扮演 印光大师。第 4 轮（末轮）。
【对方上一轮立场摘要】
慧能部分接受末法根机说，但坚持念佛不离自心，'外求'即非真念，唯心净土与持名不二。
【本轮你的任务】R4 综合 — 双方共许 / 仍异 / 给读者的话。
【弹药库】
- 对禅宗：信愿持名是阿弥陀佛大悲普被，老实念佛即是真见性。[X62n1182]
【硬约束 略】
```

Subagent 返回 → 追加。

### 阶段终 — 中立观察（orchestrator 自己写）

```
### 教内余争 — 中立观察
- 分歧本质：见地层（自性本具 vs 仗佛慈力）与根机判（顿门为通门 vs 持名为末法稳门）。
- 共识点：所证不二，皆归一心；老实修行优于解会。
- 留给读者：禅与净不是 A or B，是同一心地的两个入口 — 哪个让你少打妄想就走哪个。
```

## 与 `/compare-masters` 的边界

- `compare-masters`：横向并列、单轮、单 context、即时回答
- `master-debate`：纵向交锋、N 轮、**每轮 fresh subagent**、暴露分歧
- 关键词正交：`对比 / 比较 / 各宗看法` → compare；`辩论 / 各执一词 / 谁更对` → debate
