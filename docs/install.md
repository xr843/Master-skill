# 开发者安装与用法

> 五端安装、教学模式、自定义生成的完整说明。快速开始见 [README](../README.md#开发者安装)。

---

> 👤 **只是想体验？** 直接用 [fojin.app/chat](https://fojin.app/chat)，跳过下面的安装步骤。
> 🛠️ **本节面向**：Claude Code / Cursor / Codex CLI / OpenCode / Gemini CLI 用户，希望在终端 AgentSkill 环境中直接调用 `/master-xuanzang` `/master-huineng` 等命令。

### 安装

**NPX 一键安装（推荐，无需常驻）**

`npx master-skill install --all` 一次安装全部 20 个 Skill：15 位祖师、4 个教学模式（含 `/master-help` 路由），以及 `create-master` 生成器。`create-master` 会复制自包含的运行时，因此临时 npx 包目录被清理后仍可使用；重新安装或 `update --all` 会更新运行时，但保留 `create-master/masters/` 中用户生成的 persona。

```bash
# 安装指定祖师
npx master-skill install master-zhiyi master-fazang master-huineng

# 单独安装公共教学模式或自定义生成器
npx master-skill install compare-masters
npx master-skill install create-master

# 安装全部 20 个 Skill
npx master-skill install --all

# 查看全部可安装 Skill
npx master-skill list

# 不知道该问谁？描述你的问题，让它推荐
npx master-skill recommend "念佛怎么念才算老实"
npx master-skill recommend "禅宗从哪开始学"
```

**不知道该用哪位祖师 / 哪个模式？**

两个入口，共用同一份路由表（仓库根的 `routing.json` + 各 `meta.json` 的 `search_scope.keywords`）：

| 入口 | 场景 |
|------|------|
| `master-skill recommend "<问题>"` | 终端里，确定性打分，支持 `--json` |
| `/master-help` | 对话里，直接问"我该问谁" |

判定顺序是短路的：**学修路径 → 对辩 → 对比 → 单位祖师 → 白话状况 → 主题配对**。
它只给目标，不代答教理——落到哪位祖师，就由那位祖师自己的 `citation_contract`
和边界规则接手。

上方[「你的状况」表](#如果你不确定该找谁问可以这样开始)的每一行都被
`tests/cli.test.mjs` 锁住：**改那张表而不改路由数据，测试就会失败**。

```bash
$ master-skill recommend "十六观智是什么"

推荐祖师：
  /master-buddhaghosa  [南传]  命中 十六观智
  /master-mahasi-sayadaw  [南传]  命中 十六观智、观智
```

> 打分只认长度 ≥ 2 的关键词。`空` `戒` `定` `慧` `苦` `禅` `业` 这七个单字在日常汉语里
> 会误命中（"有空吗"曾被判给中观宗），已从打分中排除；只带单字的问题会落到主题配对兜底。

**全局安装（频繁使用 / 离线场景）**

```bash
npm install -g master-skill            # 一次性装到 $PATH
master-skill install master-zhiyi      # 之后省掉 npx，直接调
master-skill list
npm update -g master-skill             # 升到下一个 minor / patch
```

**Claude Code**

插件方式（同时装上 session-start hook）：

```bash
claude plugin marketplace add xr843/Master-skill
claude plugin install master-skill@master-skill
```

`claude plugin details master-skill` 应显示 `Skills (20)`。v0.12.11 及更早的插件只注册了
`create-master` 一个 skill，hook 却宣布了全部 `/master-*` 命令。插件按版本号更新，已安装的在下一个版本发布后运行
`claude plugin update master-skill`（同版本号时 update 会报“已是最新”而不拉取修复）。

git clone 手动链接：

```bash
git clone https://github.com/xr843/Master-skill ~/Master-skill
cd ~/Master-skill && pip install -r requirements.txt
mkdir -p ~/.claude/skills   # 目录不存在时下面的 ln 全部失败
for d in prebuilt/master-*/; do ln -sf "$(pwd)/$d" ~/.claude/skills/"$(basename $d)"; done
ln -sf "$(pwd)/prebuilt/compare-masters" ~/.claude/skills/compare-masters
ln -sf "$(pwd)" ~/.claude/skills/create-master
```

**Cursor**

```bash
git clone https://github.com/xr843/Master-skill ~/Master-skill
# Cursor 自动检测 .cursor-plugin/plugin.json 并注册技能
```

**OpenCode**

```bash
npx master-skill install --all
```

OpenCode 无需配置即读取 `~/.claude/skills/`，npx 正是装到这里；`opencode debug skill` 应列出 20 个。
已 clone 仓库的，也可在 `opencode.json` 里写
`{"skills": {"paths": ["/仓库绝对路径/prebuilt"]}}`，得到 `prebuilt/` 下的 19 个（`create-master` 在仓库根，不在其中）。

> 旧版说明让你写 `"plugin": ["master-skill@git+https://github.com/xr843/Master-skill.git"]`。
> OpenCode 的 plugin 是 JavaScript 模块，本仓库没有提供，这样配置**一个 skill 都不会注册**。

**Codex CLI**

参见 [.codex/INSTALL.md](../.codex/INSTALL.md)。Codex 不读 `~/.claude/skills/`，npx 装的它看不到。

**Gemini CLI**

```bash
gemini skills install https://github.com/xr843/Master-skill --path prebuilt
```

`gemini skills list` 应列出 19 个（15 位祖师 + 4 个教学模式）。已 clone 仓库的，用
`gemini skills link /仓库路径/prebuilt`。

> 只装扩展（`gemini extensions install`）**不带来任何祖师**：Gemini CLI 只从扩展根目录的 `skills/`
> 找 skill，本仓库的 skill 在 `prebuilt/`，扩展只提供 `GEMINI.md`——即 `create-master` 生成器与
> `compare-masters` 的说明。仓库的 `hooks/hooks.json` 会被 Gemini 读到并在 `/hooks` 里显示为 enabled，
> 但它按精确字符串匹配 SessionStart 来源，`startup|clear|compact` 永远不命中，法师列表不会注入。
> Gemini CLI 同样不读 `~/.claude/skills/`。

> 以上 OpenCode / Codex / Gemini 的结论均于 2026-09-16 在 Linux 上以隔离的 HOME 实测
> （OpenCode 1.18.13、Codex CLI 0.153.4、Gemini CLI 0.60.0）；Windows 步骤未重新验证。

### 使用预置法师

在支持 AgentSkills 的环境（Claude Code / Cursor / Codex CLI / OpenCode / Gemini CLI）中直接调用
（Codex 按所链接的目录名加前缀，显示为 `master-skill:master-huineng` 等）：

```
# 印度
/master-nagarjuna      — 龙树菩萨（印度·中观｜八宗共祖）

# 汉传
/master-xuanzang       — 玄奘法师（法相唯识宗）
/master-kumarajiva     — 鸠摩罗什（三论宗/中观）
/master-huineng        — 慧能大师（禅宗六祖）
/master-zhiyi          — 智顗大师（天台宗）
/master-fazang         — 法藏大师（华严宗）
/master-yinguang       — 印光大师（净土宗）
/master-ouyi           — 蕅益大师（天台/净土·跨宗派）
/master-xuyun          — 虚云老和尚（禅宗·五宗兼嗣）

# 藏传
/master-atisha         — 阿底峡尊者（噶当派开祖 · 三士道 · 982-1054）
/master-tsongkhapa     — 宗喀巴大师（格鲁派创始人 · 三主要道 · 应成中观）
/master-milarepa       — 米拉日巴尊者（噶举派 · 大手印 · 那洛六法）

# 南传
/master-buddhaghosa    — 觉音尊者（上座部论师 · 《清净道论》· 5世纪）
/master-mahasi-sayadaw — 马哈希尊者（缅甸内观 · 标记法 · 1904-1982）
/master-ajahn-chah     — 阿姜查（泰国森林禅林派 · 巴蓬寺传承）
```

### 教学模式（v0.7）

- **`/compare-masters`** — 多位法师对同一问题的并列对比（横向 / 单轮）
- **`/master-debate`** — 祖师就争议议题做多轮交叉辩论（v0.8 起：**每轮派 fresh subagent**，只携带对方上一轮 ≤80 字摘要 + 本方 cross_critique 弹药；轮数由 `debate_protocol.per_pair_overrides` 决定，默认 4 轮，`huineng-vs-tsongkhapa` / `ouyi-vs-tsongkhapa` 默认 5 轮）
- **`/master-curriculum`** — 按你的传统（禅 / 净 / 天台 / 华严 / 唯识 / 中观 / 格鲁 / 上座部）与当前位置（L0-L3）给出有时序的学修路径

**`/compare-masters` 用法示例：**

```
# 自动选择相关法师
/compare-masters 什么是空性

# 手动指定法师（推荐，结果更精准）
/compare-masters 什么是遍行因 --masters master-xuanzang,master-zhiyi,master-ouyi

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
生成的 persona 存放在 `create-master/masters/master-{slug}/`（`update --all` 会保留），并链接到
`~/.claude/skills/master-{slug}` 之后才能用 `/master-{slug}` 调用——生成器在终验通过后会做这一步；
若同名 skill 已存在（如重新生成了一位预置祖师），它不会覆盖，而是交给你决定。

---
