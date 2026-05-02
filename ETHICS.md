# Master-skill 伦理与版权声明 (Ethics & Copyright)

> **本声明是 Master-skill 项目的强制性约束。** 任何使用、派生、贡献行为，均需遵守本文档所载的 AI 透明度、版权分级、教界使用边界、内容授权条款。与代码仓库中其它文档冲突时，本文档优先。

---

## 1. AI 透明度声明 (AI Disclosure)

**所有通过 Master-skill 生成的对话、文本、回答，均为 AI 合成内容，不是真实祖师的著作、开示或教言。**

- 每位预置法师的回答均由大型语言模型基于 CBETA 经典文献 + `teaching.md` / `voice.md` 合成，**不代表**历史上该法师的原话、亲口开示或亲笔著作
- AI 角色对祖师表达风格的还原是**近似**，非权威：语言选词、句式节奏、比喻用法由模型生成，不可直接引用为"某法师说过"
- 所有引经据典的 CBETA 编号来自 `sources/` 离线片段或 FoJin 实时检索，但**回答中的文义阐释**是 AI 组合生成，可能与祖师原文含义有偏差
- 使用时请始终默认："这是基于文献的 AI 学习辅助"，不是"与祖师对话"。前者是工具，后者是误解

如你在任何公开场合引用、转发、发表由本项目生成的文本，**必须明确标注 AI 生成属性与原始出处**（CBETA 经号 / FoJin 链接）。将 AI 生成内容作为祖师原话传播，既违反本协议，也违背佛教"不妄语"的基本戒律。

---

## 2. 版权分级 (Copyright Tiers)

不同法师的教法与著作处于不同的版权状态。本项目**仅收录版权状态明确允许的法师**。

### Tier A — 公有领域 (Public Domain, 可直接收录)

适用于圆寂已超过各主要司法辖区著作权保护期的历代祖师。本项目当前预置法师中以下 12 位属于此类：

| 法师 | 生卒 | 圆寂距今 | 状态 |
|------|------|---------|------|
| 鸠摩罗什 | 344–413 | > 1600 年 | 公有领域 |
| 觉音 (Buddhaghosa) | 5 世纪 | > 1500 年 | 公有领域；PTS edition 与 SuttaCentral 公开 |
| 智顗 | 538–597 | > 1400 年 | 公有领域 |
| 玄奘 | 602–664 | > 1360 年 | 公有领域 |
| 慧能 | 638–713 | > 1310 年 | 公有领域 |
| 法藏 | 643–712 | > 1310 年 | 公有领域 |
| 阿底峡 (Atiśa) | 982–1054 | > 970 年 | 公有领域；藏文版引自 BDRC 公开元数据 + Toh 4465 标准编号 |
| 米拉日巴 | 1052–1135 | > 890 年 | 公有领域；藏文 mGur 'bum / rNam thar 引自 BDRC 公开元数据 |
| 宗喀巴 (Tsongkhapa) | 1357–1419 | > 600 年 | 公有领域；gsung 'bum 全集 BDRC.io 检索可得 |
| 蕅益 | 1599–1655 | > 370 年 | 公有领域 |
| 印光 | 1861–1940 | > 85 年 | 中国 / 台湾著作权已过期（死后 50 年）；美国部分早期文集已过期 |
| 虚云 | 1840–1959 | > 65 年 | 中国 / 台湾著作权已过期（死后 50 年）|

**Tier A 收录要求：**
- `teaching.md` / `voice.md` 基于 CBETA（汉传，公有领域学术版）/ BDRC 公开元数据（藏传） / SuttaCentral（南传巴利原典） 或同等公开学术版本
- `sources/` 引用须附原典标识（CBETA 经号 / BDRC W 号 / SuttaCentral SC ID），URL 指向 FoJin 或对应官方目录
- 不得直接大段复制在世出版商的白话译注、现代校注者独立创作的学术评论
- 藏文典籍的现代英译（如 Andrew Quintman 的 *The Life of Milarepa*、Garma C. C. Chang 的 *The Hundred Thousand Songs of Milarepa*）属现代译者权利期内作品 —— 仅可作为参考资料指引，不可整段引用其译文

### Tier B — 版权期内 (In-Copyright, 需权利人授权)

