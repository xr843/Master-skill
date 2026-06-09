# `tests/persona/` — RAW/SPE/CUS Persona Fidelity Evals

v0.8 引入的 LLM-as-judge 评测层，在 `prebuilt/master-<slug>/meta.json` 的
`signature_phrases` + `style` schema 之上，用 [promptfoo](https://promptfoo.dev)
的 `llm-rubric` 断言机制把"祖师声音的可辨识度"做成可重复测量的工程指标。

## 三维度（RAW / SPE / CUS）

借鉴 [RoleLLM / RoleBench](https://github.com/InteractiveNLP-Team/RoleLLM-public)
的三维 persona 评估框架：

| 维度 | 全称 | 我们在这里测什么 |
|---|---|---|
| **RAW** | Raw Instruction-Following | 基础指令服从 + ETHICS 拒答能力（当代政治 / 医疗 / 法律 / 密法越界） |
| **SPE** | Specialist Knowledge | 本宗专属知识忠实度（不串到他宗、典故还原、术语正确） |
| **CUS** | Customised Style | 答疑节奏 + 签名短语 + 不掉书袋（祖师独特的"听起来像他"） |

每个 master config **必须** 同时覆盖三个维度，每个维度至少 1 个 case，全文
件至少 4 个 case。

## 目录布局

```
tests/persona/
├── README.md                          # 本文件
├── shared.yaml                        # persona prompt 模板（单点维护）
├── huineng.promptfooconfig.yaml       # 慧能（汉传 / 禅宗 / 中文）
├── ajahn-chah.promptfooconfig.yaml    # 阿姜查（南传 / 泰国丛林 / 英文）
└── tsongkhapa.promptfooconfig.yaml    # 宗喀巴（藏传 / 格鲁 / 中文）
```

这 3 个 master 是三大传统的代表样本 + 中英文双语支持的活文档。**剩余 11
个 master 的 promptfooconfig 按本目录模板由社区贡献**，schema 由
`scripts/validate-promptfoo-configs.py` 把关。

## 本地运行

### 仅 schema 校验（无 API key 也能跑）

```bash
# 强 schema：filename / dimension coverage / contains-any whitelist / shared.yaml sync
python3 scripts/validate-promptfoo-configs.py

# 可选：promptfoo 自带的 YAML schema 校验
npm install -g promptfoo
promptfoo validate -c tests/persona/huineng.promptfooconfig.yaml
```

### 跑完整 llm-rubric 评测（需 ANTHROPIC_API_KEY）

```bash
export ANTHROPIC_API_KEY=sk-ant-...
promptfoo eval -c tests/persona/huineng.promptfooconfig.yaml
promptfoo eval -c tests/persona/ajahn-chah.promptfooconfig.yaml
promptfoo eval -c tests/persona/tsongkhapa.promptfooconfig.yaml
```

约 6 个 case × 1 个 provider × 1 个 judge 调用 / case = 单 master 约 12 次
Opus 调用，单跑约 $0.10-$0.30 量级（视回答长度）。

## CI 行为（advisory 模式）

[`.github/workflows/persona-fidelity.yml`](../../.github/workflows/persona-fidelity.yml)
分两段：

1. **schema 校验** — **总是** 跑（无需 API key）。这是真正的"会 block PR"的
   gate：filename 约定 / RAW-SPE-CUS 全覆盖 / contains-any 在白名单内 / inline
   prompt 与 `shared.yaml` 同步。
2. **llm-rubric eval** — **仅在配置了 `ANTHROPIC_API_KEY` 时** 跑，并且用
   `|| true` 把退出码吞掉，**永不 block PR**。结果作为 artifact 上传供人工
   查看。
   - 项目当前政策（见 maintainer 备忘）：不为 LLM-as-judge 付费 CI。等社区
     验证评测价值后再决定是否升级为 hard gate。

## 为剩余 11 个 master 补 config 的步骤

1. 在 `shared.yaml` 顶部加新条目，按现有命名 `<slug_underscore>_persona_prompt`
   （例：`zhiyi_persona_prompt`，注意 `master-mahasi-sayadaw` 这种带连字符的
   slug 在 yaml key 里用下划线 `mahasi_sayadaw_persona_prompt`）。
2. 在 `scripts/validate-promptfoo-configs.py` 的 `SHARED_KEY_MAP` 里登记
   `"<slug>": "<yaml_key>"`。
3. 在本目录新增 `<slug>.promptfooconfig.yaml`，**第一个 prompt 字符串必须与
   shared.yaml 中对应 key 的内容逐字一致**（validator 强制）。
4. 至少 4 个 tests，按 `RAW: …` / `SPE: …` / `CUS: …` 前缀分类，三类全覆盖。
5. `contains-any` 断言里的所有 value 必须出自该 master 的
   `meta.json#signature_phrases`，或在 validator 的
   `EXTRA_ALLOWED_CONTAINS` 里登记（每条都要写理由注释）。
6. 跑 `python3 scripts/validate-promptfoo-configs.py` 直到 OK；
   有 key 的话再跑一次 `promptfoo eval` 看 rubric 通过率。
7. 提 PR。CI 自动跑 schema gate；eval 在你 fork 上是 advisory 跳过。

## 设计理由

- **为什么不直接用 fidelity.jsonl？** `scripts/test-fidelity.py` 用的是 must-cite /
  must-use 关键词的**确定性**断言，强但脆——遇到祖师换一个等价表达就 false
  negative。`llm-rubric` 适合 RAW（拒答能力）和 CUS（风格判断）这两类**软**
  指标。两者互补。
- **为什么 contains-any 要白名单？** 没有白名单时，作者可以随手往 contains-any 里
  塞任何关键词，rubric 也"通过"——但这通过的是噪声不是 fidelity。绑死到
  `signature_phrases` 让评测层和 schema 层互相校验。
- **为什么 prompt 要 inline + 强制与 shared.yaml 一致？** 因为 promptfoo
  没有 `file://shared.yaml#key` 这种 anchor 解引用。inline 是必要的，但是
  inline 会漂——所以 validator 强制一致性，shared.yaml 是 single source of
  truth。

## 参考

- [promptfoo: llm-rubric](https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/)
- [promptfoo: contains-any](https://www.promptfoo.dev/docs/configuration/expected-outputs/deterministic/)
- [RoleBench 三维度 RAW/SPE/CUS](https://github.com/InteractiveNLP-Team/RoleLLM-public)
- 本仓库 [`docs/persona-schema.md`](../../docs/persona-schema.md) — `signature_phrases` / `style` / `lore_triggers` 字段定义
