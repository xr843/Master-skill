# Master-skill v0.7 — `/master-debate` + `/master-curriculum` 设计

> 2026-06-06 · 在 v0.6（15 位三大传统祖师、统一 `/master-<slug>` slash 前缀）基础上新增两个**教学模式**元 skill：祖师辩论（多轮交叉）与学修路径（有时序）。**纯增量**：不动单个 master skill，不接 fojin 在线 API，与 `compare-masters` 互补。

---

## 0. 一句话

`compare-masters` 横向并列，`master-debate` 多轮交叉，`master-curriculum` 纵向时序——三者构成教学模式三角，分别覆盖"同时看多家"、"看分歧"、"看下一步学什么"。

---

## 1. 现状（实测 grounding）

| 组件 | 状态 |
|---|---|
| 15 个 `prebuilt/master-<slug>/` skill | 已上线 v0.6，每个含 SKILL.md / meta.json / references / sources / tests/fidelity.jsonl |
| `prebuilt/compare/` 元 skill | 已上线，按"问题主题↔配对祖师"表选 master，做并列对比 |
| 顶层 `SKILL.md` | `/create-master` 入口，含"对比模式"一节 |
| `scripts/validate-fidelity.py` | jsonl 结构 + boundary/pressure 枚举校验，离线纯结构验证 |
| `scripts/test-fidelity.py` | 真正跑 master 测试（需 API key，可 dry-run） |
| `.version-bump.json` | 同步 package.json + 4 个 plugin manifest 版本 |
| npm publish workflow | 已配，但 NPM_TOKEN 已 revoke 待重签（不本轮触发） |

---

## 2. 目标 / 非目标

**目标**：
- 上线 `/master-debate`：祖师就争议性议题进行 4 轮交叉辩论（立论→反驳→回应→综合），输出"教内余争"
- 上线 `/master-curriculum`：根据用户传统、当前位置、约束，输出"根基→深入→精研→可能的盲点"四段学修路径
- 与现有 `compare-masters` / 各 master skill 完全并列，零回归面

**非目标**：
- 不改单个 master skill（meta.json / SKILL.md / references / sources / tests 全部不动）
- 不接 fojin 在线 RAG（保持 v0.6 离线可用特性；v0.8 再做可选增强）
- 不写 `cross_critique` 字段——那是 v0.7.1（路径 B 增量），本期路径 A 仅靠 SKILL.md 内"不许稻草人"约束保障
- 不触发 npm publish（NPM_TOKEN 未重签）

---

## 3. 架构（新增 2 个元 skill）

```
prebuilt/
├─ compare/              ← 已有（不动）
├─ master-debate/        ← 新
│  ├─ SKILL.md
│  └─ tests/
│     └─ fidelity.jsonl
└─ master-curriculum/    ← 新
   ├─ SKILL.md
   ├─ references/
   │  ├─ chan.md                       # 禅宗路径
   │  ├─ jingtu.md                     # 净土
   │  ├─ tiantai.md                    # 天台
   │  ├─ huayan.md                     # 华严
   │  ├─ weishi.md                     # 法相唯识
   │  ├─ sanlun-zhongguan.md           # 三论 / 中观
   │  ├─ gelug-madhyamaka.md           # 格鲁 · 应成中观
   │  └─ theravada-vipassana.md        # 上座部内观
   └─ tests/
      └─ fidelity.jsonl
```

**复用现有数据**：
- 选 master：复用每位 master `meta.json.search_scope.keywords`
- 输出引经：复用 `citation_format`
- 推荐经/论：复用 master `meta.json.sources`
- 决策树兜底：复用 `compare-masters` 已有"问题主题↔配对祖师"表（debate 在此基础上加对立专属配对）

**改动现有文件**（仅 3 处）：
- 顶层 `SKILL.md`：把"对比模式"一节扩为"教学模式"，列三个命令
- `README.md` / `README_EN.md`：对应章节同步
- `scripts/validate-fidelity.py`：`VALID_BOUNDARIES` 加 3 个新值（见 §6）

---

## 4. `/master-debate` 详细设计

