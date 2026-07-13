# create-master 主流程细节

> **何时读这个**：进入主流程 Step 1-5 任一步遇到细节问题（错误兜底、用户交互文案、版本号策略）时；处理"追加材料 / 纠正 / 管理命令"涉及版本与冲突时；运行时执行优先级冲突解释场景。
> 主流程骨架在根 SKILL.md，本文档是按需展开的"细则手册"。

## Step 1：信息录入细则

### 快捷入口（用户直接给名）

用户直接输入 `/create-master 弘一大师` → 跳过交互问答，自动填充默认值：
- 关注方面 = 全部
- 语言 = 根据传承自动推荐（汉传/中文，藏传/中文+藏文术语注音，南传/中文+巴利术语注音）

展示确认摘要：

```
即将创建：弘一大师
传承：汉传（律宗）
关注方面：全部
语言：中文
确认创建？(Y/n)
```

用户确认后直接进入 Step 2。

### 语言自动检测

根据用户**第一条消息**的语言决定后续全部交互语言：
- 中文消息 → 中文回复
- English message → English replies
- 其他语言同理

中途切换语言 → 跟随切换，但保持术语原文 + 注音。

### FoJin KG 匹配

- **匹配成功** → 自动填充传承、时代、宗派等元数据，展示给用户确认
- **匹配失败** → 提示：

  > "未在 FoJin 知识图谱中找到「{name}」。请确认名称是否正确，或提供以下信息以手动创建：宗派（如禅宗/净土/天台/华严/唯识等）、时代、师承。"

- 用户提供补充信息后，以**手动模式**继续（仍走 Step 2，但跳过 KG 实体采集，仅做经文检索）

### 名称校验规则

- 名称必须为**历史真实人物**，不接受虚构角色（小说人物 / 游戏角色 / 神话人物 / 在世法师）
- 检测到非历史 / 虚构人物 → 回复：

  > "本工具仅支持历史上真实存在的高僧大德，无法为虚构人物创建教学角色。"

- 名称不可为空、不可为纯数字 / 特殊字符
- 多写法名（如"鸠摩罗什"/"鸠摩罗什婆"）→ 优先 FoJin KG 中的**标准名称**
- 已存在（预置或已生成） → 提示：

  > "「{name}」已存在，可直接使用 /{slug} 调用。如需重新生成，请先执行 /delete-master {slug}。"

- 在世法师 / 圆寂未足版权期 → 走 `references/ethics-runtime.md` §版权分级 Tier B/C 流程

## Step 2：数据采集细则

### 采集内容

```bash
python3 ${CLAUDE_SKILL_DIR}/tools/sutra_collector.py --name "<法师名>" --tradition "<传承>" --output collected_data.json
```

包括：
- 知识图谱实体与师承关系
- 相关经典列表与内容摘录
- 传承相关术语（汉传 → CBETA 经名 / 藏传 → 藏文典名 + Toh 编号 / 南传 → SC 经名 + PTS 编号）

### API 故障处理

FoJin API 返回错误或不可达 → 向用户说明：

> "FoJin API 暂时不可用（错误信息：{error}）。您可以：①稍后重试；②进入手动输入模式，提供经文文本。"

手动输入模式下，用户可粘贴经文原文或提供 CBETA 经号，系统基于用户提供的材料继续生成。**但所有用户提供的经号仍须经 verify_sources.py 验证。**

### 超时与重试

- 每次 API 调用超时 = 30 秒
- 超时自动重试 1 次
- 仍失败 → 触发上述故障处理

### 最低数据阈值

采集到经文 < 3 条 → 警告：

> "仅找到 {n} 条相关经文，生成的角色内容可能不够丰富。建议：①追加关键词重新搜索；②手动补充经文材料；③继续生成（内容可能有限）。"

### 引用验证

采集完成后：

```bash
python3 ${CLAUDE_SKILL_DIR}/tools/verify_sources.py --check-links collected_data.json
```

该命令离线检查来源家族、ID 格式、声明归属与自动派生的 citation contract；它不请求外部站点。
格式或归属无效的来源须在 Step 3 前排除。外部可达性如有需要，应另作人工或可选在线核验。
详细引用规则 → `references/source-conventions.md`。

### 采集结果确认

```
数据采集完成：
  知识图谱实体：{n} 个
  相关经典：{m} 部
  内容摘录：{k} 段
  无效链接：{j} 个（已排除）
继续分析？(Y/n)
```

## Step 3：分析与生成细则

### 运行时检索规则

加载 `${CLAUDE_SKILL_DIR}/prompts/rag_instructions.md`，将检索指引嵌入生成的每个法师 SKILL.md 运行规则中——确保法师回答时调用 FoJin 实时检索而非仅依赖 LLM 自身知识。

### 两阶段分析

1. **教义分析** — 加载 `prompts/sutra_analyzer.md` + 采集数据，分析教义结构：核心教义维度、关键经典、修行次第
2. **风格分析** — 加载 `prompts/voice_analyzer.md` + 采集数据，分析说法风格：语言特征、说法模式、常用譬喻

### 宗派标签自动检测（风格规则路由）

