# Contributing to Master-skill

欢迎贡献！本项目分三类改动，每类流程不同——**请先判断你的改动属于哪一类**，再按对应流程走。

> 📜 贡献前**必读**：[`ETHICS.md`](ETHICS.md) — AI 透明度、版权 Tier、教界边界、内容授权。违反伦理条款的 PR 不会 review。

---

## 三类改动

### ① 代码 / CI / 工具链

`scripts/**`, `tools/**`, `bin/**`, `hooks/**`, `.github/**`, `tests/`（非 fidelity）

流程：**普通 GitHub PR**。满足 Python 3.9+、现有测试通过、`python scripts/validate.py --strict` 绿色即可。

**新加一道门禁，必须让它在 PR 上真的跑起来。** `scripts/` 下每个带 `main` 的脚本，
要么能从某个 `on: pull_request` 的 workflow 到达（直接写进 `run:`，或被已可达的脚本
`import` / `spec_from_file_location` 加载），要么登记进 `check-gate-liveness.py` 的
`NOT_A_PR_GATE` 并写明为什么不跑。登记是**双向**校验的：脚本已删、或它其实已经在 PR 上
跑了，那条申报同样报错——一个过期的借口比没有申报更糟，它是个假的警告。

这条规矩是有来历的：2026-09-16 查出 `validate-citation-templates.py` 与
`validate-self-audit-sources.py` 只出现在 `package.json` 的 `test` 串里，而 `npm test`
只由 `npm-publish.yml` 在**发版时**运行——两道门禁写好了、有单测、也被
`test_gates_actually_fire.py` 证明过会红，却从未守过任何一次改动。更早还有一次同样的：
`validate-curriculum-sources.py` 曾"没接进任何 workflow、任何 npm 脚本、任何子检查，
只有自己的单元测试"。两次都不是代码写错，是**没接线**，而绿灯看起来一模一样。

### ② 文档 / README / 脚本注释 / 翻译

`README.md`, `README_EN.md`, `docs/**`, `CHANGELOG.md`, 其它非 `prebuilt/**` 的 markdown

流程：**普通 PR**。不需要跑 fidelity 测试，CI 中的 validate / smoke job 会跳过（除非改了其它触发路径）。

### ③ 贡献 / 修改法师内容（⚠️ 最严，必读）

`prebuilt/**`, `prompts/**`

涉及：

- 新增一位法师
- 修改已有法师的 `teaching.md` / `voice.md` / `sources/`
- 修改 fidelity 测试用例

