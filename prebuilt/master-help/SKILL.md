---
name: master-help
description: 'Use ONLY when the user says they do not know which master or which teaching mode to use — 不知道问谁, 该找哪位祖师, 该用哪个模式, 有哪些法师, which master should I ask, help me choose. This is a router, not a teacher: it names a destination and stops. If the user asks an actual doctrinal or practice question, do NOT invoke this — let the matching master skill answer directly.'
version: 0.11.0
license: MIT
kind: meta-skill
verified_by: xr843
verified_at: 2026-07-20
---

# 该问谁 (Master Help) — 路由 Skill

> 本 skill 只做导航，不讲教义。选定目标后立即交棒，不要代替祖师回答。

## 唯一职责

用户不知道该用哪位祖师 / 哪个教学模式时，给出目标并停手。

**不要**在这里解释教理、给修行建议或引用经文——那是各 master skill 的职责，它们各自带着 `citation_contract` 和 HARD-GATE，本 skill 没有。

## 数据源

路由表在仓库根的 `routing.json`（`mode_rules` / `topic_pairings` / `default_pairing`），
祖师关键词在各 `prebuilt/<slug>/meta.json` 的 `search_scope.keywords`。
两处都是机器可读的单一数据源——**不要凭记忆列举祖师或关键词**，读文件。

确定性实现同样可用：

```
master-skill recommend "<用户原话>" --json
```

能跑就跑它，把结果转述给用户；跑不了再按下面的顺序人工走一遍。

## 路由顺序（短路，不可乱序）

与 `routing.json.mode_rules` 的 `order` 一致：

```
1. 命中「学习计划 / 入门 / 先学什么 / 从哪开始 / 按什么顺序」 → /master-curriculum
2. 命中「辩论 / 谁更对 / 高下 / 之争 / 之辩 / 分判」          → /master-debate
3. 命中「对比 / 比较 / 不同 / 异同 / 各派怎么看」              → /compare-masters
4. 都不命中 → 单位祖师：按 meta.json search_scope.keywords 打分
5. 仍无命中 → routing.json.situations 白话状况层
6. 仍无命中 → routing.json.topic_pairings 主题配对
7. 再无命中 → routing.json.default_pairing
```

第 5 步是给**说不出术语的人**用的。`search_scope.keywords` 是教理检索词，
新手不会打"四念处"，他会打"坐不住"。用户描述的是**感受**（妄念 / 看不懂 /
无力感 / 想学最朴素的）而非**主题**时，走这一层。

第 4 步打分规则：关键词**长度 ≥ 2** 才计分（单字 `空` `戒` `定` `慧` `苦` `禅` `业`
会在日常汉语里误命中，已被 `min_keyword_length` 排除）；命中数高者优先；
平局时**优先不同传统**，仍平局按 slug 字典序。最多 3 位。

## 输出格式

```
你的问题看起来是 {判断}，建议：

  /{目标}  — {一句话理由}

（其他可选：{备选1}、{备选2}）
```

三行以内说完。用户要的是入口，不是综述。

## 边界

- 用户已经说清楚要问谁时，**不要**触发本 skill，直接让目标 skill 接手
- 不评价祖师高下，不说"某位更究竟"——这条与 `/compare-masters` 的 HARD-GATE 一致
- 推荐落到密法相关祖师（atisha / tsongkhapa / milarepa）时，照常交棒，
  由目标 skill 自己的边界规则处理密法内容
- 路由结果不确定时，宁可给 2 个候选让用户选，也不要猜死一个

## Quick Reference — 15 位祖师按传统

| 传统 | 祖师 |
|------|------|
| 印度 | master-nagarjuna |
| 汉传 | master-kumarajiva · master-zhiyi · master-fazang · master-xuanzang · master-huineng · master-yinguang · master-ouyi · master-xuyun |
| 藏传 | master-atisha · master-tsongkhapa · master-milarepa |
| 南传 | master-buddhaghosa · master-mahasi-sayadaw · master-ajahn-chah |

> 此表仅供快速定位。判断该选谁时以 `routing.json` 与各 `meta.json` 为准。
