# Buddha-skill

基于佛教经典文献的法师教学角色生成器，遵循 AgentSkills 标准，由 [FoJin](https://fojin.app) 驱动。

---

## 声明

本项目本着对佛教传统的尊重而建立。所有内容均依据佛教经典文献生成，不做教义评判，不代表任何宗派权威。生成内容仅供学习参考，如需正式修行指导，请亲近善知识。

---

## 特性

- **预置八位汉传祖师大德**：涵盖唯识、中观、禅、天台、华严、净土、跨宗派七大核心宗派，开箱即用
- **FoJin 数据桥**：接入 [fojin.app](https://fojin.app) 的 503 个数据源、10K+ 文本、678K+ 语义向量和 31K 实体知识图谱
- **AgentSkills 标准**：遵循 AgentSkills 规范，可作为子技能被其他 Agent 调用
- **双模输出**：每位法师生成 `teaching.md`（教义体系）和 `voice.md`（说法风格）两份文件
- **增量进化**：已生成的法师可追加新经文材料进行增量合并，角色持续完善
- **版本管理**：内置版本号与时间戳，支持回滚到任意历史版本

---

## 快速开始

### 安装

**Claude Code**

```bash
git clone https://github.com/xr843/Buddha-skill ~/Buddha-skill
cd ~/Buddha-skill && pip install -r requirements.txt
# 注册 skills（符号链接到 ~/.claude/skills/）
for d in prebuilt/*/; do ln -sf "$(pwd)/$d" ~/.claude/skills/"$(basename $d)"; done
ln -sf "$(pwd)" ~/.claude/skills/create-master
```

**OpenClaw**

```bash
git clone https://github.com/xr843/Buddha-skill ~/.openclaw/workspace/skills/create-master
cd ~/.openclaw/workspace/skills/create-master && pip install -r requirements.txt
```

**手动安装**

```bash
git clone https://github.com/xr843/Buddha-skill
cd Buddha-skill && pip install -r requirements.txt
```

### 使用预置法师

在支持 AgentSkills 的环境（OpenClaw / Claude Code）中直接调用：

```
/xuanzang       — 玄奘法师（法相唯识宗）
/kumarajiva     — 鸠摩罗什（三论宗/中观）
/huineng        — 慧能大师（禅宗六祖）
/zhiyi          — 智顗大师（天台宗）
/fazang         — 法藏大师（华严宗）
/yinguang       — 印光大师（净土宗）
/ouyi           — 蕅益大师（天台/净土·跨宗派）
/xuyun          — 虚云老和尚（禅宗·五宗兼嗣）
```

### 多法师对比

同一问题由 2-3 位法师并列回答，展现宗派视角差异：

```
# 自动选择相关法师
/compare-masters 什么是空性

# 手动指定法师（推荐，结果更精准）
/compare-masters 什么是遍行因 --masters xuanzang,zhiyi,ouyi

# 自然语言触发
请慧能和印光对比回答"如何看待念佛"
比较禅宗和净土宗对修行的看法
```

**选择逻辑**：系统先尝试从用户提问中提取关键词，与每位法师的核心概念匹配；若无强匹配，则按主题映射兜底（念佛/禅修/唯识中观/判教等）。**如果自动选的法师不符合预期，直接用 `--masters` 手动指定**。

### 自定义生成

```
/create-master 弘一大师
```

或自然语言触发：

```
帮我创建一个弘一大师的教学角色
```

系统将引导完成三步信息录入，然后自动从 FoJin 采集数据、生成教义分析与风格文件。

---

## 预置法师

### 玄奘法师（602-664）

唐代高僧，中国佛教史上最伟大的译经家。西行求法十七年，遍学印度诸部，归国后主持译经事业，译出经论七十五部一千三百三十五卷。创立法相唯识宗，以严谨精确的翻译风格著称，确立"五种不翻"原则。
主要来源：CBETA《大般若经》《瑜伽师地论》《成唯识论》《心经》等。
调用命令：`/xuanzang`

### 鸠摩罗什（Kumarajiva，344-413）

龟兹出身，后秦长安译经，中国四大译经家之一。其译文以文学性和流畅度著称，《妙法莲华经》《金刚经》《维摩诘经》《中论》等译本至今最为通行。奠定了三论宗（中观）在中国的基础。
主要来源：CBETA《妙法莲华经》《金刚经》《维摩诘经》《中论》《大智度论》等。
调用命令：`/kumarajiva`

### 慧能大师（638-713）

禅宗六祖，南宗禅创立者。不识文字的卖柴樵夫，闻《金刚经》而开悟，得五祖弘忍传法。著《六祖坛经》——中国人著作中唯一被尊为"经"者。主张"直指人心，见性成佛"，开顿悟法门。
主要来源：CBETA《六祖大师法宝坛经》T48n2008。
调用命令：`/huineng`

### 智顗大师（538-597）

天台宗创始人，被尊为"东土小释迦"。建立中国佛教第一个完整的判教体系（五时八教），著天台三大部《摩诃止观》《法华玄义》《法华文句》。核心思想：一念三千、三谛圆融、止观双修。
主要来源：CBETA《摩诃止观》T46n1911、《法华玄义》T33n1718 等。
调用命令：`/zhiyi`

### 法藏大师（643-712）

华严宗三祖，华严哲学体系的实际创立者。武则天国师，以"金师子章"为武后说华严义。核心思想：法界缘起、四法界、十玄门、六相圆融——一切现象互含互摄，事事无碍。
主要来源：CBETA《华严经探玄记》T35n1733、《华严五教章》T45n1866 等。
调用命令：`/fazang`

### 印光大师（1861-1940）

汉传净土宗第十三代祖师，近代净土复兴的核心人物。
文字平实恳切，戒行严谨，以书信形式广度众生，著有《印光法师文钞》三编。
主要来源：CBETA 汉文大藏经，含文钞正编、续编、三编及净土三经。
调用命令：`/yinguang`

### 蕅益大师（1599-1655）

明末四大高僧之一，净土宗九祖。"教宗天台，行归净土"——融通禅、教、律、净四宗，是中国佛教史上最重要的跨宗派综合者。其《阿弥陀经要解》被印光大师赞为"即使古佛再来，也不能超过其上"。
主要来源：CBETA《阿弥陀经要解》T37n1762、《教观纲宗》等。
调用命令：`/ouyi`

### 虚云老和尚（1840-1959）

近代禅宗泰斗，世寿一百二十岁，一身兼嗣禅门五宗（临济、曹洞、沩仰、云门、法眼）法脉——佛教史上绝无仅有。复兴六大祖庭，历经清末、民国、新中国三个时代。主张参话头、老实修行、禅净双修。
主要来源：CBETA《楞严经》《金刚经》《六祖坛经》等。
调用命令：`/xuyun`

---

## 架构图

```
用户请求
    │
    ▼
SKILL.md (AgentSkills 入口)
    │
    ├─ 预置法师 ──────────────────────► prebuilt/{slug}/
    │                                        ├── SKILL.md
    │                                        ├── teaching.md
    │                                        ├── voice.md
    │                                        └── meta.json
    │
    └─ 自定义生成
          │
          ├─ prompts/intake.md          (信息录入)
          │
          ├─ tools/sutra_collector.py
          │       │
          │       └──► FoJin API ───► 知识图谱 + 语义检索 + 经文文本
          │
          ├─ prompts/sutra_analyzer.md  (教义分析)
          ├─ prompts/voice_analyzer.md  (风格分析)
          ├─ prompts/teaching_builder.md
          ├─ prompts/voice_builder.md
          │
          ├─ tools/master_builder.py    (角色构建)
          ├─ tools/skill_writer.py      (文件写入)
          └─ tools/version_manager.py  (版本管理)
                │
                ▼
          masters/{slug}/
              ├── SKILL.md
              ├── teaching.md
              ├── voice.md
              └── meta.json
```

---

## 与 FoJin 的关系

[FoJin](https://fojin.app) 是一个佛教文本聚合平台，整合了 503 个数据源、10K+ 篇文本、678K+ 条语义向量嵌入，以及涵盖 31K 实体的知识图谱，覆盖 CBETA 汉文大藏经、SuttaCentral 巴利藏及英译、84000 藏经英译等主要语料库。

Buddha-skill 通过 `tools/fojin_bridge.py` 接入 FoJin API，实现：

- 知识图谱实体检索（法师生平、师承、宗派）
- 语义向量相似度搜索（教义相关经文）
- 原文段落提取与出处追踪

所有引用均附带可追溯的 FoJin 链接，确保内容来源透明。

---

## 敏感性边界

**不做：**

- 不对宗派优劣进行评判
- 不宣称神通感应
- 不涉及政治化宗教议题

**要做：**

- 忠实依据经文原文，所有回答附 FoJin 出处链接
- 通过运行时 RAG 检索真实经文，而非仅依赖 AI 自身知识
- 遇到超出范围的问题坦诚说明

---

## 贡献指南

欢迎提交新的预置法师（请在 `prebuilt/` 目录下按已有格式创建）、修正文献来源错误，或改进工具链。

提交前请确认：文献来源可追溯，内容忠实于佛教经典文献，无宗派偏见。

---

## 许可证

MIT License

---

## 致谢

感谢以下开源佛教文献项目：

- [CBETA](https://cbeta.org) — 汉文大藏经数字化
- [SuttaCentral](https://suttacentral.net) — 巴利藏及多语种译本
- [84000](https://84000.co) — 藏经英译项目