按 FoJin KG 宗派信息自动选用 voice_analyzer 中对应宗派的风格规则：

| 宗派 | 风格特征 |
|------|---------|
| 禅宗 | 机锋、公案风格 |
| 净土宗 | 劝信、念佛开示风格 |
| 天台宗 | 判教、止观论述风格 |
| 华严宗 | 圆融、法界观论述风格 |
| 唯识 / 法相 | 因明论证、术语精确风格 |
| 三论 / 中观 | 八不破立、二谛说法 |
| 律宗 | 戒法持犯、止持作持论述 |
| 藏传格鲁 | 道次第论证、应成中观三士道 |
| 藏传噶举 | 大手印诗偈 / 道歌风格（米拉日巴 mGur） |
| 南传上座部 | 七清净十六观智论述、巴利原文穿插 |

### 质量门控

分析器输出中任一维度标记 `"insufficient_data": true` → 向用户提示：

> "以下维度的数据不足，生成质量可能受影响：{dimensions}。"
> "建议追加相关经文材料后重新分析，或选择继续生成（不足部分将标注警告）。"

用户继续 → 生成文件中对不足维度添加 `<!-- DATA_LIMITED -->` 注释。

### 生成阶段

- **教义生成**：`prompts/teaching_builder.md` → `teaching.md`
- **风格生成**：`prompts/voice_builder.md` → `voice.md`（4 层结构）

### voice.md 4 层结构

| Layer | 含义 | 示例 |
|-------|------|------|
| **0** | 硬规则，不可违反的底线 | "不自称已证悟"、"不预言未来"、"不冒充佛"、"不收弟子" |
| **1** | 核心风格，该法师最显著的说法特征 | 慧能：直指见性 / 印光：劝信念佛 / 玄奘：因明严谨 |
| **2** | 辅助风格，次要但常见的表达模式 | 引用习惯、常用譬喻、句式偏好 |
| **3** | 情境风格，特定场景下的应对方式 | 面对学者 / 面对初学 / 面对疑惑 / 面对争执 |

## Step 3.5：二阶段审查细则

### 顺序不可颠倒

教义准确性审查 → 风格一致性审查。**不可颠倒**，因为教义错误修复可能影响风格层级。

### 教义准确性审查

生成器先从 `sources[].type` 派生 citation contract，并在内存中保留同一个 sources/contract 对象。
`prompts/doctrine_reviewer.md` 接收这个**生成器内存上下文**及 teaching.md：
- 经证覆盖率（目标 ≥ 90%）
- 各来源家族 ID 的声明归属准确性
- 宗派边界越界（如让慧能讲三士道）
- 输出：PASS / PASS WITH WARNINGS / FAIL

最终 spec 与 `meta.json` 必须复用同一个 contract；写入器会重新按 `sources[].type` 派生并拒绝漂移。

FAIL → 自动修复严重问题后重审，**最多 2 轮**。仍 FAIL → 报告问题请求人工介入。

### 风格一致性审查

`prompts/voice_reviewer.md` 对 voice.md：
- Layer 0 硬规则完整性
- 风格与宗派特征匹配度
- 层次结构清晰度
- 输出：PASS / PASS WITH WARNINGS / FAIL

FAIL → 自动修复后重审。

### 结果展示

```
══ 审查结果 ══
教义准确性：PASS (经证覆盖率 95%, 0 严重问题)
风格一致性：PASS WITH WARNINGS (Layer 0 完整, 1 警告)
  警告：Layer 2 缺少"面对学者"的情境风格
══════════════
```

两项均 PASS 或 PASS WITH WARNINGS 后，进入 Step 4。

## Step 4：预览与确认细则

### 结构化预览格式

```
══ 教义预览（teaching.md）══
核心教义：{1-3 条核心教义概要}
关键经典：{主要引用经典列表}
修行次第：{修行路径概要}

══ 风格预览（voice.md）══
风格特征：{2-3 条风格特点}
语言模式：{典型表达方式}
示例句：
  1. "{模拟该法师风格的示例句1}"
  2. "{模拟该法师风格的示例句2}"
══════════════════════════
```

### 用户修改请求识别

| 用户说 | 处理 |
|--------|------|
| "修改教义部分" | 重新展示 teaching.md 详情，接受用户逐条调整 |
| "调整风格更严厉一些" / "语气更温和" | 调整 voice.md 风格参数后重新预览 |
| "添加更多关于{主题}的内容" | 针对性补充特定教义维度 |
| "重新生成" | 以调整后的参数重新执行 Step 3，重新展示预览 |

## Step 5：写入文件细则

```bash
python3 ${CLAUDE_SKILL_DIR}/tools/master_builder.py --spec generated-master.json --output masters/
```

`generated-master.json` 是审查通过后的生成规格，必含 `name`、`tradition`、`school`、`era`、
`languages`、`teaching_content`、`voice_content`、`sources`，并可携带审查所用的同一
`citation_contract`。若携带的 contract 与来源家族自动派生结果不同，构建立即失败。

### 生成后终验

```bash
python3 ${CLAUDE_SKILL_DIR}/tools/verify_sources.py --final-check masters/{slug}/
```

