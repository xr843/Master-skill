# 引用规则与来源约定

> **何时读这个**：用户给出 T- / X- / SC- / Toh- / W- 编号需验证或解析时；create-master 主流程 Step 2 / Step 5 验证 CBETA / BDRC / SuttaCentral / PTS 来源声明时；写入 `teaching.md` 之前需要确认引用格式时。

## 引用编号系统总览

| 系统 | 适用 | 编号格式 | 示例 |
|------|------|---------|------|
| **CBETA** | 汉文藏经 | `<藏别><册号>n<经号>` | `T08n0235`（金刚经）/ `X62n1182`（印光文钞） |
| **BDRC** | 藏文文献 | `BDRC:W<编号>`；具体版本可用 `BDRC:MW<编号>` | `BDRC:W22084`（作品 ID） |
| **SuttaCentral** | 巴利经藏 | `MN 10` / `SC:MN 10`，或语料库声明 `SuttaCentral` | `MN 10`（中部第 10 经《念处经》） |
| **Toh.** | 藏文大藏经德格版 | `Toh <序号>` | `Toh 4465`（阿底峡《菩提道灯论》） |
| **PTS** | 巴利圣典协会版本 | `PTS:<作品简称>`；册页 / 章节单列为 locator | `PTS:Vism`，locator `I.85` |
| **compiled teachings** | 经授权或合规收录的编纂开示 | `<权利人或语料名>:<作品 ID>` | `AjahnChah:FoodForTheHeart` |

## 来源中立 Citation Contract

CBETA、BDRC / Toh、PTS / SuttaCentral 与 compiled teachings 四类来源家族**同等适用 citation contract**，没有任何一种来源族可充当其他传统的全局替代。运行时必须：

1. 将引用解析到所选 persona 的 `meta.json.sources[]`
2. 确认来源类型列于 `citation_contract.allowed_source_types`
3. 仅在 `citation_contract.live_retrieval_allowed` 为 `true` 时执行实时检索

四类来源家族地位相同，但分别受自身引述与版权规则约束：CBETA 须保留底本文字与定位；BDRC / Toh 的元数据不等于现代译文授权；PTS / SuttaCentral 须遵守所用版本与站点许可；compiled teachings 按版权 Tier 与授权范围控制逐字引述，必要时仅作摘要。

## CBETA 引用规范（汉传必备）

### 编号字段构成

声明来源 ID `T08n0235` =
- `T`：大正藏
- `08`：册号
- `n`：经号分隔符
- `0235`：经号

卷、页、栏、行属于 locator，不并入 `meta.json.sources[].id`；例如 `卷10，0748b15-c03`。

### 引用要求

- **教义断言必附经证**（HARD-GATE）：`teaching.md` 中所有教义命题写明 CBETA 编号 + 卷栏行；若粒度仅到经号，至少补出处 URL
- **URL 规范**：仅在实时结果返回真实 `text_id` 时使用 `https://fojin.app/texts/<text_id>`；否则使用 `https://cbetaonline.dila.edu.tw/zh/<CBETA_ID>` 或离线声明来源
- **繁简体**：CBETA 底本一律繁体。生成内容时如用户语言偏好简体，正文用简体但**引用原文段必保繁体**并标注"〔原文繁体〕"
- **跨藏经对照**：T / X / K 三藏可能有同经异本；优先 T，X 仅在 T 缺漏或差异有研究价值时引；同时引用要标注"参 X<编号>异文"

### 常见易错点

- 引《菩提道次第广论》→ **不是 CBETA**，应按所选 persona 声明的 Toh / BDRC 来源核验；现代汉译本仅作辅助并遵守其版权
- 引《六祖坛经》→ 多版本（敦煌本 / 宗宝本 / 德异本），生成时优先 `T48n2008`（宗宝本，常用）并注明所据本
- 引《清净道论》→ 是 PTS Vism / SuttaCentral，**不在 CBETA**；应按所选 persona 声明的巴利来源核验，现代汉译本仅作辅助并遵守其版权

## BDRC 引用规范（藏传必备）

### W 号与 MW 号

- `BDRC:W<编号>` = 作品（abstract work）
- `BDRC:MW<编号>` = 该作品的具体版本 / 木刻 / 出版（manifestation work）

