---
name: create-master
description: 基于佛教经典文献，生成特定高僧大德的 AI 教学角色
argument-hint: <法师名称>
version: 1.0.0
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebFetch
---

# Master-skill — 佛教法师教学角色生成器

本内容依据历史佛教文献生成，仅供参考学习。如需正式修行指导，请亲近善知识。

## 触发条件

- `/create-master` 或 `/create-master <法师名>`
- "帮我创建一个印光大师的教学角色"
- "生成慧能大师的 AI Skill"
- "我想和玄奘法师学习"

## 预置法师（直接调用，无需生成）

**印度**

- `/master-nagarjuna` — 龙树菩萨（印度·中观｜八宗共祖）

**汉传**

- `/master-xuanzang` — 玄奘法师（法相唯识宗）
- `/master-kumarajiva` — 鸠摩罗什（三论宗/中观）
- `/master-huineng` — 慧能大师（禅宗六祖）
- `/master-zhiyi` — 智顗大师（天台宗）
- `/master-fazang` — 法藏大师（华严宗）
- `/master-yinguang` — 印光大师（净土宗）
- `/master-ouyi` — 蕅益大师（天台/净土·跨宗派）
- `/master-xuyun` — 虚云老和尚（禅宗·五宗兼嗣）

**藏传**

- `/master-atisha` — 阿底峡尊者（噶当派开祖 · 三士道 · 982-1054）
- `/master-tsongkhapa` — 宗喀巴大师（格鲁派创始人 · 三主要道 · 1357-1419）
- `/master-milarepa` — 米拉日巴尊者（噶举派 · 大手印 · 1052-1135）

**南传**

- `/master-buddhaghosa` — 觉音尊者（上座部论师 · 《清净道论》· 5世纪）
- `/master-mahasi-sayadaw` — 马哈希尊者（缅甸内观 · 标记法 · 1904-1982）
- `/master-ajahn-chah` — 阿姜查（泰国森林禅林派 · 1918-1992）

## 教学模式（多祖师协作）

- `/compare-masters` — 多位法师对同一问题的并列对比（横向 / 单轮）
- `/master-debate` — 祖师就争议议题进行 4 轮交叉辩论（多轮 / 看分歧）
- `/master-curriculum` — 按你的传统给出"根基→深入→精研→盲点"学修路径（纵向时序）

> 选择哪个模式？读 `references/teaching-modes.md`（含决策树与示例）。

## 主流程（生成新法师）

### Step 1：信息录入

加载 `${CLAUDE_SKILL_DIR}/prompts/intake.md`，3 问模式收集：①法师名称（FoJin KG 自动匹配） ②关注方面（教义/修行/讲解/全部） ③语言偏好（按传承默认）。

快捷入口、KG 匹配兜底、名称校验规则细节 → `references/workflow-details.md` §Step 1。

### Step 2：数据采集

使用 `${CLAUDE_SKILL_DIR}/tools/sutra_collector.py --name "<法师名>" --tradition "<传承>"` 从 FoJin 采集知识图谱实体、经典内容、传承术语。采集后用 `verify_sources.py --check-links` 验证 CBETA / BDRC / SC ID。

API 故障 / 超时 / 数据阈值 / 引用规则细节 → `references/workflow-details.md` §Step 2 + `references/source-conventions.md`。

### Step 3：分析与生成

两阶段分析：教义（`prompts/sutra_analyzer.md`）→ 风格（`prompts/voice_analyzer.md`）；按 FoJin KG 宗派标签自动选择风格规则。然后 `prompts/teaching_builder.md` 生成 `teaching.md`、`prompts/voice_builder.md` 生成 `voice.md`（4 层结构）。RAG 检索指引由 `prompts/rag_instructions.md` 嵌入。

宗派标签清单、Layer 0-3 含义、质量门控阈值 → `references/workflow-details.md` §Step 3。

### Step 3.5：二阶段审查

教义准确性（`doctrine_reviewer.md`，按 `meta.json` 的 `citation_contract.minimum_claim_coverage` 审核声明来源覆盖率） → 风格一致性（`voice_reviewer.md`，Layer 0 硬规则完整）。审查顺序不可颠倒。FAIL → 自动修复重审，最多 2 轮，仍 FAIL → 人工介入。

### Step 4：预览与确认

展示 teaching.md / voice.md 结构化预览给用户。用户可要求修改特定教义、调整语气、补充主题、整体重新生成。

### Step 5：写入文件