### 4.1 触发

- 显式：`/master-debate <议题>`
- 自然语言：用户问争议性议题，关键词命中 `辩论` / `祖师辩论` / `各执一词` / `谁更对` / `debate` / `空有之争` / `禅净之争` / `性相之辩` / `顿渐之争` / `应成 vs 自续`

### 4.2 Master 选型决策树

1. **用户显式指定** → 直用
2. **议题→对立配对兜底表**（写在 debate SKILL.md 内）：

   | 议题关键词 | Master A | Master B |
   |---|---|---|
   | 禅净 / 念佛 vs 参禅 | huineng | yinguang |
   | 空有 / 中观 vs 唯识 | kumarajiva | xuanzang |
   | 顿渐 / 顿悟 vs 次第 | huineng | zhiyi |
   | 应成 vs 顿悟 / 中观分判 vs 直指 | tsongkhapa | huineng |
   | 戒律行持 vs 直观内观 | ajahn-chah | mahasi-sayadaw |
   | 三士道 vs 自性见 | atisha | huineng |
   | 教宗天台 vs 行归净土 | ouyi | yinguang |

3. **兜底**：取议题 keywords 强匹配 top-2 且不同传统的 master

### 4.3 轮次（固定 4 + 综合）

| 轮 | 角色 | 内容 | 引经要求 |
|---|---|---|---|
| R1 | A 立论 | 议题→立场→3 条核心理由 | ≥1 条 citation |
| R2 | B 反驳 | 针对 R1 三条**逐条**回应，不引新议题 | ≥1 条 |
| R3 | A 回应 | 接受/部分接受/坚持 + 说明 | ≥1 条 |
| R4 | B 综合 | 双方共许 / 余争 / 用户该如何理解 | ≥1 条 |

### 4.4 输出框架（统一骨架，voice 各自）

```markdown
> 本对话依据历史佛教文献生成，对比旨在展现多元视角，不评判优劣。

## 议题：<topic>

### R1｜<Master A> 立论
（A 的 voice，立场 + 3 理由 + 至少 1 条 citation）

### R2｜<Master B> 反驳
（B 的 voice，**复述 A 三条原意**后逐条回应 + citation）

### R3｜<Master A> 回应
（A 的 voice，接受/部分接受/坚持哪几条 + citation）

### R4｜<Master B> 综合
（B 的 voice，给读者的话 + citation）

### 教内余争
- 双方共许：<list>
- 仍异之处：<list>
```

### 4.5 约束（写进 debate SKILL.md）

- **禁稻草人**：R2/R3 必须**先复述对方原意**再回应。复述缺失即不合格。
- **禁裁决**：不写 "X 赢了" / "X 更究竟" / "你应该选 X"。综合环节明示分歧不抹平。
- **禁伪造对话**：不虚构两位祖师"互相打招呼"或具体史实交锋（沿用 compare-masters 已有 boundary `no_fabricated_dialogue`）。
- **底部免责**：固定挂在顶部（见 §4.4 引用框）。

---

## 5. `/master-curriculum` 详细设计

### 5.1 触发

- 显式：`/master-curriculum`
- 自然语言：`学修次第` / `先学什么` / `从哪入门` / `下一步读什么` / `curriculum` / `学习计划` / `路径推荐` / `想学 X 但不知从哪开始`

### 5.2 输入（三项；缺则反问）

1. **目标传统/法门**：禅宗 / 净土 / 中观 / 唯识 / 华严 / 天台 / 格鲁中观 / 上座部内观 / 跨传统理论
2. **当前位置**：
   - L0 完全零基础
   - L1 读过白话简介
   - L2 能读基本经论但缺次第
   - L3 有专修但想深入对比
3. **现实约束**（可选）：每周可投入时间、母语限制（文言/巴利/藏文能否读）、有无指导老师

### 5.3 输出骨架（统一模板）