引用建议：教义命题层面用 `W` 号；如需指明具体校刊本可附 `MW`。

### URL 规范

- BDRC 公开元数据 → `https://library.bdrc.io/show/bdr:W<编号>`
- 配 Toh 编号时同列（如 `Toh 4465 / BDRC:W22087`）
- 现代藏译英 / 汉译版本（如 Quintman 译《米拉日巴传》）属于权利期内，**不可大段引用**，仅作为研究指引

### 与汉地引用的衔接

藏传祖师教法引用：
1. 优先藏文原典 W 号 + Toh 编号
2. 若仅有现代研究文献，标注为"参考文献"而非"经证"，不进入 teaching.md 教义命题的支撑链
3. 涉及汉译本（如《菩提道次第广论》汉译版），可引为辅助说明但需在脚注注明译者与出版方

## SuttaCentral / PTS 引用规范（南传必备）

### 巴利经藏五尼柯耶代号

| Nikāya | 中文 | 代号 |
|--------|------|------|
| Dīgha Nikāya | 长部 | DN |
| Majjhima Nikāya | 中部 | MN |
| Saṃyutta Nikāya | 相应部 | SN |
| Aṅguttara Nikāya | 增支部 | AN |
| Khuddaka Nikāya | 小部 | KN（含 Dhp / Sn / Ud / It 等子集） |

### 引用格式

- 经文声明 ID：`SC:MN 10` 或 `MN 10`；locator 可另列经内章节
- 论藏 / 注释声明 ID：如 `PTS:Vism`；册页 + 章节号另列 locator `I.85`
- URL：`https://suttacentral.net/mn10`（小写）

### 巴利 vs 汉译《阿含》对照

- 引南传上座部教法 → 必引 SC / PTS，**不能仅引《杂阿含》《中阿含》替代**
- 若用户问"上座部与阿含异同"，可同时列 SC + T2 / T26 双引并说明文本史
- 觉音注释（Atthakathā）有 PTS 标准编号，引用时附章节号

## 引用验证流程（运行时）

create-master 主流程在 Step 2 与 Step 5 调用 `verify_sources.py`：

```bash
# Step 2 采集后初验
python3 ${CLAUDE_SKILL_DIR}/tools/verify_sources.py --check-links collected_data.json

# Step 5 写入前终验
python3 ${CLAUDE_SKILL_DIR}/tools/verify_sources.py --final-check masters/{slug}/
```

### 两个离线模式的真实边界

1. `--check-links collected_data.json` 读取采集 manifest，验证 `sources[]` 非空、来源家族受支持、各家族 ID 格式、来源不重复、可选 `citations[]` 均属于已声明来源，并确认 `citation_contract` 等于从 `sources[].type` 自动派生的合同。
2. `--final-check masters/{slug}/` 先确认 persona 目录包含 `SKILL.md`、`teaching.md`、`voice.md`、`meta.json`，再对 `meta.json` 执行同一来源与合同校验。
3. 两个模式都不联网，也不解析 `teaching.md` 中的自由文本引文，因此成功只表示 manifest / meta 的结构、家族 ID 和声明归属一致；不表示每个正文断言已经逐条核验，也不保证外部站点 HTTP 可达。

### 外部可达性与旧版 CBETA 审计

外部链接可达性需要独立的人工或可选在线核验。`verify_sources.py --fix` 保留旧版在线 CBETA URL
审计与替换流程，只覆盖仓库中的 CBETA / FoJin 链接；它不验证 BDRC、Toh、SuttaCentral、PTS 或
compiled teachings，也不能代替上述声明归属校验。不得把 `--check-links` 或 `--final-check` 的成功
描述为“所有链接已检查 200”或“题名 / 作者已在线核对”。

## 编造引用 = HARD-GATE 红旗

- 编造不存在或未由 persona 声明的 CBETA / BDRC / Toh / PTS / SC / compiled-teaching ID
- "众所周知该法师持此见，故不引"（HARD-GATE 防御表禁止）
- 用现代译本充当经证（仅作辅助参考，不进入教义断言支撑链）
- 引述时省略卷栏行致使无法定位（粒度低于"经"级别一律视为不充分）

> 完整 HARD-GATE 规则与理性化防御 → `references/ethics-runtime.md`。