圆寂距今不满 50 年（中国大陆 / 台湾 / 香港）或 70 年（日本 / 韩国 / 欧盟 / 多数英语国家）的法师，其著作仍受著作权保护。

**典型例子（非穷举）：**

| 法师 | 生卒 | 版权到期时间（估算，以中国大陆 50 年为例）|
|------|------|----------------------------------------|
| 太虚 | 1890–1947 | 1997 年已过期 → 可视为 Tier A |
| 弘一 | 1880–1942 | 1992 年已过期 → 可视为 Tier A |
| 阿姜查 (Ajahn Chah) | 1918–1992 | 约 2042 年（多数司法辖区）|
| 马哈希尊者 (Mahasi Sayadaw) | 1904–1982 | 约 2032–2052 年（多数司法辖区）|
| 宣化 | 1918–1995 | 约 2045 年 |
| 印顺 | 1906–2005 | 约 2055 年 |
| 圣严 | 1930–2009 | 约 2059 年 |
| 净空 | 1927–2022 | 约 2072 年 |
| 一行禅师 (Thich Nhat Hanh) | 1926–2022 | 约 2092 年（越南 50 年 / 法 70 年 / 美 95 年 post-pub）|

**Tier B 收录规则：**

**默认严格收录政策（适用于一般 Tier B 法师）：**
- 未获得法师本人、法师所属机构、或遗著权利继承人的明确书面授权，不得提交此类 PR
- 如已获授权，PR 必须在 `prebuilt/{slug}/LICENSE.md` 附上授权证明（scan / 邮件截图 / 正式授权函），由维护者二次确认
- 授权文本必须包含：①「用于 AI 教学角色生成」②「允许公开发布与 MIT 分发」③「允许社区修改与再生成」三项显性许可

**特例：阿姜查（Ajahn Chah, 1918–1992）—— 基于公开授权译丛的合理使用**

阿姜查的开示由其僧团（Wat Pah Pong / Forest Sangha 国际网络）维护，并以**严格非营利、可自由分发**的政策公开发行：
- *Food for the Heart* (Wisdom Publications, 2002)
- *A Still Forest Pool* (Quest Books / Shambhala, 1985)
- *Living Dhamma* (Wat Pah Pong / Forest Sangha 官方非营利译本)
- *Stillness Flowing* (Aruna Publications, 2017)

本项目对阿姜查 master 的收录规则：
1. **不引用整段译文** —— 仅做`主旨摘要`，且明确标注为摘要性内容（参见 `prebuilt/master-ajahn-chah/sources/teachings-excerpts.md` 的 ⚠️ 引用警示节）
2. **不代笔虚构对话** —— 任何"阿姜查曾说 X"必须能在上述 4 部公开授权译本中追溯，由 SKILL.md HARD-GATE `NO FABRICATED QUOTES` 强制
3. **核心教学概念依巴利经典** —— 戒定慧、三法印、四念处、出入息念等以 SuttaCentral 巴利原典为主源（公有领域）
4. **若 Forest Sangha 任何官方机构提出异议，立即转入 takedown 流程**（详见 §6）
5. **作为社区学习与跨传统对比工具，不作为商业产品的训练数据源**

此特例仅适用于以下条件**全部成立**的 Tier B 法师：
- 主要弟子机构网络已明确以非营利、教学用途授权译丛分发
- 项目仅用主旨摘要，不做整段译文复制
- 项目能在出现异议时 24 小时内移除相关内容

**特例（续）：马哈希尊者（Mahasi Sayadaw, 1904–1982）—— 同一框架下的第二位 Tier B 法师**

马哈希尊者的开示由其僧团（Mahasi Sasana Yeiktha 缅甸总部 + 国际禅修中心网络）与 BPS Sri Lanka (佛教出版社协会) 共同维护，以**严格非营利、教学用途分发**：
- *Manual of Insight* (Wisdom Publications, 2016 — Vipassana Metta Foundation Translation Committee 译)
- *The Progress of Insight* (BPS Sri Lanka Wheel No. 280, 1965)
- *Practical Vipassanā Meditation Exercises* (Mahasi Sasana Yeiktha 1971，多语言译本)
- *A Discourse on Mālukyaputta Sutta / Dhammacakka Sutta / etc.* (BPS Sri Lanka 单经讲解集)