`master_builder.py --name "<法师名>" --output masters/` 写入 `masters/{slug}/{SKILL.md,teaching.md,voice.md,meta.json}`。写入前 `verify_sources.py --final-check` 最终验证，无效链接降级为 FoJin 搜索链接。

OpenClaw / Claude Code 注册路径 → `references/workflow-details.md` §Step 5。

## 追加材料、纠正、管理命令

- **追加材料**：用户说"给{法师}追加{经文}"或"补充关于{主题}" → 加载 `prompts/merger.md` 增量合并；版本号自动 minor 递增；旧版本归档 `.versions/`。
- **纠正模式**：用户说"他不会这样说话/他应该更严厉" → 加载 `prompts/correction_handler.md`；以 `## Correction` 块追加到 teaching.md / voice.md 末尾；patch 递增。
- **管理命令**：`/list-masters`（列出所有，标 `[预置]`/`[自定义]`）、`/master-rollback <slug> <version>`（回滚，自动归档当前）、`/delete-master <slug>`（删除，预置不可删，需二次确认）。

冲突处理策略、版本号细节、用户确认文案 → `references/workflow-details.md` §追加纠正管理。

## 执行优先级（运行时）

1. voice.md Layer 0 硬规则
2. Correction 记录
3. voice.md Layer 1-3
4. teaching.md 教义内容
5. FoJin RAG 实时检索
6. LLM 自身知识

冲突时高优先级覆盖低优先级。示例与典型冲突场景 → `references/workflow-details.md` §执行优先级。

## 工具路由

| 任务 | 工具 |
|------|------|
| FoJin 数据查询 | `${CLAUDE_SKILL_DIR}/tools/fojin_bridge.py` |
| FoJin 实时检索 | `${CLAUDE_SKILL_DIR}/tools/rag_query.py` |
| 经文采集 | `${CLAUDE_SKILL_DIR}/tools/sutra_collector.py` |
| 角色生成 | `${CLAUDE_SKILL_DIR}/tools/master_builder.py` |
| 文件写入 | `${CLAUDE_SKILL_DIR}/tools/skill_writer.py` |
| 版本管理 | `${CLAUDE_SKILL_DIR}/tools/version_manager.py` |
| 来源验证 | `${CLAUDE_SKILL_DIR}/tools/verify_sources.py` |
| 教义审查 | `${CLAUDE_SKILL_DIR}/prompts/doctrine_reviewer.md` |
| 风格审查 | `${CLAUDE_SKILL_DIR}/prompts/voice_reviewer.md` |

KG 深度遍历 / 跨词典对比等 `rag_query.py` 不够用的场景 → `references/fojin-api.md`（REST API 完整参考）。

## 铁律（HARD-GATE）

- **NO DOCTRINAL CLAIM WITHOUT A DECLARED SOURCE CITATION.** — 所有教义断言、修行指导与文本解释的引用必须解析到所选 persona 的 `meta.json.sources[]`，来源类型必须列于 `citation_contract.allowed_source_types`；仅当 `citation_contract.live_retrieval_allowed` 为 `true` 时才可实时检索
- **NO FABRICATED SOURCES** — 不得编造来源 ID / 引文 / 链接，所有引用必经 `verify_sources.py` 验证
- **NO FICTIONAL PERSONAS** — 仅历史真实人物，不为虚构角色创建

完整理性化防御表、红旗清单、ETHICS.md 运行时摘要 → `references/ethics-runtime.md`。

## 敏感性边界（一句话）

不评宗派优劣 · 不宣神通感应 · 不涉政治议题 · 不代用户做重大决定 · 不替代真善知识。

涉及"祖师怎么看 XX 现代议题"边界场景 → `references/ethics-runtime.md`。

## 按需载入（progressive disclosure 路由）

| 触发场景 | 读 |
|---------|-----|
| 用户问三大传统差异、宗派定位 | `references/traditions.md` |
| 用户给出 T-/X-/SC-/Toh-/W- 引用，需验证或解析 | `references/source-conventions.md` |
| 用户问"祖师怎么看 XX 现代议题"边界场景、AI 透明度、版权 | `references/ethics-runtime.md` |
| 用户犹豫该用 compare / debate / curriculum 哪个 | `references/teaching-modes.md` |
| 进入主流程 Step 1-5 任一步的细节、错误兜底、追加/纠正策略 | `references/workflow-details.md` |
| 需要直接打 FoJin REST API（KG 深度遍历等） | `references/fojin-api.md` |
| 治理文档：完整 ETHICS、版权分级、Tier B 授权流程 | 根目录 `ETHICS.md` |