`--final-check` 离线验证 persona 目录包含 `SKILL.md`、`teaching.md`、`voice.md`、`meta.json`，
并验证 `meta.json` 的来源家族、ID 格式、声明归属与 citation contract。它不会解析
`teaching.md` 的自由文本引文，也不检查外部链接 HTTP 状态；外部可达性是独立的人工或可选在线步骤。

### 生成目录结构

```
masters/{slug}/
├── SKILL.md          # /{slug} 触发（完整角色定义）
├── teaching.md       # 教义体系（可单独使用）
├── voice.md          # 说法风格（可单独使用）
└── meta.json         # 元数据（版本、生成时间、数据来源）
```

### 角色注册（按运行环境）

**Claude Code 用户**
1. 生成的 SKILL.md 已放置在 `masters/{slug}/`
2. 确保 `masters/` 在 Claude Code skill 搜索路径中（检查 `.claude/settings.json` 的 `skillDirs` 配置）
3. 完成后自动可通过 `/{slug}` 触发

**OpenClaw 用户**
1. 将 `masters/{slug}/` 复制到 OpenClaw 的 skills 目录
2. 在 OpenClaw 配置中注册新 skill
3. 参考 OpenClaw 文档完成注册流程

### 完成提示

```
已生成「{master_name}」教学角色
  目录：masters/{slug}/
  调用命令：/{slug}
  包含文件：SKILL.md, teaching.md, voice.md, meta.json
  数据来源：{n} 条经文，{m} 个知识图谱实体
```

## 追加材料、纠正、管理命令细则

### 追加材料（进化模式）

**触发短语**：
- "给印光大师追加《文钞三编》的材料"
- "追加《经名》的材料"
- "补充关于{主题}的内容"
- "用这段语录更新慧能大师的说法风格"

加载 `prompts/merger.md` 增量合并。

**合并冲突处理**：
- merger.md 策略：「新数据优先、保留原有结构」
- 教义矛盾（如不同经典对同一概念阐述差异）→ 保留双方并加注释说明差异
- 风格冲突 → 新材料风格特征与现有特征**合并**，不覆盖

**版本自动递增**：
- 每次追加 → meta.json `version` 自动 minor 递增（1.0.0 → 1.1.0）
- 旧版本自动归档到 `masters/{slug}/.versions/`
- `/master-rollback` 可回退到任意历史版本

### 纠正模式

用户对 AI 表现提出纠正：
- "他不会这样说话"
- "他应该更严厉一些"
- "他遇到这种问题会先引用《法华经》"

加载 `prompts/correction_handler.md`。

**纠正处理流程**：
1. 识别纠正类型：教义纠正 → `teaching.md`；风格纠正 → `voice.md`
2. 以 `## Correction` 块格式追加到对应文件**末尾**，含时间戳 + 原始反馈
3. 纠正记录的优先级**高于**分析生成的内容（详见下文执行优先级）
4. 每次纠正 → meta.json 版本号 patch 递增（1.1.0 → 1.1.1）

### 管理命令

| 命令 | 行为 |
|------|------|
| `/list-masters` | 列出所有已生成的法师，显示传承、时代、版本号；预置标 `[预置]`，自定义标 `[自定义]` |
| `/master-rollback <slug> <version>` | 回滚到指定版本；当前版本自动归档到 `.versions/`；指定版本不存在 → 列出可用版本供选择 |
| `/delete-master <slug>` | 删除法师目录；执行前二次确认："确定要删除「{master_name}」吗？此操作不可恢复。输入 'yes' 确认。"；**预置不可删除** |

## 执行优先级冲突细则

法师角色运行时优先级（高→低）：

1. voice.md Layer 0 硬规则
2. Correction 记录
3. voice.md Layer 1-3
4. teaching.md 教义内容
5. FoJin RAG 实时检索结果
6. LLM 自身知识

### 典型冲突场景示例

| 场景 | 处理 |
|------|------|
| voice.md Layer 0 规定"不自称已证悟"，teaching.md 有该法师证悟记载 | 回答时**不以第一人称宣称证悟**（Layer 0 覆盖 teaching） |
| 用户纠正"他从不直接回答是非题"，voice.md Layer 1 可能有直接回答模式 | 纠正记录覆盖 Layer 1（Correction 高于 Layer 1-3） |
| FoJin RAG 检索经文与 teaching.md 记载有细节差异 | 以 teaching.md 为准（RAG 作为补充参考） |
| LLM 自有知识与 teaching.md 冲突 | 以 teaching.md 为准（LLM 知识最低优先级） |

## FoJin API 深度使用

`rag_query.py` 不够用的场景（KG 深度遍历、跨词典分组对比等）→ 参考 `references/fojin-api.md`（REST API 完整参考）。

## 衔接其他 references

- 引用规则（CBETA / BDRC / SC / Toh / PTS）→ `references/source-conventions.md`
- HARD-GATE 完整规则、AI 透明度、版权分级、边界场景 → `references/ethics-runtime.md`
- 三大传统总论、宗派定位、跨传统对比议题 → `references/traditions.md`
- compare / debate / curriculum 选择 → `references/teaching-modes.md`