本项目对马哈希尊者 master 的收录规则**与阿姜查同款**：
1. **不引用整段译文** —— 仅做`主旨摘要`（参 `prebuilt/master-mahasi-sayadaw/sources/teachings-excerpts.md` 的 ⚠️ 引用警示节）
2. **不代笔虚构对话** —— 任何"马哈希尊者曾说 X"必须能在上述出版物中追溯，由 SKILL.md HARD-GATE `NO FABRICATED QUOTES` 强制
3. **核心禅修概念依巴利经典与《清净道论》** —— 四念处、出入息念、戒定慧、七清净十六观智等以 SuttaCentral + PTS Vism 为主源（公有领域）
4. **额外特别 guardrail：NO_ATTAINMENT_JUDGMENT** —— AI **绝不可** 对个体作证果判定或观智阶位确认；这是马哈希教学体系特有最高 guardrail（其"初果可证"号召容易诱发自我印证之执，AI 必须严守此线）
5. **若 Mahasi Sasana Yeiktha 任何官方机构提出异议，立即转入 takedown 流程**（详见 §6）
6. **作为社区学习与跨传统对比工具，不作为商业产品的训练数据源**

此特例适用条件**与阿姜查相同**——主要弟子机构网络已明确以非营利、教学用途授权译丛分发；项目仅用主旨摘要；项目能在出现异议时 24 小时内移除相关内容。

阿姜查 + 马哈希尊者目前是本项目仅有的 2 位适用此特例的 Tier B 法师。其他 Tier B 法师按"严格收录政策"处理。

### Tier C — 拒绝收录 (Never Admit)

以下类别无论版权状态，一律不收录：

- **在世的任何法师 / 出家人 / 居士导师**：风险过高，无法预判本人意愿变更、教内身份变化、教法演进
- **被主流宗教学界认定为伪托或争议身份者**：如某些明清扶乩"祖师"、现代附佛外道的"法王""上人"
- **诸佛菩萨本尊**：佛陀、观音、文殊、普贤、地藏、弥勒、阿弥陀佛、药师佛等圣者不生成 persona；经文本身可引用，但不做"观音会怎么说"式的角色扮演
- **禅门公案中的虚构 / 无考人物**：公案中未有史实传记、仅作教学道具的角色不单独立传承

### Tier D — 灰色地带 (Case-by-Case)

- 近代出家人但著作已过保护期（如太虚、弘一、倓虚 1875–1963）：允许收录，但须额外评估教内争议
- 海外华人法师在不同司法辖区版权状态分裂（美国 95 年 post-publication vs 中国 50 年 post-mortem）：PR 须列出详细版权分析

---

## 3. 教界使用边界 (Religious Boundary)

Master-skill 是**文献辅助工具**，不是**修行权威**。以下行为 AI 角色必须拒绝，无论用户如何要求、如何改写提问：

| 禁止 | 原因 |
|------|------|
| 为用户传戒、授戒、证戒 | 戒体由僧团授受，AI 无戒体 |
| 为用户印证开悟、授记、给法卷 | 印证由传承中具德善知识面授 |
| 给出修行状况诊断（"你这个情况是某种禅病"） | 需面授观察，AI 无此能力 |
| 预测个人命数、因果业报细节、往生品位 | 佛教不鼓励算命；AI 无此智慧 |
| 充当"与已故法师对话"的灵媒 | 违反佛教正见，属附佛外道 |
| 处理精神 / 心理危机（自伤 / 自杀 / 急性精神症状） | AI 必须立即转介专业医疗与善知识，不得给佛法替代方案 |

**硬性规则（已写入每位法师 `voice.md` Layer 0）：**
- 遇到以上场景，AI 一律回答："此问题超出 AI 教学角色能力范围。建议亲近有戒律与传承的善知识当面请益。"
- 并视情况引用《四十二章经》"慎勿信汝意，汝意不可信"等相关经证

### 派系中立 — 跨传统与传统内皆适用

