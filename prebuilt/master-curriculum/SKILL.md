---
name: master-curriculum
description: Use when user asks for a sequenced learning path within a Buddhist tradition — 学修次第, 先学什么, 从哪入门, 下一步读什么, curriculum, 学习计划, 路径推荐. Differs from /compare-masters (parallel opinion) and /master-debate (adversarial dialectic) by being 纵向 / 时序: stage-by-stage plan keyed on tradition × level (L0-L3) → foundation → intermediate → advanced + blind spots. Trigger is planning intent — "禅宗对比" goes to /compare-masters; "禅宗从哪开始学" goes here.
version: 0.7.0
license: MIT
kind: meta-skill
verified_by: xr843
verified_at: 2026-06-06
---

# 学修路径 (Master Curriculum) — 元 Skill

> 本路径依据历史佛教文献生成，仅供学习参考。如需正式修行指导，请亲近善知识。

## 决策树：选择哪份路径？

### 优先级 1 — 用户显式指定传统

| 用户说 | 加载 reference |
|--------|---------------|
| 禅宗 / 禅 / 见性 | `references/chan.md` |
| 净土 / 念佛 / 弥陀 | `references/jingtu.md` |
| 天台 / 止观 | `references/tiantai.md` |
| 华严 / 一真法界 | `references/huayan.md` |
| 唯识 / 法相 / 瑜伽行 | `references/weishi.md` |
| 三论 / 中观 / 般若 | `references/sanlun-zhongguan.md` |
| 格鲁 / 应成 / 道次第 | `references/gelug-madhyamaka.md` |
| 上座部 / 内观 / vipassana | `references/theravada-vipassana.md` |

### 优先级 2 — 关键词匹配

从用户输入抽取关键词，匹配每份 reference 顶部的 `## 触发关键词` 列表，取最高分。若用户说"什么传统都行 / 综合理论"，按 keyword density 给一份**默认推荐**而非平均加载。

### 优先级 3 — 兜底（无 reference 命中）

若全部 reference 关键词分数均为 0（典型例：噶举 / 米拉日巴 / 真言宗 / 黄檗 / 等暂未提供路径的传统），**不要**用任何 reference。明确告诉用户本传统尚无 curriculum 路径，并建议改用对应单 master skill（如 `/master-milarepa`）或先 `/compare-masters` 横向了解后再选定方向。禁止套用错误传统的路径。

## 输入收集（缺则反问）

1. **目标传统/法门** — 必填
2. **当前位置**（必填，缺则反问）：
   - **L0** 完全零基础
   - **L1** 读过白话简介
   - **L2** 能读基本经论但缺次第
   - **L3** 有专修但想深入对比
3. **现实约束**（可选）：每周可投入时间 / 母语限制（文言/巴利/藏文）/ 有无指导老师

## 输出框架（统一模板）

```markdown
> 本路径依据历史佛教文献生成，仅供学习参考。如需正式修行指导，请亲近善知识。

## 你的学修路径：<传统> · 从 L<n> 开始

### 一、根基（入门，建议 N 周）
- **主用经/论**：《<经名>》【<cbeta_id 或 sc_uid>】
- **推荐 master**：`/master-<slug>` — <此阶段教什么>
- **目标**：能用自己的话讲清 <3 个核心概念>

### 二、深入（进阶，M 周）
- 主用经/论 + 配合 master + 关键议题

### 三、精研（专修，长期）
- 主用经/论 + 配合 master + 验收标准

### 四、可能的盲点
（本传统初学者最易踩 2-3 个陷阱 + 各祖师对此的提醒）

### 延伸
- 交叉对比 → `/compare-masters`
- 了解争议 → `/master-debate`
```

## 硬约束

1. **引经必经查证**：所有 CBETA 经号 / SC uid / Toh / 集成开示 id 必须真实存在于某 master `meta.json.sources`。CI 通过 `scripts/validate-curriculum-sources.py` 强制。
2. **推荐 master 必须存在**：`/master-<slug>` 必须指向已存在的 `prebuilt/master-<slug>/`。
3. **不抹平传统差异**：哪怕用户问"综合"，也按传统分别给路径，禁止造混合体。
4. **不替善知识**：盲点和精研环节必须明确提示"亲近善知识"。
5. **L0 起手不灌输宗派优越**：第一阶段教法描述保持中性、传统内部声音。

## 与 `/compare-masters` 和 `/master-debate` 的边界

- `compare-masters` = 横向并列（多家看一题，单轮）
- `master-debate` = 多轮交锋（看分歧）
- `master-curriculum` = **纵向时序**（按月按季规划学什么）
- 关键词正交：`次第 / 先学 / 路径 / 计划 / 入门` → curriculum；不与 compare/debate 重叠。
