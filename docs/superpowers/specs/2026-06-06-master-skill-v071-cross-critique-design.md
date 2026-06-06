# Master-skill v0.7.1 — `cross_critique` Field Design

> 2026-06-06 · 在 v0.7（debate + curriculum 教学模式）基础上增量。每位单 master 的 `meta.json` 加 `cross_critique` 字段，记录"本祖师对其他主要传统的标准批判点"，让 `/master-debate` 的 R2 反驳从泛泛"反对"升级到"援引祖师本人立场"。**纯数据增量 + 一次 SKILL.md wiring + 一处 validator 扩展**，零回归。

---

## 0. 一句话

把 v0.7 spec §11 列为 v0.7.1 的"路径 B 增量"落地：14 位单 master 各加 2-3 条 `{target_master, position, citation}` 结构化对象，master-debate runtime 选定配对后查询并注入对方专属批判点，降稻草人风险。

---

## 1. 现状（实测 grounding）

| 现有 | 状态 |
|---|---|
| 14 个 `prebuilt/master-<slug>/meta.json` | 含 `sources` / `search_scope` / `disclaimer`，无 `cross_critique` |
| `prebuilt/master-debate/SKILL.md` | 8 个对立配对兜底表、4 轮结构、硬约束（含禁稻草人），但 R2/R3 反驳质量靠 LLM 自行生成 |
| `scripts/validate.py --strict` | 通过 meta.json 结构校验，无 `cross_critique` 相关检查 |
| `scripts/validate-curriculum-sources.py` | 已能 cross-check citation + master slug，可被 v0.7.1 复用 |

---

## 2. 目标 / 非目标

**目标**：
- 14 位单 master 各新增 `cross_critique` 字段（可选但建议覆盖该 master 在 debate 配对表中的配对对象）
- `master-debate/SKILL.md` 增"批判点查询"决策步骤，runtime 选定 (A, B) 后查 `A.cross_critique[?target_master == B]` 与 `B.cross_critique[?target_master == A]`，注入 R1/R2/R3 上下文
- 新 validator `scripts/validate-cross-critique.py` 强制结构 + citation 真实 + target_master 真实
- CHANGELOG + version bump 0.7.0 → 0.7.1

**非目标**：
- 不改 `master-debate` 4 轮结构 / 输出框架 / 硬约束
- 不动 `master-curriculum` / `compare-masters` / 单 master SKILL.md
- 不要求每位 master 都填满所有可能配对（覆盖 debate 配对表为底线）
- 不替 debate runtime 注入 cross_critique 的实际 LLM 行为，仅 SKILL.md 指示

---

## 3. Schema

每位单 master `meta.json` 顶层增加（可选）字段：

```json
"cross_critique": [
  {
    "target_master": "<slug>",
    "position": "<本祖师对该传统的核心批判点，简短 1-2 句，体现本祖师 voice>",
    "citation": "<经号 / Toh / 集成开示 id>"
  }
]
```

**字段语义**：
- `target_master`: kebab-case 单 master slug，必须存在于 `prebuilt/master-<slug>/`
- `position`: 10-300 字 zh-Hans 文本（validator 硬上下限），**关键约束**：是"本祖师立场对他派的回应"，**不是**"本祖师否认他派合法性"。建议落在 30-150 字范围，过长易跑题、过短易标签化
- `citation`: 必须是本 master `sources[].id` 中的真实条目（即批判须有本祖师文献依据）

**字段约束**：
- 整个 `cross_critique` 字段**可选**（缺失即视为空数组，向后兼容）
- 数组长度建议 0-5（写不出来的别凑数）
- `target_master` 在数组内可重复（一对祖师可有多个不同切入角度）
- `target_master` 不可指向 meta-skill（`compare-masters` / `master-debate` / `master-curriculum`）或自指（`target_master != self.slug`）

---

## 4. 覆盖目标（doctrinal scope）

**底线**：v0.7 master-debate 配对表中的 8 对必须双向有 entry——

| 配对（A ↔ B） | A.cross_critique → B | B.cross_critique → A |
|---|---|---|
| huineng ↔ yinguang | ✓ | ✓ |
| kumarajiva ↔ xuanzang | ✓ | ✓ |
| huineng ↔ zhiyi | ✓ | ✓ |
| tsongkhapa ↔ huineng | ✓ | ✓（huineng 共 3 个 target） |
| ajahn-chah ↔ mahasi-sayadaw | ✓ | ✓ |
| atisha ↔ huineng | ✓ | ✓（huineng 共 4 个 target） |
| ouyi ↔ yinguang | ✓ | ✓ |
| ouyi ↔ tsongkhapa | ✓ | ✓ |

总计 **16 个有向 entry**，分布到 9 位 master（huineng / yinguang / kumarajiva / xuanzang / zhiyi / tsongkhapa / ajahn-chah / mahasi-sayadaw / atisha / ouyi）。

**剩 4 位**（buddhaghosa / fazang / xuyun / milarepa）不在 debate 配对表中，可暂留空数组或 1-2 条选填，不强制。

---

## 5. master-debate wiring

`prebuilt/master-debate/SKILL.md` 新增"批判点注入"小节，位置在「轮次结构」之前：

```markdown
## 批判点注入

选定配对 (A, B) 后，runtime **必须**：

1. 读 `prebuilt/master-<A>/meta.json` 的 `cross_critique`，筛选 `target_master == B` 的 entry
2. 读 `prebuilt/master-<B>/meta.json` 的 `cross_critique`，筛选 `target_master == A` 的 entry
3. 把筛到的 `position` 串 + 对应 `citation` 作为"本祖师对对方的标准立场"上下文，注入：
   - R1（A 立论）：A 关于自己对 B 的立场，作为立论时区别于 B 的依据
   - R2（B 反驳）：B 关于自己对 A 的立场，作为反驳 A 立论的 grounding
   - R3（A 回应）：A 再次引用
   - R4（B 综合）：B 引用以呈现"双方共许 / 仍异"中的"仍异"

若任一 master 的 `cross_critique` 中没有对应 target 的 entry，注入**留空**——LLM 退回到 v0.7 既有的"禁稻草人 + 引经必经查证"硬约束兜底，不阻塞流程。
```