```markdown
> 本路径依据历史佛教文献生成，仅供学习参考。如需正式修行指导，请亲近善知识。

## 你的学修路径：<传统> · <从 L? 开始>

### 一、根基（入门，建议 N 周）
- **主用经/论**：《<经名>》【<cbeta_id>/sc_uid】
- **推荐 master**：`/master-<slug>` — <此阶段教什么>
- **目标**：能用自己的话讲清 <3 个核心概念>

### 二、深入（进阶，M 周）
- 主用经/论 + 配合 master + 关键议题

### 三、精研（专修，长期）
- 主用经/论 + 配合 master + 验收标准

### 四、可能的盲点
（本传统初学者最易踩 2-3 陷阱 + 各祖师对此的提醒）

### 延伸
- 交叉对比 → `/compare-masters`
- 了解争议 → `/master-debate`
```

### 5.4 内容来源（v0.7 全部离线）

- 8 份 `references/<traditon>.md` 由人工编写
- 每份骨架引用的所有 `cbeta_id` / `sc_uid` 必须**真实存在于某个 master `meta.json.sources`**（CI 强制 cross-check，见 §6.3）
- 路径的"配合 master"必须指向**已存在的** `/master-<slug>`

### 5.5 与 compare-masters 边界

- compare = 横向并列 / 即时回答 / 单轮
- curriculum = 纵向时序 / 规划下个月 / 多阶段
- 决策树兜底逻辑互不重叠（关键词 `对比/比较/各宗/不同` → compare；`次第/先学/路径/计划/入门` → curriculum）

---

## 6. 测试与 fidelity gate

### 6.1 `prebuilt/master-debate/tests/fidelity.jsonl`

至少 8 个 case，覆盖：
- 4 个正例（禅净 / 空有 / 顿渐 / 应成 vs 顿悟），含 `must_select_pair` / `must_have_rounds: ["R1","R2","R3","R4"]` / `must_have_sections: ["教内余争"]` / `must_cite_per_round: true`
- 4 个 boundary：
  - `no_winner_judgment`：`must_not_contain: ["谁赢了","X 更究竟","你应该学 X"]`
  - `no_strawman`：要求 R2 必须含 R1 立论关键词的复述（结构性检查）
  - `no_fabricated_dialogue`（复用 compare）
  - `sectarian_judgment`（复用 compare）

### 6.2 `prebuilt/master-curriculum/tests/fidelity.jsonl`

至少 8 个 case：
- 6 个正例（每个主要传统至少 1），含 `must_have_sections: ["根基","深入","精研","可能的盲点"]` / `must_cite_only_existing_sources: true` / `must_recommend_existing_master: true`
- 2 个 boundary：
  - `no_fabricated_curriculum`：`must_not_contain: ["《某未列经》","/master-未存在"]`
  - `neutral_first_turn`：L0 用户得到的不是宗派灌输

### 6.3 新增 `scripts/validate-curriculum-sources.py`

离线纯结构校验，CI 一票否决：
- 扫 `prebuilt/master-curriculum/references/*.md`
- 抽出所有 `T\d+n\d+` / `X\d+n\d+` / `SC-\w+` / `Toh \d+` 形式的引用
- cross-check 是否都出现在某个 `prebuilt/master-*/meta.json.sources[*].cbeta_id` 或类似字段
- 抽出 `/master-<slug>` 引用，cross-check `prebuilt/master-<slug>/` 目录存在
- 任一 miss 直接 fail

### 6.4 扩 `scripts/validate-fidelity.py`

`VALID_BOUNDARIES` 增加：
- `no_winner_judgment`
- `no_strawman`
- `no_fabricated_curriculum`

### 6.5 CI

- 现有 `Validate & Test` workflow 自动覆盖新 jsonl（paths 已含 `prebuilt/**`、`scripts/**`）
- 新增 step 跑 `python scripts/validate-curriculum-sources.py`

---

## 7. 文档与版本

### 7.1 顶层 `SKILL.md`

"对比模式"一节改为"教学模式"，列三命令：

```markdown
## 教学模式

- `/compare-masters` — 多位法师对同一问题的并列对比
- `/master-debate` — 祖师就争议议题进行多轮交叉辩论（v0.7 新增）
- `/master-curriculum` — 根据你的传统与当前位置，给出有时序的学修路径（v0.7 新增）
```