流程：见下方 [§3 贡献一位新法师](#3-贡献一位新法师)。

---

## 开发环境

```bash
git clone https://github.com/xr843/Master-skill
cd Master-skill

# Python（用于 validate / fidelity / verify-links）
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-eval.txt  # 仅 fidelity 实跑需要（钉版的 anthropic / openai / pytest；**需 Python ≥ 3.10**，两个 SDK 的地板）

# Node（用于 npx installer）
# 需要 Node.js >= 18
npm install -g .  # 可选，本地测试 CLI
# 注：npm test / npm run validate 调用 `python3`（系统自带或 venv 内均可）
```

**改 `.github/workflows/**` 时另外注意**：CI 的 actionlint 门禁会连带跑 shellcheck，
而 actionlint 在本机**找不到 shellcheck 就静默跳过那一半检查** —— 本地绿、CI 红。
本地复现要先装 shellcheck，再跑 `actionlint`。

```bash
# 首选；若系统 Python 受 PEP 668 管控（Debian/Ubuntu/WSL 常见），pip 会拒装
pip install shellcheck-py

# 退路：官方静态二进制，解开就能用，不动系统 Python
curl -sL https://github.com/koalaman/shellcheck/releases/download/v0.10.0/shellcheck-v0.10.0.linux.x86_64.tar.xz \
  | tar -xJ --strip-components=1 -C /tmp shellcheck-v0.10.0/shellcheck
PATH="/tmp:$PATH" actionlint
```

**装完先验它真的在跑**：actionlint 找不到 shellcheck 时不会报错，只会静默
少跑一半检查——绿灯看起来一模一样。拿一段故意写坏的脚本试一次：

```bash
mkdir -p /tmp/probe/.github/workflows && cd /tmp/probe && git init -q
printf 'name: p\non: push\njobs:\n  j:\n    runs-on: ubuntu-latest\n    steps:\n      - run: ls | tail -1\n' \
  > .github/workflows/p.yml
actionlint    # 应报 SC2012；什么都不报，就说明 shellcheck 没在跑
```
2026-09-07 就靠它抓到一处：`exit` 被插在结果汇总块之前，整段变成死代码。

**基本健康检查：**

```bash
# Lint SKILL.md frontmatter — 每位法师必须通过
python scripts/validate.py --strict

# Fidelity 结构（不调 API）
python scripts/validate-fidelity.py

# Fidelity 干跑（显示测试用例，不调 API）
python scripts/test-fidelity.py --all --dry-run

# Fidelity 实跑（需要 ANTHROPIC_API_KEY，一次 ≈ $0.05-0.10）
ANTHROPIC_API_KEY=sk-... python scripts/test-fidelity.py --master master-zhiyi --max-tests 1

# Python 单测（判分器、引用审计器、各项门禁 —— 只跑 `npm test` 也会覆盖，
# 但改 scripts/ 时单独跑这条更快）
python -m pytest tests/ scripts/tests/ -q
```

`npm test` 会把上面这些（除需要 API key 的实跑）串起来跑一遍，**包括 Python 单测**——
CI 一直单独跑 `pytest`，直到 2026-09-03 本地 `npm test` 才补上这一步；改
`scripts/**` 前先跑一次，避免在 CI 才发现单测崩了。

---

## § 1 分支与提交约定

- **分支命名**：`feat/<short>`、`fix/<short>`、`docs/<short>`、`chore/<short>`、`master/<slug>`
- **Commit 格式**：[Conventional Commits](https://www.conventionalcommits.org/)（`feat:` / `fix:` / `docs:` / `chore:` / `refactor:` / `test:` + 可选 scope）
- **Commit message 语言**：代码/基础设施类改动用英文，佛教内容类改动中英文均可，但 PR description 需要有中文摘要（方便教内读者审阅）

---

## § 2 PR 评审清单

提交 PR 前自检：

- [ ] CI 绿色（validate 必过；fidelity-smoke 在未配置 `ANTHROPIC_API_KEY` 时为 advisory pass——目前主仓与 forks 均未配置，绿勾代表结构校验通过，实跑评分是本地/发版前手动步骤）
- [ ] CHANGELOG.md 的 `[Unreleased]` 章节已更新（除非是纯 typo）
- [ ] 涉及 `prebuilt/**` 的改动 → 已 review ETHICS.md §2（版权 Tier）、§3（教界边界）
- [ ] PR description 说明**做了什么 + 为什么**，而非只列改动文件

---

## § 3 贡献一位新法师

### 3.1 前置检查（必看 [`ETHICS.md`](ETHICS.md)）

**这位法师可以收录吗？**

| 情形 | 判断 |
|-----|------|
| 生卒明确，圆寂超过 50 年（CN/TW）或 70 年（大多数其它辖区） | ✅ Tier A，可直接 PR |
| 近现代法师，亲授弟子在世 / 所属寺院仍运营 | ⚠️ Tier B，PR 必须附 `prebuilt/{slug}/LICENSE.md` 授权证明 |
| 在世法师 | ❌ Tier C，不接受 |
| 主流学界对身份 / 著作有争议 | ❌ Tier C，不接受 |
| 汉传、印度、藏传或南传等有可靠史料与合规原典来源的传统 | ✅ 按同一版权、史实、声明来源与教义审查标准评估；不评宗派高下 |

**想收录但不确定？** 先开一个 [new_master Issue](https://github.com/xr843/Master-skill/issues/new?template=new_master.yml) 征询意见，**不要先写完再提 PR**——已经投入精力再被拒成本太高。

### 3.2 选项 A：交给 `/create-master` 生成（推荐）

```bash
# 在 Claude Code / Cursor 等 AgentSkills 环境
/create-master 某某法师
```

生成管线会：

1. **intake** — 3 问收集信息（传承、核心教义、可用文献）
2. **collect** — 从 FoJin 或人工输入采集该法师所属来源族的声明原典（CBETA / BDRC / Toh / SuttaCentral / PTS / 合规编纂开示）
3. **analyze** — `sutra_analyzer` + `voice_analyzer` 并行分析
4. **review** — 二阶段独立审查：教义准确性 → 风格一致性
5. **write** — 生成 `prebuilt/<slug>/` 目录结构
6. **validate** — 自动跑 `validate.py` + `validate-citation-contract.py` + `validate-fidelity.py`

然后你手动：

- Review 生成结果，补充 `references/teaching.md`、`voice.md` 的细节
- 起草 5 条 `tests/fidelity.jsonl`（1 basic + 2 intermediate + 2 advanced）
- 跑一次 `test-fidelity.py --master <slug>` 确认 ≥ 4/5 通过

### FoJin 查不到某部经时

周检（`.github/workflows/verify-links.yml`）会为「FoJin 里查不到的 CBETA id」
开 issue。如果那是 **FoJin 确实不收录**的一部（例如嘉兴藏 J 系列），把它登记进
`tools/fojin-known-absent.json`，它就不再计入 `Not found in FoJin` —— 否则同一条
每周开一次，而一个永远响的告警等于没有告警：真出现新缺失时没人看得出来。

登记有三条硬性要求，`tests/test_verify_sources.py` 会验：

1. **写清理由**（≥ 20 字），并给出**可解析的核验日期**——不接受「TODO」「待定」。
   理由里要说明是怎么确认的，最好附一次对照查询（同一次请求里另一个 id 能查到，
   才能区分「缺这部书」和「接口不通」）。
2. **该 id 必须已在某个 `meta.json` 的 `sources[]` 里声明**。给一个没人引用的 id
   预留豁免，等于为将来的伪造引用开后门。
3. 清单会**双向**失效：登记过的 id 若哪天在 FoJin 查得到了，周检报 `[STALE]`
   并计入失败，要求删掉那一条。清单不会悄悄烂掉。

离线引文审计不受此清单影响——只要 id 在 `meta.json` 里声明过，
`verify_citations.py` 照常解析。它影响的只是能不能附 fojin.app 活链接。

### 摘录里的「原典」块

`sources/*-excerpts.md` 里以「原典」开头的标签、后接 `>` 引文和「引用格式」的块，
人设会当作原文引给用户。周检逐个分句去 CBETA 所引的那一卷里找，有分句找不到就计入
`Excerpt quotes not in the cited text` 并开 issue（2026-09-15 首次核查，63 段里 19 段
对不上）。所以：

1. **照抄 CBETA 原文**，省略处用 `……`；校勘说明、浅释写在引文块外的「注：」行。
2. **标卷次**：`【《书名》卷N，经号】`。超过 30 卷的书不标卷，周检只能记为「未知」。
3. 整理、概括的文字不要写成「原典」块：标成「要义（整理，非原文）」，也不加 `>`。
4. `meta.json` 的 `lore_triggers` 同样受查：`——` 之前必须是原文。

比对按读音，繁简写法不影响结果；同音错字查不出来，抄完仍要自己对一遍。

### 人设里当原话引的句子

`references/` 与 `sources/` 里五种写法会被周检当作引文送去 CBETA 全文检索：
voice.md 的编号示例句（`1. "……"`）、以 `> "` 开头的引用块、同一行里带书名号的
「云／曰」、**具名引出且带冒号**的（`佛说："……"`、`神秀偈："……"`、
`老和尚说："……"`）、以及**同一行里《书名》后紧跟的引号片段**（`如《金刚经》
"一切有为法……"`）。后两种是 2026-09-16 补上的：此前慧能的风幡、神秀与达摩的偈、
罗什所引《金刚经》、阿姜查摘录里以「佛说：」引出的三段巴利经文、虚云的四段开示，
一条都没被检查过（49 条在查，13 条没查）。查不到就计入
`Quoted lines CBETA does not have` 并开 issue
（2026-09-15 首次手工核查：玄奘「因明立量，非为诤胜」、智顗「功在渐次，证在
圆融」等五条查无出处，另有三条分别是灌顶、澄观、彭际清的话挂在祖师名下）。所以：

1. **示例句要照抄原文**，并在括号里标出处与卷次。想写自己的概括，就在句外写，
   或在同一行标「转述」「非原文」「主旨」——标了的行不送检索。
2. **引他书要在同一行写明**。引文只要在 CBETA 里找得到、却不在该人设声明的作品里，
   记为「未判定」不报错（玄奘引窥基所记的唯识比量即是一例），但读者需要知道出处。
3. **只声明 CBETA 来源的人设**（慧能、罗什、龙树、智顗、法藏、玄奘、蕅益），
   查不到即判错；另有编集开示或藏文来源的人设（虚云、印光、阿底峡、宗喀巴等），
   查不到只记未判定——《法汇》《文钞》本来就不在 CBETA 里。
4. **检索只认繁体**，脚本用 opencc 的 `s2tw` 转换并把「爲」「衆」归一成「為」「眾」；
   少了这一层，《坛经》《中论》的真引文都会被报成查无此句。
5. **每条引文都要能让读者查到出处**，否则 `scripts/validate-quote-attribution.py`
   会在**每个 PR** 上报错（它只读本地文件，不必等周检）。出处写在同行、下方的
   `> 出处：` 行、同一编号列表的兄弟条目、或上方小节标题里，四者居其一即可。
   这一条与第 2 条不同：第 2 条管"引的是不是该人设声明过的书"，这一条管"读者能不能
   自己查"——2026-09-16 实测，慧能有五条货真价实的《坛经》原文（风幡、何期自性、
   迷时师度、神秀慧能二偈、达摩付法偈），前面每一道检查都放行，唯独通篇没写出自哪部，
   读者无从核对。已逐条对 T48n2008 核实并补上品名。
6. **讲"这句该不该引、该怎么标"的行整行不送检索**。纠错说明（「某句常被当作某某的话
   引用，但《某经》中没有」）、禁用示例（「不可用……作为某某立场」）里的引号片段不是
   引文——它们恰恰是在记录一句伪托语，若照送检索，周检会把这条**纠错记录本身**判成
   伪造引文。标记词只认关于引用行为的成句短语（`常被当作`、`应保守表述`、`不要把`、
   `引用规范`、`》中没有` 等）；不要往里加「勿」「不可用」这类泛词——实测会误伤
   《坛经》「勿使惹尘埃」、罗什「且勿急」、虚云「不可用意识思量卜度」三处真引文。

### CBETA 之外的编集语录

上一步对虚云、印光这类祖师只能记「未判定」——他们的语录本来就不在 CBETA 里，
而 2026-09-15 修掉的那批拼接引文恰恰长在这个盲区。`tools/compiled-teaching-sources.json`
登记这些书的免费全文地址，周检 3i 进原书逐字找，结果计入
`Quoted lines the compiled teachings do not have`。登记要求：

1. **`coverage` 决定这一步能不能判错**。`complete` 表示该祖师声明的编集语录**全都**
   在清单里取得到，找不到即判错；只要还有一部声明了却取不到全文，就写 `partial`，
   找不到只记未判定。印光的正编、续编、三编就是《文钞》的全部，标 `complete`；
   虚云标 `partial`——净慧编的《开示录》比岑学吕的《法汇》多出六十余万字，
   BFNN 上没有，真引文完全可能出自那里。**宁可少判，不可错判。**
2. **写清理由与核验日期**，并说明是怎么确认「全都取得到」的。理由要能让人复核，
   不接受「应该齐了」。
3. **地址要钉住底本**。殆知阁用 commit 号而不是分支名——它的默认分支是 `data`
   不是 `master`，用分支名取既会取错也会随时变。取不到时 3i 记未判定，不判错。
4. **取不到 ≠ 原书没有**。网络失败、编码错、页面改版都只会让这一步记未判定；
   能判错的只有「全文取到了、而且确实没有这句」。

### 引用格式指向 CBETA 之外的「原典」块

3f 只收**引用格式带 CBETA 经号**的「原典」块。《文钞》《法汇》这类书没有经号，
它们的块因此对 3f 不可见；而块里的 `>` 行多是裸行文、不带引号，采集引文行的那一步
（3h/3i）同样收不到。2026-09-16 实测：master-yinguang 有五个这样的块，其中两块
是用真语拼接出来的改写，却一直以「原典」示人，**没有任何一步检查看得见它们**。

现在这类块由 3i 一并核对，计入 `Excerpt blocks the compiled teachings do not have`：

1. **块要能对上原书**。逐段（以 `……` 分隔）拿到 `tools/compiled-teaching-sources.json`
   登记的全文里找，找不到即判错——前提是该祖师语料标了 `complete`。
2. **语料不全就只能确认、不能定罪**；原书取不到一律记未判定。判错的门槛是
   「全文读到了、而且确实没有这句」。
3. **引用格式要标到篇**。印光那块原标《一函遍復》，实际出自《复唐能诚居士书》——
   篇名错了，前面每一步都看不出来，因为它们根本没在看这个块。

### 声明的 BDRC 作品号

`meta.json` 里 `BDRC:W…` 形式的作品号，周检会去 BDRC（ldspdi.bdrc.io）取记录。
查无此号，或记录的题名里找不到声明的藏文题名，就计入 `BDRC records that do not match`
并开 issue（2026-09-15 首次核查：master-milarepa 的两个号一个是宗喀巴全集、一个
BDRC 根本没有，挂了 73 处）。所以：

1. **号要在 BDRC 上核过**：打开 `https://ldspdi.bdrc.io/resource/<号>.json`，顺着
   `instanceReproductionOf` / `instanceOf` 看 MW 实例与 WA 作品的题名和作者。
   `library.bdrc.io/show/bdr:<号>` 对任何号都打开一个页面，不能拿它当证据。
2. **用影像实例号**（`W` 后紧跟数字，如 `W1GS56158`）：引文门禁只认这种写法，
   `MW…` / `WA…` 会被当成字段名略过。
3. **写藏文题名**：SKILL.md frontmatter 同号条目的 `tibetan_title`，或 `meta.json`
   题名括注里的 Wylie。没写题名，周检只能记为「未知」。题名写得越全越好——只写
   「rNam thar」，别人的传记也对得上。
- 提 PR

### 3.3 选项 B：手工编写

参考现有法师 `prebuilt/master-yinguang/` 的完整结构：

```
prebuilt/master-<slug>/
├── SKILL.md             # 必须。frontmatter 见下
├── meta.json            # 必须。sources + citation_contract + search_scope
├── references/
│   ├── teaching.md      # 必须。教义体系，合同覆盖的内容附声明来源引用
│   └── voice.md         # 必须。Layer 0/1/2/3 四层表达风格
├── sources/
│   ├── INDEX.md         # 必须。本目录导览
│   └── *.md             # ≥ 2 篇合规的声明来源核心段落或摘要
└── tests/
    └── fidelity.jsonl   # 必须。5 条 Q&A 测试用例
```

**SKILL.md frontmatter 必填字段：**

```yaml
---
name: <slug>              # 小写英文或拼音，作为 `/命令` 触发词
description: Use when user asks about ..., triggers include ...
version: 0.1.0
license: MIT
lineage: <宗派>
dates: 生年-卒年
sources:
  - title: <经典名称>
    source_type: <cbeta | tibetan_canon | pali_canon | compiled_teaching | ...>
    source_id: <该来源族中的声明 ID>
  - ...                    # 至少 3 部经
citation_format: "【《{title}》，{source_id}{locator}】"
verified_by: <你的 GitHub handle>
verified_at: <YYYY-MM-DD>
---
```

`meta.json` 是运行时来源合同的权威位置；`allowed_source_types` 必须等于 `sources[].type` 的排序去重值：

```json
{
  "sources": [
    {"type": "pali_canon", "id": "MN 10", "title": "Satipaṭṭhāna Sutta"}
  ],
  "citation_contract": {
    "version": 1,
    "claim_policy": "declared_sources_only",
    "required_for": ["doctrinal_claim", "practice_guidance", "text_interpretation"],
    "allowed_source_types": ["pali_canon"],
    "minimum_claim_coverage": 0.9,
    "live_retrieval_allowed": true
  }
}
```

完整来源族与 ID 规范见 [`references/source-conventions.md`](references/source-conventions.md)；结构验证运行 `python3 scripts/validate-citation-contract.py`。

**HARD-GATE 铁律（写入任何 `teaching.md` 前请自检）：**

1. 每一条教义断言、修行指导与文本解释必须附一个能解析到 `meta.json.sources[]` 的**真实声明来源 ID**
2. 不得捏造来源 ID；类型必须属于 `citation_contract.allowed_source_types`
3. 不得为虚构 / 神话 / 未有史实记载的人物建角色
4. 不得大段抄录仍在版权期内的现代白话译本或学术校注

### 3.4 Voice.md 四层结构

见 `prebuilt/master-yinguang/references/voice.md` 作为参照。重点：

> ⚠️ **v0.6 命名约定**：所有新 master 目录与 frontmatter `name:` 必须以 `master-` 开头（如 `prebuilt/master-foo/` + `name: master-foo`）。两个 meta-skill 例外：`compare-masters` 与 `create-master` 保持原状（避免 `/master-compare-masters` 重复前缀）。详见 [CHANGELOG §0.6.0](CHANGELOG.md#060--2026-05-02)。


- **Layer 0 — 硬规则**：[`ETHICS.md` §3](ETHICS.md) 的禁止行为必须原文复制到此
- **Layer 1 — 身份**：生卒、传承、核心立场
- **Layer 2 — 表达风格**：常用比喻、开场方式、称呼
- **Layer 3 — 教学方法**：循序渐进的路径、遇困惑时的处理

### 3.5 Fidelity 测试用例怎么写

`tests/fidelity.jsonl` 每行一个 JSON，字段：

```json
{
  "q": "用户会问的典型问题",
  "must_cite": ["T48n2008", "MN 10", "Toh 4465"],
  "must_mention": ["核心术语1", "核心术语2"],
  "must_convey": ["判不了的要求"],
  "must_not_contain_first_turn": ["学生啊", "师兄"],
  "difficulty": "basic|intermediate|advanced"
}
```

**`must_mention` 与 `must_convey` 的分界（重要）：**

`must_mention` 是**纯子串匹配**。只放**必须原样出现的术语**——`阿赖耶`、
`khaṇika-samādhi`、`十念法`、`/compare-masters`。

放**命题或概念**进去会量错。2026-08-31 全量跑的逐条裁定
（`eval/reports/ADJUDICATION.md`）实测：447 条 `must_mention` 里 56 条判错，
其中 54 条根本不是字串问题——夹具要 `方便`、回答写「应病与药」；要 `不是虚无`、
回答写「空非虚无」；要 `根机`、回答写「人有迷悟」。**列同义词表是拿模型输出反向
拟合夹具**，既挡不住假阳性，也会一路滑向凑分。

这类要求写进 `must_convey`：**既不判通过、也不判失败，记为待裁决**。这是本仓库
对 `audit_unavailable` / `unparsed_citations` 用的同一条原则——量具不得宣称它判过
它判不了的东西。

⚠️ **`must_convey` 不能自己往里加。** `scripts/validate-fixture-terms.py` 会要求
每一条都能追溯到 `eval/reports/adjudication-*.json` 里一条 `instrument` / `fixture`
裁定，而那条裁定必须带一句已被核对过确实存在于回答原文里的引语。裁定为 `upheld`
（真失败）的词，永远不能改判为「判不了」。把碍事的检查挪进 `must_convey` 让构建
变绿，正是这道门禁存在的理由。

**5 条分布建议：**

- 1 条 `basic` — 宗派入门问题（smoke 会优先跑这条）
- 2 条 `intermediate` — 核心教义（如 "三性" / "信愿行"）
- 1 条 `advanced` — 跨宗派对话 / 批判性问题
- 1 条 boundary 测试 — 试探 "给我授戒 / 印证我开悟了吗" 一类，must_not_contain 检查 AI 是否正确拒绝

### 3.6 Review 过程

PR 提交后：

1. CI 自动跑 validate + fidelity-smoke（抽本 PR 修改的法师做 smoke）
2. 维护者 review 教义准确性 + 风格一致性 + 版权 Tier 判断
3. 如有佛学学者 / 教内法师愿意 review，欢迎在 PR 评论 tag 维护者协调
4. Review 周期：7-14 天（含教内邀请意见）

---

## § 4 修改已有法师

- 小修（typo、措辞）：直接 PR
- 大修（新增教义章节、修改 Layer 1-3 风格）：先开 issue 讨论
- 修改 fidelity 测试用例：**PR description 必须说明新旧用例的差异以及为何新用例更能体现该法师风格**——不要为了让测试通过而放宽标准

---

## § 5 行为准则

见 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)。

本项目涉及佛教内容，请在讨论中：

- 不评判宗派高下
- 不借项目传播个人修行见解
- 不对其他贡献者做教学式 / 居高临下的发言
- 教理争议以学界主流共识 + 对应传统的声明原典为准，而非个人修学经验

---

## § 6 为单 master 补 `lore_triggers`（v0.8）

v0.8 在 `meta.json` 引入 `lore_triggers`，让 runtime 在用户提问命中 keyword 时按需注入一段真实祖师 quote。详细 schema 见 [`docs/persona-schema.md`](docs/persona-schema.md)。

补 entry 的流程：

1. **先有原典**：打开 `prebuilt/master-<slug>/sources/<id>-excerpts.md`，找到一段你想暴露的真实段落。如果 excerpts 里没有合适段落，**不要为了补 entry 而新摘原典**——先开 PR 加 excerpts，再回头补 entry。
2. **content 必须是文献原文**（可在末尾加一句"——"开头的浅释，但不得改写经文本身）。长度 80-300 字。
3. **source_ref**：写本 master `sources[].id` 中的真实 id，可加 `#章名` 锚点（如 `T48n2008#般若品`）。validator 校对前缀。
4. **keys**：用户最自然会用到的提问词，3-6 个为佳。OR 语义。
5. **何时用 `selective: true`**：当 keys 容易在非本主题语境下命中（如"定慧"在大多数佛教讨论里都会出现），用 `secondary_keys` 加副词收窄。validator 强制 secondary_keys 存在时 selective 必须 true。
6. **本地验证**：
   ```bash
   python scripts/validate-persona-fidelity.py
   # 或
   npm run validate:persona-fidelity
   ```
7. **提交 lore_triggers PR 前的自检（v0.8 起强烈建议，v0.9 起 hard gate）**：
   ```bash
   # advisory 模式（与 CI 一致）
   python scripts/validate-lore-triggers-content.py --master master-<slug>
   # 或 npm
   npm run validate:lore-content

   # 强制硬失败（在 PR 提交前本地预演 v0.9 行为）
   python scripts/validate-lore-triggers-content.py --strict --master master-<slug>
   ```
   该 validator 在你的 `content` quote 上做归一化 LCS / SequenceMatcher
   匹配，校验是否真在 `sources/*-excerpts.md` 中找得到。三态：

   - `PASS`：在 sources/ 找到 → 直接提交
   - `WARN`：仅在 references/ 找到 → 强烈建议先扩展 sources/excerpts.md
     使 v0.9 hard gate 启用时仍 PASS
   - `FAIL`：两处都找不到 → **必须**改 content 或扩展 excerpts；这是
     伪造的明显信号

   详细阈值与原理见 [`docs/persona-schema.md`](docs/persona-schema.md#lore_triggers-content-完整性自动验证v08)。
8. PR description 必须列出 entry 数 + 引用来源章节，方便 maintainer 与 excerpts 文件对照。

**禁止**：

- 改写经文（无论"为了易读"还是"为了简洁"）
- 把 secondary teaching（讲记 / 现代释义）冒充原典
- entry > 5 条/master 一次性提交（一次 PR 限制 3-5 entry，保证 reviewer 能逐条核对）

---

## § 7 依赖 PR（Dependabot 自动开）

本仓库自 v0.8 起开启 [Dependabot](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates)，每周一自动开四类依赖升级 PR：

| 生态 | 监控目标 |
|------|---------|
| `github-actions` | `.github/workflows/*.yml` 中所有 SHA-pin 的 actions |
| `npm` | `package.json` 依赖 + workflow 中 `npm install -g promptfoo@<ver>` |
| `pip` | `requirements.txt` + `requirements-eval.txt`（validate / fidelity 工具链） |
| `cargo` | `desktop/Cargo.lock`（408 个 crate；桌面版是**唯一**下载即执行的产物） |

### ⚠️ `anthropic` / `openai` 的升级 PR：绿灯不算数

评测的评分路径**没有 key 就不跑**，所以这两个 SDK 的破坏性变更在 CI 上**完全不显形**——
它会一路绿到有人真花钱跑全量的那一刻，也就是发现成本最高的时刻。
Dependabot 一周内提过四次这两个包的升级，每次都带绿勾。

2026-09-14 起这句话只对一半：线协议与响应解析层面的破坏，CI 现在看得见（见下文
`smoke-eval-sdk.py`）；**真实模型的行为变化**仍然只有付费跑分才看得见。

评审这类 PR 时跑：

```bash
pip install -r requirements-eval.txt      # 装成 PR 里钉的那个版本
python3 scripts/check-eval-sdk-surface.py
python3 scripts/smoke-eval-sdk.py
```

前者导入实际装上的包、逐项读 `test-fidelity.py` 真正调用的表面，并核对装的
就是钉的那个版本。缺任何一项则退出 1 并指名。

后者更进一步：起一个本地假服务，按各家的线协议应答，让 `test-fidelity.py`
**真的**构造请求、由钉住的 SDK 发送并解析，再走一遍判分与引文审计——不需要
key，不联网，不花钱。签名没变而线协议或响应模型变了，只有它看得出来。
CI 的 validate job 在每个 PR 上都跑它，**并且同时跑 `--break`**（假服务返回
缺正文的回复、断言不变，必须退出 1）——一个不会失败的冒烟测试只是个绿勾。

**maintainer review 流程**（也欢迎贡献者帮忙跑）：

1. **CI 必须全绿**——所有 required status checks 是依赖更新最可靠的回归信号。
2. **SHA 真实性核对**（仅 github-actions PR）：
   ```bash
   gh api repos/actions/<name>/git/refs/tags/<new-version> --jq '.object.sha'
   ```
   与 Dependabot PR 里写的 SHA 比对，一致才合并。
3. **major bump 不可自动合并**：major 版本通常含 breaking change，必须人工读 release note + 跑 fidelity smoke 确认行为不变。
4. **minor / patch**：CI 绿即可合并，合并方式与本仓库其它 PR 一致——`gh pr merge --merge`（保留 commit 历史）。

如需手动触发一次扫描：仓库 Settings → Code security and analysis → Dependabot → "Check for updates"。

> 报告 Dependabot 误判 / 漏报：开普通 issue，标签选 `dependencies`。

---

## 问题？

- 技术问题 → [Bug Report](https://github.com/xr843/Master-skill/issues/new?template=bug_report.yml)
- 新法师建议 → [New Master Proposal](https://github.com/xr843/Master-skill/issues/new?template=new_master.yml)
- 教界边界疑虑 → [Boundary Violation](https://github.com/xr843/Master-skill/issues/new?template=boundary_violation.yml)（P0，优先处理）
- 一般讨论 → [GitHub Discussions](https://github.com/xr843/Master-skill/discussions)
- 紧急版权下架 → xianren843@protonmail.com（48 小时回复）

感谢你愿意为汉传佛教数字人文贡献一份力。合十。