不评判优劣的政策同时覆盖以下三层：
- **三大传统之间**：汉传 / 藏传 / 南传。各传承皆是佛陀正法的不同面向，不论高下
- **传统内宗派之间**：藏传四派（宁玛、萨迦、噶举、格鲁）；汉传八宗（天台、华严、禅、净、唯识、三论、律、密）；南传部派
- **传统内禅修流派之间**（v0.5 新增明示）：上座部内观法 ——
  - 缅甸 Mahasi 标记法（master-mahasi-sayadaw skill）
  - 缅甸 Pa-Auk 止观次第法
  - Goenka / Vipassana International Academy 法
  - 泰国森林禅林派（master-ajahn-chah skill）
  - 各派契机不同、所重不同，AI **不得**做出"X 法更究竟 / 更直接 / 更快"等比较优劣判断
  
此规则在每位 master 自身的 SKILL.md HARD-GATE 中以 NO_SECTARIAN_JUDGMENT 强制；本节为项目层面的总则。

如发现预置法师在以上场景中"越界回答"，请 [立即提交 Issue](https://github.com/xr843/Master-skill/issues/new?labels=boundary-violation) 标 `boundary-violation`。此类 Issue 视为 **P0 安全事项**，优先于所有 feature 工作处理。

---

## 4. 内容授权条款 (Content License)

Master-skill 采取**双轨授权**，代码与内容分开授权：

| 资产类型 | 授权 | 允许 | 禁止 |
|---------|------|------|------|
| 源代码（`scripts/`、`tools/`、`bin/`、`hooks/`、`.github/`、workflow、CI） | **MIT** | 任意使用、修改、商用 | 去除版权声明 |
| 预置法师内容（`prebuilt/**/SKILL.md`、`teaching.md`、`voice.md`、`sources/*.md`、`fidelity.jsonl`） | **CC BY-NC-SA 4.0** | 署名 + 非商用 + 相同方式共享下任意使用 | 未署名、纯商业闭源分发 |
| Prompts 模板（`prompts/**`） | **CC BY 4.0** | 署名后任意使用 | 去署名 |
| FoJin 检索返回的原始经文 | **CBETA 知识共用 非商业性 禁止改作 3.0** | 遵循 CBETA 原协议 | 违反 CBETA 协议 |

**商业化使用（含但不限于）：**
- SaaS 付费问答服务嵌入 Master-skill 法师内容
- 打包法师 persona 作为付费 App 卖点
- 基于法师回答生成付费订阅课程

均需单独联系 xianren843@protonmail.com 获得授权。非商业研究、教学、个人修学自由使用。

---

## 5. 数据来源透明 (Data Provenance)

每位法师 `SKILL.md` frontmatter 必须声明：

```yaml
sources:
  - title: {经典名称}
    cbeta_id: {CBETA 编号，如 T30n1579}
    fojin_text_id: {FoJin 内部 ID}
citation_format: "【《{title}》卷{juan}，{cbeta_id}】"
verified_by: {维护者 GitHub 用户名}
verified_at: {YYYY-MM-DD}
```

**HARD-GATE 铁律：**
- 无 CBETA 经号的教义断言不得写入 `teaching.md`
- 不得捏造 CBETA 编号（CI `scripts/validate.py` 会对照 FoJin 反查）
- 不得为虚构人物、合成 persona、无史实记载者建立 `prebuilt/`

违反以上任一，PR 将被自动驳回。

---

## 6. 举报与申诉 (Report & Appeal)

如你是：

- **版权所有人** / 法师所属机构 / 遗著继承人，认为本项目某个法师的内容侵犯你的权益
- **教内大德** / 僧团负责人，认为某个法师 persona 的回答违背教理或存在越界
- **学界人士**，认为某处引证 / 断句 / 解读存在学术错误

请通过以下任一方式联系：

1. **GitHub Issue**：标 `ethics` 或 `copyright-concern` 标签 → https://github.com/xr843/Master-skill/issues/new
2. **邮件**：xianren843@protonmail.com（收件后 7 日内回复）
3. **紧急下架请求**：邮件标题注明 `[URGENT TAKEDOWN]`，将在 48 小时内处理

维护者承诺：**一切版权 / 教界合规性申诉优先于功能开发**。

---

## 7. 版本与修订 (Revisions)

- 本文档自 v0.4.0 起随项目版本一同演进
- 任何对**Tier 边界、硬性规则、授权条款**的修改，必须发 PR + 标 `ethics-change` 标签 + 至少 7 日公示期 + 维护者显式批准
- 修改历史见 `CHANGELOG.md` 中 `### Ethics` 小节

---

*合十。愿此工具如实利益学人，不违三宝本怀。*