### 7.2 README.md / README_EN.md

- "特性"一节加 debate / curriculum 项
- 新增 "教学模式"小节示例（一段 debate 输出片段 + 一段 curriculum 输出片段）
- 中英文同步

### 7.3 CHANGELOG.md

新增 v0.7.0 entry：
```markdown
## [0.7.0] — 2026-06-XX

### Added
- `/master-debate` — 祖师就争议议题进行 4 轮交叉辩论（立论→反驳→回应→综合 + 教内余争）
- `/master-curriculum` — 按传统与当前位置生成"根基→深入→精研→盲点"学修路径，离线可用
- `scripts/validate-curriculum-sources.py` — curriculum references 经证 + master slug cross-check

### Changed
- 顶层 SKILL.md：「对比模式」→「教学模式」，列三命令
- README.md / README_EN.md：同步教学模式章节
- scripts/validate-fidelity.py：VALID_BOUNDARIES 新增 no_winner_judgment / no_strawman / no_fabricated_curriculum

### Not Changed
- 15 个单 master skill 完全不动
- 不接 fojin 在线 API，保持离线
- 不触发 npm publish（NPM_TOKEN 待重签）
```

### 7.4 版本

- `package.json` 0.6.0 → 0.7.0
- `.version-bump.json` 列出的 4 个 plugin manifest 同步（脚本自动）
- description 末尾加 `+ debate + curriculum teaching modes`

---

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| Debate 仍出现稻草人 | SKILL.md 内"先复述对方原意再回应"约束 + fidelity test `no_strawman` 结构性检查 + v0.7.1 加 `cross_critique` 字段 |
| Curriculum 推荐到不存在的经/master | `validate-curriculum-sources.py` CI 一票否决 |
| Debate 综合环节抹平分歧 | 模板强制"教内余争"section + boundary `no_winner_judgment` |
| 决策树 compare/curriculum 关键词冲突 | 关键词正交划分（对比/比较 vs 次第/路径），互不触发 |
| references/*.md 写出宗派偏见 | ETHICS.md 已有原则；编写时严守"传统内部声音、传统之间平等"；PR review checklist 增加此条 |

---

## 9. 工作量估算

| 项 | 工时 |
|---|---|
| `prebuilt/master-debate/SKILL.md` + fidelity.jsonl | 1d |
| `prebuilt/master-curriculum/SKILL.md` + 8 份 references | 2-3d |
| `prebuilt/master-curriculum/tests/fidelity.jsonl` | 0.5d |
| `scripts/validate-curriculum-sources.py` | 0.5d |
| 扩 `validate-fidelity.py` + 顶层 SKILL.md / README 同步 | 0.5d |
| CHANGELOG + 版本 bump + CI 调通 | 0.5d |
| **合计** | **≈ 5-6 天** |

---

## 10. 验收

- `npm test` 通过：`validate.py --strict` + `validate-fidelity.py` + `validate-curriculum-sources.py` 全绿
- 顶层 `node bin/cli.mjs list` 列出 `master-debate` 和 `master-curriculum`
- 手动 dry-run 一个禅净 debate（4 轮 + 余争 + 引经齐全）和一个禅宗 L0 curriculum（4 段齐全 + 所有经号真实）
- CHANGELOG / README / 顶层 SKILL.md 同步
- PR 单 PR 合入 main，merge 后 tag v0.7.0

---

## 11. 后续（v0.7.x / v0.8）

- v0.7.1：每位 master `meta.json` 加 `cross_critique` 字段（路径 B 增量），提升 debate 反驳含金量
- v0.8：debate 加 LLM-as-judge 中立观察轮 + curriculum 可选接 fojin RAG 做"下一本"动态推荐（路径 C）
- npm publish：等 NPM_TOKEN 重签后正式 release（独立于本期）

---

## 关联

- 本仓库 v0.6 PR #17、#18（15 masters + master- 前缀）
- memory：[[project_master_skill_v06]] · [[project_master_skill_backlog]] · [[feedback_npm_token_renewal]]
- 三大传统平等：依 ETHICS.md 已有原则