---

## 6. 新 validator `scripts/validate-cross-critique.py`

离线结构 + cross-check，CI 一票否决：

```python
# 伪代码
def validate(prebuilt_dir):
    known_masters = collect_master_slugs(prebuilt_dir)
    known_citations = collect_citations_per_master(prebuilt_dir)  # dict slug → set
    errors = []
    for meta_path in prebuilt_dir.glob("master-*/meta.json"):
        slug = meta_path.parent.name.removeprefix("master-")
        data = json.load(meta_path)
        cc = data.get("cross_critique", [])
        if not isinstance(cc, list):
            errors.append(f"{slug}: cross_critique must be list")
            continue
        for i, entry in enumerate(cc):
            if not isinstance(entry, dict):
                errors.append(f"{slug}#{i}: entry must be object")
                continue
            for k in ("target_master", "position", "citation"):
                if k not in entry or not entry[k]:
                    errors.append(f"{slug}#{i}: missing {k}")
            tm = entry.get("target_master")
            if tm == slug:
                errors.append(f"{slug}#{i}: cannot target self")
            if tm in ("curriculum", "debate", "compare-masters"):
                errors.append(f"{slug}#{i}: cannot target meta-skill {tm}")
            if tm and tm not in known_masters:
                errors.append(f"{slug}#{i}: target_master '{tm}' not found")
            cit = entry.get("citation")
            if cit and cit not in known_citations.get(slug, set()):
                errors.append(f"{slug}#{i}: citation '{cit}' not in {slug}'s sources")
            pos = entry.get("position") or ""
            if not (10 <= len(pos) <= 300):
                errors.append(f"{slug}#{i}: position length {len(pos)} out of [10, 300]")
    # debate 配对表覆盖率检查
    required_pairs = [
        ("huineng","yinguang"), ("kumarajiva","xuanzang"), ("huineng","zhiyi"),
        ("tsongkhapa","huineng"), ("ajahn-chah","mahasi-sayadaw"),
        ("atisha","huineng"), ("ouyi","yinguang"), ("ouyi","tsongkhapa"),
    ]
    for a, b in required_pairs:
        if not has_entry(a, b): errors.append(f"missing critique: {a} → {b}")
        if not has_entry(b, a): errors.append(f"missing critique: {b} → {a}")
    return errors
```

**TDD**：先写 `scripts/tests/test_validate_cross_critique.py`（覆盖 pass/fail/边界），再写实现。

---

## 7. 文档与版本

- `CHANGELOG.md` 新增 v0.7.1 entry
- `package.json` + 4 plugin manifests bump 0.7.0 → 0.7.1
- 顶层 `SKILL.md` 不动（教学模式 section 已含 master-debate）
- `README.md` / `README_EN.md` 可加一段"v0.7.1 注：debate 模式新增祖师本人对他派的批判点注入，减少稻草人"

---

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| `position` 文字写不准（断章取义 / 误读祖师立场） | (1) 必须配 `citation` 来自本 master sources（自证）；(2) PR review checklist；(3) 限制 30-300 字防过度发挥 |
| 配对表覆盖外的 master 被强制写 | scope §4 已明示底线只覆盖 debate 配对，其他选填 |
| `position` 变成贬他派的工具 | spec §3 明确"是回应不是否认"，写作 guideline 写入 `prompts/voice_reviewer.md` 类似目录（如有）或 PR review 标尺 |
| target_master 拼写错误 silently pass | validator §6 cross-check 已覆盖 |

---

## 9. 工作量估算

| 项 | 工时 |
|---|---|
| 16 个有向 entry doctrinal 写作（9 master meta.json） | 2-3d |
| `scripts/validate-cross-critique.py` + TDD tests | 1d |
| `master-debate/SKILL.md` 加批判点注入小节 | 0.5d |
| CHANGELOG + version bump + CI gate | 0.5d |
| **合计** | **≈ 4-5 天** |

---

## 10. 验收

- `python3 scripts/validate-cross-critique.py` 通过：所有结构 + cross-ref + 16 配对覆盖
- `python3 scripts/validate.py --strict` 仍通过（meta.json 加字段不破坏既有 schema）
- `python3 scripts/validate-fidelity.py` 仍通过
- `python3 -m pytest scripts/tests/ -q` 全绿（含新 validate_cross_critique 测试）
- 手动 dry-run 禅净 debate：R2/R3 反驳明显含本祖师对他派立场的具体援引而非泛泛反对
- `node bin/cli.mjs list` 仍正确列出 17 个 skill
- CHANGELOG / package.json / 4 plugin manifests 全部为 0.7.1

---

## 11. 后续（v0.7.2 / v0.8）

- v0.7.2：buddhaghosa / fazang / xuyun / milarepa 补 cross_critique（按需）
- v0.8：debate 引入 LLM-as-judge 中立观察轮 + curriculum 接 fojin RAG（路径 C）
- 远期：cross_critique 也可被 `master-curriculum` 的"可能的盲点"小节复用（自动生成"本传统看他派常见误判"提示）

---

## 关联

- v0.7 spec / plan / PR #28 (`dd2cdf5`)
- memory: [[project_master_skill_v07]] · [[project_master_skill_backlog]] · [[feedback_full_ship_pipeline]]
