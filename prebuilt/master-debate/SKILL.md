---
name: master-debate
description: Use when user explicitly asks for an adversarial / multi-round dialectic between masters — keywords like 祖师辩论, 各执一词, 谁更对, 辩论一下, debate, 应成 vs 顿悟, 顿渐之争. Differs from /compare-masters (parallel single-round) by being adversarial 4-round (claim → rebut → respond → synthesize + 教内余争). Topical contexts where this fits include 空有 / 禅净 / 性相 / 戒律 vs 内观, but the trigger is the adversarial framing, not the topic alone — bare "禅净比较" goes to /compare-masters; "禅净辩论 / 谁的见地更究竟" goes here.
version: 0.7.0
license: MIT
kind: meta-skill
verified_by: xr843
verified_at: 2026-06-06
---

# 祖师辩论 (Master Debate) — 元 Skill

> 本对话依据历史佛教文献生成，对比旨在展现多元视角，不评判优劣。所有教义断言附经证。

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

## 批判点注入（v0.7.1）

选定配对 (A, B) 后，runtime **必须**：

1. 读 `prebuilt/master-<A>/meta.json` 的 `cross_critique`，筛选 `target_master == B` 的 entry
2. 读 `prebuilt/master-<B>/meta.json` 的 `cross_critique`，筛选 `target_master == A` 的 entry
3. 把筛到的 `position` 文 + 对应 `citation` 当作"本祖师对对方的标准立场"上下文注入：
   - R1（A 立论）：A 关于 B 的立场，作为立论时区别于 B 的依据
   - R2（B 反驳）：B 关于 A 的立场，作为反驳 A 立论的 grounding
   - R3（A 回应）：A 再次引用本人立场
   - R4（B 综合）：B 引用以呈现"教内余争"中的"仍异"

若任一 master 的 `cross_critique` 缺对应 entry，注入留空——退回到「禁稻草人」+「引经必经查证」硬约束兜底，**不阻塞流程**。

## 轮次结构（固定 4 轮 + 综合）

| 轮 | 角色 | 内容 | 引经 |
|---|------|------|------|
| R1 | Master A 立论 | 议题 → 立场 → 3 条核心理由 | ≥1 条 citation |
| R2 | Master B 反驳 | 针对 R1 三条**逐条**回应，不引新议题 | ≥1 条 |
| R3 | Master A 回应 | 接受/部分接受/坚持 + 说明 | ≥1 条 |
| R4 | Master B 综合 | 双方共许 / 余争 / 用户该如何理解 | ≥1 条 |

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

### 教内余争
- 双方共许：<list>
- 仍异之处：<list>
```

## 硬约束

1. **禁稻草人**：R2 / R3 必须**先复述对方原意**再回应。复述缺失即不合格。
2. **禁裁决**：不写 "X 赢了" / "X 更究竟" / "你应该选 X"。综合环节明示分歧不抹平。
3. **禁伪造对话**：不虚构两位祖师互相打招呼或具体史实交锋（沿用 compare-masters `no_fabricated_dialogue` 边界）。
4. **底部免责**：固定挂在输出顶部（见上方引用框）。
5. **引经必经查证**：所有 CBETA 经号 / SC uid / Toh / 集成开示 id 必须真实，禁止造编号。

## 与 `/compare-masters` 的边界

- `compare-masters`：横向并列、单轮、即时回答
- `master-debate`：纵向交锋、4 轮、暴露分歧
- 关键词正交：`对比 / 比较 / 各宗看法` → compare；`辩论 / 各执一词 / 谁更对` → debate
