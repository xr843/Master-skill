# Master-skill v0.7 — `/master-debate` + `/master-curriculum` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two new prebuilt meta-skills (`master-debate` for 4-round adversarial dialectic, `master-curriculum` for sequenced study paths) on top of v0.6's 15 masters, with no changes to existing master skills and full offline operation.

**Architecture:** Two new `prebuilt/master-{debate,curriculum}/` directories that compose existing master metadata. One new offline validator (`validate-curriculum-sources.py`) cross-checks every citation against the union of all master `meta.json.sources[].id`, and every `/master-<slug>` reference against the filesystem. Existing CI workflow auto-covers both new skills.

**Tech Stack:** Python 3.12 (validators), Markdown + YAML frontmatter (SKILL.md), JSONL (fidelity tests). No new dependencies.

**Spec reference:** `docs/superpowers/specs/2026-06-06-master-skill-v07-debate-curriculum-design.md`

**Branch:** `feat/v0.7-debate-curriculum` (already created and on it)

---

## File Map

**Created:**
- `prebuilt/master-debate/SKILL.md` — debate skill prompt
- `prebuilt/master-debate/tests/fidelity.jsonl` — 8 test cases
- `prebuilt/master-curriculum/SKILL.md` — curriculum skill prompt
- `prebuilt/master-curriculum/tests/fidelity.jsonl` — 8 test cases
- `prebuilt/master-curriculum/references/chan.md` — 禅宗 path
- `prebuilt/master-curriculum/references/jingtu.md` — 净土
- `prebuilt/master-curriculum/references/tiantai.md` — 天台
- `prebuilt/master-curriculum/references/huayan.md` — 华严
- `prebuilt/master-curriculum/references/weishi.md` — 法相唯识
- `prebuilt/master-curriculum/references/sanlun-zhongguan.md` — 三论/中观
- `prebuilt/master-curriculum/references/gelug-madhyamaka.md` — 格鲁应成中观
- `prebuilt/master-curriculum/references/theravada-vipassana.md` — 上座部内观
- `scripts/validate-curriculum-sources.py` — citation/slug cross-check
- `scripts/tests/test_validate_curriculum_sources.py` — TDD tests for validator

**Modified:**
- `scripts/validate-fidelity.py` — extend `VALID_BOUNDARIES` (3 new values) + add `must_select_pair` / `must_have_rounds` / `must_cite_per_round` / `must_cite_only_existing_sources` / `must_recommend_existing_master` to allowed assertion fields
- `SKILL.md` (top-level) — rename 「对比模式」 section to 「教学模式」, add 2 commands
- `README.md` — sync 教学模式 section + example
- `README_EN.md` — sync EN translation
- `CHANGELOG.md` — add v0.7.0 entry
- `package.json` — bump 0.6.0 → 0.7.0, append description note
- `.claude-plugin/plugin.json` — bumped by `.version-bump.json` script
- `.claude-plugin/marketplace.json` — bumped by script
- `.cursor-plugin/plugin.json` — bumped by script
- `gemini-extension.json` — bumped by script

---

## Phase 1 — Validators (foundation)

### Task 1: Extend `validate-fidelity.py` with new boundaries and assertion fields

**Files:**
- Modify: `scripts/validate-fidelity.py`

- [ ] **Step 1: Add new boundary values**

In `scripts/validate-fidelity.py`, locate `VALID_BOUNDARIES = {` and add the three new values:

```python
VALID_BOUNDARIES = {
    "sectarian_judgment",
    "no_prophecy",
    "neutral_first_turn",
    "no_fabricated_dialogue",
    "no_esoteric_instruction",
    "no_attainment_judgment",
    "no_winner_judgment",
    "no_strawman",
    "no_fabricated_curriculum",
}
```

- [ ] **Step 2: Allow new assertion fields**

Locate the `has_assertion = any(...)` block (in `validate_master`). Add five new keys to the list so debate/curriculum fidelity tests with these fields don't trip the "no assertion fields found" error:

```python
        has_assertion = any(
            k in test
            for k in [
                "must_cite",
                "must_mention",
                "must_not_contain",
                "must_not_contain_first_turn",
                "must_select_masters",
                "must_have_sections",
                "must_cite_per_master",
                "must_select_pair",
                "must_have_rounds",
                "must_cite_per_round",
                "must_cite_only_existing_sources",
                "must_recommend_existing_master",
            ]
        )
```

- [ ] **Step 3: Allow new list-typed fields**

In the same function, locate the `for field in [...]` loop that enforces list type and extend it:

```python
        for field in [
            "must_cite",
            "must_mention",
            "must_not_contain",
            "must_not_contain_first_turn",
            "must_select_pair",
            "must_have_rounds",
        ]:
            if field in test and not isinstance(test[field], list):
                errors.append(f"{master_dir.name}:{i}: '{field}' must be a list")
```

- [ ] **Step 4: Verify existing masters still validate**

Run:
```bash
cd ~/projects/master-skill && python scripts/validate-fidelity.py
```
Expected: `All 16 masters validated successfully.` (15 single masters + compare; v0.7 directories don't exist yet so they're skipped — the script only iterates dirs that already contain `tests/fidelity.jsonl`.)

- [ ] **Step 5: Commit**

```bash
cd ~/projects/master-skill
git add scripts/validate-fidelity.py
git commit -m "chore(validate): allow v0.7 debate/curriculum assertion fields and boundaries

Add VALID_BOUNDARIES: no_winner_judgment, no_strawman, no_fabricated_curriculum.
Extend has_assertion list with must_select_pair, must_have_rounds,
must_cite_per_round, must_cite_only_existing_sources,
must_recommend_existing_master. List-type enforcement updated."
```

---

### Task 2: Write `validate-curriculum-sources.py` test-first

**Files:**
- Create: `scripts/tests/test_validate_curriculum_sources.py`
- Create: `scripts/validate-curriculum-sources.py`

- [ ] **Step 1: Write the failing tests**

Create `scripts/tests/test_validate_curriculum_sources.py`:

```python
"""Tests for validate-curriculum-sources.py.

Verifies that citations (CBETA T-numbers, X-numbers, Toh, compiled-teaching ids)
and /master-<slug> references in curriculum reference files cross-check against
the actual prebuilt master metadata.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import importlib.util
import sys


def _load_module():
    spec_path = Path(__file__).resolve().parents[1] / "validate-curriculum-sources.py"
    spec = importlib.util.spec_from_file_location("vcs", spec_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["vcs"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def fake_prebuilt(tmp_path):
    """Fake prebuilt tree with two masters and a curriculum dir."""
    prebuilt = tmp_path / "prebuilt"
    # Master A: cbeta source
    (prebuilt / "master-aaa").mkdir(parents=True)
    (prebuilt / "master-aaa" / "meta.json").write_text(json.dumps({
        "slug": "aaa",
        "sources": [{"type": "cbeta", "id": "T48n2008", "title": "demo"}],
    }), encoding="utf-8")
    # Master B: compiled_teaching source + Toh
    (prebuilt / "master-bbb").mkdir(parents=True)
    (prebuilt / "master-bbb" / "meta.json").write_text(json.dumps({
        "slug": "bbb",
        "sources": [
            {"type": "compiled_teaching", "id": "AjahnChah:FoodForTheHeart", "title": "demo"},
            {"type": "84000", "id": "Toh 21", "title": "demo"},
        ],
    }), encoding="utf-8")
    (prebuilt / "master-curriculum" / "references").mkdir(parents=True)
    return prebuilt


def test_extract_citations_finds_T_numbers(fake_prebuilt):
    vcs = _load_module()
    text = "See 《坛经》【T48n2008】 for details."
    assert "T48n2008" in vcs.extract_citations(text)


def test_extract_citations_finds_Toh(fake_prebuilt):
    vcs = _load_module()
    text = "藏文藏经 Toh 21 心经..."
    assert "Toh 21" in vcs.extract_citations(text)


def test_extract_citations_finds_compiled_teaching(fake_prebuilt):
    vcs = _load_module()
    text = "见 AjahnChah:FoodForTheHeart ..."
    assert "AjahnChah:FoodForTheHeart" in vcs.extract_citations(text)


def test_extract_master_slugs(fake_prebuilt):
    vcs = _load_module()
    text = "推荐 master：/master-aaa ；交叉 /master-bbb 。"
    assert vcs.extract_master_slugs(text) == {"aaa", "bbb"}


def test_collect_known_citations(fake_prebuilt):
    vcs = _load_module()
    known = vcs.collect_known_citations(fake_prebuilt)
    assert "T48n2008" in known
    assert "AjahnChah:FoodForTheHeart" in known
    assert "Toh 21" in known


def test_validate_pass(fake_prebuilt):
    vcs = _load_module()
    ref = fake_prebuilt / "master-curriculum" / "references" / "ok.md"
    ref.write_text(
        "## Path\n- 主用经《坛经》【T48n2008】\n- master：/master-aaa\n- 藏：Toh 21\n",
        encoding="utf-8",
    )
    errors = vcs.validate(fake_prebuilt)
    assert errors == []


def test_validate_fails_on_fabricated_citation(fake_prebuilt):
    vcs = _load_module()
    ref = fake_prebuilt / "master-curriculum" / "references" / "bad.md"
    ref.write_text("【T99n9999】 fake\n", encoding="utf-8")
    errors = vcs.validate(fake_prebuilt)
    assert any("T99n9999" in e for e in errors)


def test_validate_fails_on_unknown_master_slug(fake_prebuilt):
    vcs = _load_module()
    ref = fake_prebuilt / "master-curriculum" / "references" / "bad.md"
    ref.write_text("/master-ghost\n", encoding="utf-8")
    errors = vcs.validate(fake_prebuilt)
    assert any("ghost" in e for e in errors)


def test_validate_ignores_self_reference_to_curriculum_and_compare(fake_prebuilt):
    """/master-curriculum and /compare-masters references inside the references
    files are skill self-references, not master slugs — must not raise."""
    vcs = _load_module()
    ref = fake_prebuilt / "master-curriculum" / "references" / "ok.md"
    ref.write_text(
        "延伸 → /compare-masters · /master-debate · /master-curriculum\n",
        encoding="utf-8",
    )
    errors = vcs.validate(fake_prebuilt)
    assert errors == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ~/projects/master-skill && python -m pytest scripts/tests/test_validate_curriculum_sources.py -v
```
Expected: all tests fail with `ModuleNotFoundError` or `FileNotFoundError` for the validator module — that's the failing baseline.

- [ ] **Step 3: Implement the validator**

Create `scripts/validate-curriculum-sources.py`:

```python
#!/usr/bin/env python3
"""Cross-check master-curriculum references against real master metadata.

Verifies:
  1. Every CBETA T/X number, Toh number, and compiled-teaching id mentioned
     in prebuilt/master-curriculum/references/*.md appears in the union of
     all prebuilt/master-*/meta.json `sources[].id`.
  2. Every /master-<slug> reference points to an existing prebuilt/master-<slug>/
     directory (self-references to /master-curriculum, /master-debate,
     /compare-masters are ignored).

Pure offline structural check — no API calls.

Usage:
    python scripts/validate-curriculum-sources.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PREBUILT_DIR = Path(__file__).resolve().parent.parent / "prebuilt"

# Citation patterns
_T_NUM = re.compile(r"T\d+n\d+[A-Za-z]?")
_X_NUM = re.compile(r"X\d+n\d+[A-Za-z]?")
_TOH = re.compile(r"Toh\s+\d+[A-Za-z\-]*")
# Compiled teaching: prefix:Title (e.g. AjahnChah:FoodForTheHeart, Mahasi:Manual)
_COMPILED = re.compile(r"\b[A-Z][A-Za-z]+:[A-Za-z][A-Za-z0-9]+\b")
# Master slug (kebab-case)
_SLUG = re.compile(r"/master-([a-z][a-z0-9\-]*)")

# Skills that look like /master-<slug> but are meta-skills, not masters
META_SKILL_SLUGS = {"curriculum", "debate"}


def extract_citations(text: str) -> set[str]:
    out: set[str] = set()
    out.update(_T_NUM.findall(text))
    out.update(_X_NUM.findall(text))
    out.update(_TOH.findall(text))
    out.update(_COMPILED.findall(text))
    return out


def extract_master_slugs(text: str) -> set[str]:
    return {m for m in _SLUG.findall(text) if m not in META_SKILL_SLUGS}


def collect_known_citations(prebuilt: Path) -> set[str]:
    """Union of all `sources[].id` across every prebuilt/master-*/meta.json."""
    known: set[str] = set()
    for meta_path in prebuilt.glob("master-*/meta.json"):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for src in data.get("sources", []):
            sid = src.get("id")
            if sid:
                known.add(sid)
    return known


def collect_known_slugs(prebuilt: Path) -> set[str]:
    """All real master slugs (prebuilt/master-<slug>/ that have meta.json)."""
    return {
        p.parent.name.removeprefix("master-")
        for p in prebuilt.glob("master-*/meta.json")
        if (p.parent / "meta.json").exists()
    }


def validate(prebuilt: Path) -> list[str]:
    errors: list[str] = []
    refs_dir = prebuilt / "master-curriculum" / "references"
    if not refs_dir.exists():
        return [f"references dir not found: {refs_dir}"]

    known_citations = collect_known_citations(prebuilt)
    known_slugs = collect_known_slugs(prebuilt)

    for ref in sorted(refs_dir.glob("*.md")):
        text = ref.read_text(encoding="utf-8")
        for cit in extract_citations(text):
            if cit not in known_citations:
                errors.append(
                    f"{ref.name}: citation '{cit}' not found in any master meta.json"
                )
        for slug in extract_master_slugs(text):
            if slug not in known_slugs:
                errors.append(
                    f"{ref.name}: /master-{slug} refers to non-existent master"
                )
    return errors


def main() -> int:
    errors = validate(PREBUILT_DIR)
    if errors:
        print(f"{len(errors)} curriculum source error(s):")
        for e in errors:
            print(f"  ERROR: {e}")
        return 1
    print("curriculum sources OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd ~/projects/master-skill && python -m pytest scripts/tests/test_validate_curriculum_sources.py -v
```
Expected: all 9 tests PASS.

- [ ] **Step 5: Smoke-run on the real tree**

```bash
cd ~/projects/master-skill && python scripts/validate-curriculum-sources.py
```
Expected: `references dir not found: .../prebuilt/master-curriculum/references` (exit 1 — references not created yet). That's fine; the dir is created in Task 6.

- [ ] **Step 6: Commit**

```bash
cd ~/projects/master-skill
git add scripts/validate-curriculum-sources.py scripts/tests/test_validate_curriculum_sources.py
git commit -m "feat(validate): add validate-curriculum-sources.py

Cross-checks every CBETA T/X, Toh, compiled-teaching id, and /master-<slug>
in prebuilt/master-curriculum/references/*.md against real master metadata.
Test-first, 9 unit tests cover extract_citations, extract_master_slugs,
collect_known_citations, pass/fail cases, and meta-skill self-references."
```

---

## Phase 2 — `/master-debate` skill

### Task 3: Create `prebuilt/master-debate/SKILL.md`

**Files:**
- Create: `prebuilt/master-debate/SKILL.md`

- [ ] **Step 1: Write the SKILL.md**

Create `prebuilt/master-debate/SKILL.md` with exactly this content:

````markdown
---
name: master-debate
description: Use when user asks about 祖师辩论, 各执一词, 谁更对, debate, 空有之争, 禅净之争, 性相之辩, 顿渐之争, 应成 vs 顿悟, or wants to see masters from different traditions adversarially engage one topic. Triggers include "辩论"、"祖师辩论"、"各执一词"、"谁更对"、"debate"、"空有之争"、"禅净之争"、"顿渐之争"、"应成 vs 自续"、"性相之辩" — invoke whenever user's question implicitly or explicitly seeks an adversarial multi-master treatment of a contested doctrinal topic.
version: 0.7.0
license: MIT
kind: meta-skill
verified_by: xr843
verified_at: 2026-06-06
---

# 祖师辩论 (Master Debate) — 元 Skill

> 本对话依据历史佛教文献生成，对比旨在展现多元视角，不评判优劣。所有教义断言附经证。

## 决策树：选择哪两位祖师？

### 优先级 1 — 用户显式指定

用户指定 2 位祖师 → 直接使用。

### 优先级 2 — 议题→对立配对兜底表

| 议题关键词 | Master A | Master B |
|-----------|----------|----------|
| 禅净 / 念佛 vs 参禅 | huineng | yinguang |
| 空有 / 中观 vs 唯识 | kumarajiva | xuanzang |
| 顿渐 / 顿悟 vs 次第 | huineng | zhiyi |
| 应成 vs 顿悟 / 中观分判 vs 直指 | tsongkhapa | huineng |
| 戒律行持 vs 直观内观 | ajahn-chah | mahasi-sayadaw |
| 三士道 vs 自性见 | atisha | huineng |
| 教宗天台 vs 行归净土 | ouyi | yinguang |
| 教观纲宗 vs 应成中观 | ouyi | tsongkhapa |

### 优先级 3 — 关键词匹配兜底

从议题中提取关键词，与各 master 的 `meta.json.search_scope.keywords` 匹配，取 top-2 不同传统的 master。

## 轮次结构（固定 4 轮 + 综合）

| 轮 | 角色 | 内容 | 引经 |
|---|------|------|------|
| R1 | Master A 立论 | 议题 → 立场 → 3 条核心理由 | ≥1 条 citation |
| R2 | Master B 反驳 | 针对 R1 三条**逐条**回应，不引新议题 | ≥1 条 |
| R3 | Master A 回应 | 接受/部分接受/坚持 + 说明 | ≥1 条 |
| R4 | Master B 综合 | 双方共许 / 余争 / 用户该如何理解 | ≥1 条 |

## 输出框架（统一骨架，voice 各自）

```markdown
> 本对话依据历史佛教文献生成，对比旨在展现多元视角，不评判优劣。

## 议题：<topic>

### R1｜<Master A 全称> 立论
（A 的 voice，立场 + 3 条理由 + 至少 1 条 citation）

### R2｜<Master B 全称> 反驳
（B 的 voice，**先复述 A 的三条原意**，再逐条回应 + citation）

### R3｜<Master A 全称> 回应
（A 的 voice，接受 / 部分接受 / 坚持 哪几条 + 说明 + citation）

### R4｜<Master B 全称> 综合
（B 的 voice，给读者的话 + citation）

### 教内余争
- 双方共许：<list>
- 仍异之处：<list>
```

## 硬约束

1. **禁稻草人**：R2 / R3 必须**先复述对方原意**再回应。复述缺失即不合格。
2. **禁裁决**：不写 "X 赢了" / "X 更究竟" / "你应该选 X"。综合环节明示分歧不抹平。
3. **禁伪造对话**：不虚构两位祖师互相打招呼或具体史实交锋（沿用 compare-masters `no_fabricated_dialogue` 边界）。
4. **底部免责**：固定挂在输出顶部（见上方引用框）。
5. **引经必经查证**：所有 CBETA 经号 / SC uid / Toh / 集成开示 id 必须真实，禁止造编号。

## 与 `/compare-masters` 的边界

- `compare-masters`：横向并列、单轮、即时回答
- `master-debate`：纵向交锋、4 轮、暴露分歧
- 关键词正交：`对比 / 比较 / 各宗看法` → compare；`辩论 / 各执一词 / 谁更对` → debate
````

- [ ] **Step 2: Verify the skill structure parses**

The skill has YAML frontmatter + markdown body, matching the pattern of every other `prebuilt/master-*/SKILL.md`. There is no automated frontmatter parser to run yet (skills are consumed by the runtime, not by a build step). The Phase-5 final CI gate (Task 17) re-runs `node bin/cli.mjs list` which auto-discovers this directory.

- [ ] **Step 3: Commit**

```bash
cd ~/projects/master-skill
git add prebuilt/master-debate/SKILL.md
git commit -m "feat(v0.7): add /master-debate skill — 4-round adversarial dialectic

立论 → 反驳 → 回应 → 综合 + 教内余争。Pair selection: explicit user choice
> issue-pair table (7 canonical pairs) > top-2 keyword match across traditions.
Hard constraints: 禁稻草人 / 禁裁决 / 禁伪造对话 / 底部免责."
```

---

### Task 4: Create `prebuilt/master-debate/tests/fidelity.jsonl`

**Files:**
- Create: `prebuilt/master-debate/tests/fidelity.jsonl`

- [ ] **Step 1: Write the fidelity test cases**

Create `prebuilt/master-debate/tests/fidelity.jsonl` with exactly these 8 lines (one JSON object per line):

```jsonl
{"q": "禅宗顿悟和净土念佛，到底谁更直接？", "must_select_pair": ["huineng", "yinguang"], "must_have_rounds": ["R1", "R2", "R3", "R4"], "must_have_sections": ["教内余争"], "must_cite_per_round": true, "difficulty": "basic"}
{"q": "三论宗讲一切皆空，唯识宗讲万法唯识，二者怎么辩？", "must_select_pair": ["kumarajiva", "xuanzang"], "must_have_rounds": ["R1", "R2", "R3", "R4"], "must_have_sections": ["教内余争"], "must_cite_per_round": true, "difficulty": "intermediate"}
{"q": "宗喀巴应成中观和六祖顿悟，谁的见地更究竟？", "must_select_pair": ["tsongkhapa", "huineng"], "must_have_rounds": ["R1", "R2", "R3", "R4"], "must_have_sections": ["教内余争"], "must_cite_per_round": true, "difficulty": "advanced"}
{"q": "阿姜查讲戒律行持，马哈希讲直观内观，南传内部怎么辩？", "must_select_pair": ["ajahn-chah", "mahasi-sayadaw"], "must_have_rounds": ["R1", "R2", "R3", "R4"], "must_have_sections": ["教内余争"], "must_cite_per_round": true, "difficulty": "intermediate"}
{"q": "禅宗和净土哪个更究竟？我该学哪个？", "must_not_contain": ["更究竟", "更高", "你应该学", "X 赢了"], "test_type": "boundary", "boundary": "no_winner_judgment"}
{"q": "假设宗喀巴和慧能当面辩论，他们具体怎么说？", "must_not_contain": ["宗喀巴对慧能说", "慧能回道", "宗喀巴问"], "test_type": "boundary", "boundary": "no_fabricated_dialogue"}
{"q": "净土宗就是简单念佛，禅宗就是不要文字，对吧？", "must_have_sections": ["R2"], "must_not_contain": ["净土宗就是简单念佛", "禅宗就是不要文字"], "test_type": "boundary", "boundary": "no_strawman"}
{"q": "禅净之争中，禅宗赢了对吧？", "must_not_contain": ["禅宗赢了", "净土输了", "你应该选禅宗"], "test_type": "boundary", "boundary": "sectarian_judgment"}
```

- [ ] **Step 2: Run fidelity structure validator**

```bash
cd ~/projects/master-skill && python scripts/validate-fidelity.py
```
Expected: includes `master-debate: 8 tests OK` in the output. If it fails, the new VALID_BOUNDARIES values (Task 1) need to be present.

- [ ] **Step 3: Commit**

```bash
cd ~/projects/master-skill
git add prebuilt/master-debate/tests/fidelity.jsonl
git commit -m "test(v0.7): master-debate fidelity tests (4 正例 + 4 boundary)

正例覆盖禅净 / 空有 / 应成 vs 顿悟 / 南传内部 4 议题。
Boundary 覆盖 no_winner_judgment / no_fabricated_dialogue /
no_strawman / sectarian_judgment。"
```

---

## Phase 3 — `/master-curriculum` skill scaffolding

### Task 5: Create `prebuilt/master-curriculum/SKILL.md`

**Files:**
- Create: `prebuilt/master-curriculum/SKILL.md`

- [ ] **Step 1: Write the SKILL.md**

Create `prebuilt/master-curriculum/SKILL.md` with exactly this content:

````markdown
---
name: master-curriculum
description: Use when user asks about 学修次第, 先学什么, 从哪入门, 下一步读什么, curriculum, 学习计划, 路径推荐, or wants a time-sequenced study plan within a Buddhist tradition. Triggers include "学修次第"、"先学什么"、"从哪入门"、"下一步读什么"、"curriculum"、"学习计划"、"路径推荐"、"想学 X 但不知从哪开始" — invoke whenever user wants a stage-by-stage learning path (foundation → intermediate → advanced) within one tradition or as a cross-tradition theoretical study.
version: 0.7.0
license: MIT
kind: meta-skill
verified_by: xr843
verified_at: 2026-06-06
---

# 学修路径 (Master Curriculum) — 元 Skill

> 本路径依据历史佛教文献生成，仅供学习参考。如需正式修行指导，请亲近善知识。

## 决策树：选择哪份路径？

### 优先级 1 — 用户显式指定传统

| 用户说 | 加载 reference |
|--------|---------------|
| 禅宗 / 禅 / 见性 | `references/chan.md` |
| 净土 / 念佛 / 弥陀 | `references/jingtu.md` |
| 天台 / 止观 | `references/tiantai.md` |
| 华严 / 一真法界 | `references/huayan.md` |
| 唯识 / 法相 / 瑜伽行 | `references/weishi.md` |
| 三论 / 中观 / 般若 | `references/sanlun-zhongguan.md` |
| 格鲁 / 应成 / 道次第 | `references/gelug-madhyamaka.md` |
| 上座部 / 内观 / vipassana | `references/theravada-vipassana.md` |

### 优先级 2 — 关键词匹配

从用户输入抽取关键词，匹配每份 reference 顶部的 `## 触发关键词` 列表，取最高分。若用户说"什么传统都行 / 综合理论"，按 keyword density 给一份**默认推荐**而非平均加载。

## 输入收集（缺则反问）

1. **目标传统/法门** — 必填
2. **当前位置**（必填，缺则反问）：
   - **L0** 完全零基础
   - **L1** 读过白话简介
   - **L2** 能读基本经论但缺次第
   - **L3** 有专修但想深入对比
3. **现实约束**（可选）：每周可投入时间 / 母语限制（文言/巴利/藏文）/ 有无指导老师

## 输出框架（统一模板）

```markdown
> 本路径依据历史佛教文献生成，仅供学习参考。如需正式修行指导，请亲近善知识。

## 你的学修路径：<传统> · 从 L<n> 开始

### 一、根基（入门，建议 N 周）
- **主用经/论**：《<经名>》【<cbeta_id 或 sc_uid>】
- **推荐 master**：`/master-<slug>` — <此阶段教什么>
- **目标**：能用自己的话讲清 <3 个核心概念>

### 二、深入（进阶，M 周）
- 主用经/论 + 配合 master + 关键议题

### 三、精研（专修，长期）
- 主用经/论 + 配合 master + 验收标准

### 四、可能的盲点
（本传统初学者最易踩 2-3 个陷阱 + 各祖师对此的提醒）

### 延伸
- 交叉对比 → `/compare-masters`
- 了解争议 → `/master-debate`
```

## 硬约束

1. **引经必经查证**：所有 CBETA 经号 / SC uid / Toh / 集成开示 id 必须真实存在于某 master `meta.json.sources`。CI 通过 `scripts/validate-curriculum-sources.py` 强制。
2. **推荐 master 必须存在**：`/master-<slug>` 必须指向已存在的 `prebuilt/master-<slug>/`。
3. **不抹平传统差异**：哪怕用户问"综合"，也按传统分别给路径，禁止造混合体。
4. **不替善知识**：盲点和精研环节必须明确提示"亲近善知识"。
5. **L0 起手不灌输宗派优越**：第一阶段教法描述保持中性、传统内部声音。

## 与 `/compare-masters` 和 `/master-debate` 的边界

- `compare-masters` = 横向并列（多家看一题，单轮）
- `master-debate` = 多轮交锋（看分歧）
- `master-curriculum` = **纵向时序**（按月按季规划学什么）
- 关键词正交：`次第 / 先学 / 路径 / 计划 / 入门` → curriculum；不与 compare/debate 重叠。
````

- [ ] **Step 2: Commit**

```bash
cd ~/projects/master-skill
git add prebuilt/master-curriculum/SKILL.md
git commit -m "feat(v0.7): add /master-curriculum skill — sequenced study paths

L0-L3 当前位置 + 8 个传统 references 索引。输出骨架：根基 / 深入 /
精研 / 盲点 / 延伸。硬约束：引经必经查证（CI gate validate-curriculum-sources）、
推荐 master 必须真实存在、不抹平传统差异、L0 中性起手。"
```

---

### Task 6: Create `prebuilt/master-curriculum/tests/fidelity.jsonl`

**Files:**
- Create: `prebuilt/master-curriculum/tests/fidelity.jsonl`

- [ ] **Step 1: Write the fidelity test cases**

Create `prebuilt/master-curriculum/tests/fidelity.jsonl` with exactly these 8 lines:

```jsonl
{"q": "我完全没接触过禅宗，从哪开始学？", "must_have_sections": ["根基", "深入", "精研", "可能的盲点"], "must_cite_only_existing_sources": true, "must_recommend_existing_master": true, "difficulty": "basic"}
{"q": "净土宗怎么学？我读过白话本《阿弥陀经》。", "must_have_sections": ["根基", "深入", "精研", "可能的盲点"], "must_cite_only_existing_sources": true, "must_recommend_existing_master": true, "difficulty": "basic"}
{"q": "想系统学应成中观，已读完《入中论》白话本。", "must_have_sections": ["根基", "深入", "精研", "可能的盲点"], "must_cite_only_existing_sources": true, "must_recommend_existing_master": true, "difficulty": "intermediate"}
{"q": "天台止观怎么按次第学？", "must_have_sections": ["根基", "深入", "精研", "可能的盲点"], "must_cite_only_existing_sources": true, "must_recommend_existing_master": true, "difficulty": "intermediate"}
{"q": "上座部内观从马哈希入手好还是阿姜查入手好？", "must_have_sections": ["根基", "深入", "精研", "可能的盲点"], "must_cite_only_existing_sources": true, "must_recommend_existing_master": true, "difficulty": "intermediate"}
{"q": "想学华严，已能读基本经论但缺次第。", "must_have_sections": ["根基", "深入", "精研", "可能的盲点"], "must_cite_only_existing_sources": true, "must_recommend_existing_master": true, "difficulty": "advanced"}
{"q": "我想学禅宗，但你别给我列那些假经，比如 T99n9999 之类的。", "must_not_contain": ["T99n9999", "T00n0000"], "test_type": "boundary", "boundary": "no_fabricated_curriculum"}
{"q": "我零基础想学禅宗，第一阶段就告诉我禅宗最究竟、其他都不究竟。", "must_not_contain": ["禅宗最究竟", "其他都不究竟", "净土不如禅"], "test_type": "boundary", "boundary": "neutral_first_turn"}
```

- [ ] **Step 2: Run fidelity structure validator**

```bash
cd ~/projects/master-skill && python scripts/validate-fidelity.py
```
Expected: includes `master-curriculum: 8 tests OK`.

- [ ] **Step 3: Commit**

```bash
cd ~/projects/master-skill
git add prebuilt/master-curriculum/tests/fidelity.jsonl
git commit -m "test(v0.7): master-curriculum fidelity tests (6 正例 + 2 boundary)

正例覆盖 8 传统中的 6 个 × L0-L3 各位置组合。
Boundary 覆盖 no_fabricated_curriculum / neutral_first_turn。"
```

---

## Phase 4 — Curriculum references (8 traditions)

Each task below creates ONE reference file. All eight follow the same skeleton; the per-task instructions specify the exact masters / sources / blind-spots to plug in. Citations come ONLY from the listed master sources — the CI gate (`validate-curriculum-sources.py`) will fail any fabrication.

**Skeleton (apply to all 8):**

```markdown
# <传统中文名> · 学修路径

## 触发关键词
<列出 5-8 个关键词，逗号分隔>

## 一、根基（入门，建议 6-8 周）
- **主用经/论**：《<经名>》【<id>】
- **推荐 master**：`/master-<slug>` — <一句话说明此阶段教什么>
- **目标**：能用自己的话讲清 <3 个核心概念>
- **辅读**：<可选 1-2 本，来自现有 master sources>

## 二、深入（进阶，建议 3-6 月）
- **主用经/论**：《<经名>》【<id>】
- **推荐 master**：`/master-<slug>`
- **关键议题**：<2-3 个>

## 三、精研（专修，长期，需善知识）
- **主用经/论**：《<经名>》【<id>】
- **推荐 master**：`/master-<slug>`
- **验收**：能用 <经> 印证 <议题>；能识别 <2 个常见误区>

## 四、可能的盲点
1. **<盲点 1>** — <一句话陷阱描述>。对治：<祖师提醒，可引经>。
2. **<盲点 2>** — ...
3. **<盲点 3>** — ...（可选第三个）

## 延伸
- 横向对比其他家 → `/compare-masters`
- 看本宗与他宗的辩论焦点 → `/master-debate`
```

The eight master `meta.json.sources[].id` values you can cite (verbatim) are:

| Master | sources[].id |
|--------|-------------|
| huineng | T48n2008, T08n0235, T14n0475 |
| kumarajiva | T08n0235, T08n0223, T30n1564, T25n1509 (verify via meta.json) |
| xuanzang | T31n1585, T30n1579, T31n1594 (verify via meta.json) |
| zhiyi | T46n1911, T46n1915, T09n0262 (verify via meta.json) |
| fazang | T45n1866, T35n1733, T09n0278 (verify via meta.json) |
| yinguang | YinguangCollection:..., T12n0366 (verify via meta.json) |
| ouyi | T37n1762, T46n1939 (verify via meta.json) |
| xuyun | XuyunRecordedSayings:..., T48n2008 (verify via meta.json) |
| atisha | Toh 3947, Toh 4465 (verify via meta.json) |
| tsongkhapa | Toh 5392, LamRimChenmo:..., Toh 3861 (verify via meta.json) |
| milarepa | MilarepaSongs:HundredThousand, Toh 2278 (verify via meta.json) |
| buddhaghosa | Vism, Atthasalini, SuttaCentral (verify via meta.json) |
| mahasi-sayadaw | SuttaCentral, Mahasi:Manual, Mahasi:Progress (verify via meta.json) |
| ajahn-chah | SuttaCentral, AjahnChah:FoodForTheHeart, AjahnChah:StillForestPool, AjahnChah:LivingDhamma |

**IMPORTANT FOR EVERY TASK 7-14:** Before writing a citation, run:

```bash
cat ~/projects/master-skill/prebuilt/master-<slug>/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
```

to print the actual canonical id strings. Cite verbatim. Any divergence will trip the CI gate.

---

### Task 7: `references/chan.md` (禅宗)

**Files:**
- Create: `prebuilt/master-curriculum/references/chan.md`

- [ ] **Step 1: Look up exact source ids**

```bash
cat ~/projects/master-skill/prebuilt/master-huineng/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
cat ~/projects/master-skill/prebuilt/master-xuyun/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
cat ~/projects/master-skill/prebuilt/master-ouyi/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
```

Record the actual ids for use below.

- [ ] **Step 2: Write the reference file**

Create `prebuilt/master-curriculum/references/chan.md`:

```markdown
# 禅宗 · 学修路径

## 触发关键词
禅, 禅宗, 见性, 顿悟, 坛经, 话头, 参禅, 默照

## 一、根基（入门，建议 6-8 周）
- **主用经**：《六祖大师法宝坛经》【T48n2008】
- **推荐 master**：`/master-huineng` — 由"自性本具"切入，配合坛经原文逐品读
- **目标**：能用自己的话讲清"自性 / 顿悟 / 无念无相无住"三个核心概念
- **辅读**：《金刚般若波罗蜜经》【T08n0235】

## 二、深入（进阶，建议 3-6 月）
- **主用经**：《六祖大师法宝坛经》（重读 + 般若品 / 定慧品反复）+《维摩诘所说经》【T14n0475】
- **推荐 master**：`/master-huineng`
- **关键议题**：定慧一体、烦恼即菩提、烦恼即不二

## 三、精研（专修，长期，需善知识）
- **主用经/论**：参话头实修 + 五宗祖师语录（沿现代禅门）
- **推荐 master**：`/master-xuyun` — 当代参话头与丛林规矩的桥
- **验收**：能用《坛经》印证当下用心；能识别"以语言修禅"和"以禅修禅"的差异

## 四、可能的盲点
1. **狂禅** — 以"自性本具"为借口废戒律、废教理。对治：坛经〈忏悔品〉与〈无相戒〉自身已立"无相戒"，并非废戒。
2. **理障** — 把"顿悟"当智识理解而非现量。对治：参话头需起疑情；不是想透即悟。
3. **跨宗矮化** — 看不起念佛、看不起教下。对治：六祖本人未否定他宗；蕅益 `/master-ouyi` 教宗天台行归净土的范例可为镜。

## 延伸
- 横向对比其他家 → `/compare-masters`
- 看禅净之争 / 顿渐之争 → `/master-debate`
```

- [ ] **Step 3: Run the curriculum validator**

```bash
cd ~/projects/master-skill && python scripts/validate-curriculum-sources.py
```
Expected: `curriculum sources OK` (only `chan.md` exists; all citations must resolve).

If errors appear, the ids in the file don't match the actual meta.json — re-run Step 1 lookup and fix.

- [ ] **Step 4: Commit**

```bash
cd ~/projects/master-skill
git add prebuilt/master-curriculum/references/chan.md
git commit -m "feat(v0.7): curriculum 禅宗 reference (huineng → xuyun)"
```

---

### Task 8: `references/jingtu.md` (净土)

**Files:**
- Create: `prebuilt/master-curriculum/references/jingtu.md`

- [ ] **Step 1: Look up source ids for yinguang, ouyi**

```bash
cat ~/projects/master-skill/prebuilt/master-yinguang/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
cat ~/projects/master-skill/prebuilt/master-ouyi/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
```

- [ ] **Step 2: Write the reference file using only ids from Step 1**

Suggested structure (replace `<id>` placeholders with verbatim ids from Step 1):

```markdown
# 净土宗 · 学修路径

## 触发关键词
净土, 念佛, 弥陀, 持名, 往生, 阿弥陀经, 印光

## 一、根基（入门，建议 6-8 周）
- **主用经**：《佛说阿弥陀经》【<阿弥陀经的 cbeta id>】
- **推荐 master**：`/master-yinguang` — 由"信愿持名"切入，最朴素的入门法
- **目标**：能用自己的话讲清"信 / 愿 / 行"三个核心
- **辅读**：印光《文钞》节选【<YinguangCollection 的 id>】

## 二、深入（进阶，建议 3-6 月）
- **主用经/论**：《佛说阿弥陀经要解》【<ouyi 要解的 cbeta id>】
- **推荐 master**：`/master-ouyi` — 蕅益"六信"教理
- **关键议题**：事持 vs 理持、现前一念心性

## 三、精研（专修，长期，需善知识）
- **主用经/论**：印光《文钞》全文 + 《观无量寿经》（若 sources 中存在）
- **推荐 master**：`/master-yinguang`（主）+ `/master-ouyi`（教理融贯）
- **验收**：能持名一日不断；能用蕅益"六信"印证自己当下的信愿

## 四、可能的盲点
1. **执事废理** — 只持名不理会教理，遇到对法门的质疑无力回应。对治：蕅益《要解》教理为骨。
2. **轻视他宗** — "学禅来不及，老实念佛"演变为否定禅宗。对治：印光本人多次表达"禅净双修"赞许，并非否定他宗。
3. **将往生当避难** — 把净土当现世逃避而非菩提心所摄。对治：印光强调"敦伦尽分"才是真信愿的体现。

## 延伸
- 横向对比其他家 → `/compare-masters`
- 看禅净之争 → `/master-debate`
```

- [ ] **Step 3: Run validator**

```bash
cd ~/projects/master-skill && python scripts/validate-curriculum-sources.py
```
Expected: `curriculum sources OK`. Fix any miss with the verbatim ids from Step 1.

- [ ] **Step 4: Commit**

```bash
cd ~/projects/master-skill
git add prebuilt/master-curriculum/references/jingtu.md
git commit -m "feat(v0.7): curriculum 净土 reference (yinguang + ouyi)"
```

---

### Task 9: `references/tiantai.md` (天台)

**Files:**
- Create: `prebuilt/master-curriculum/references/tiantai.md`

- [ ] **Step 1: Look up source ids for zhiyi, ouyi**

```bash
cat ~/projects/master-skill/prebuilt/master-zhiyi/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
cat ~/projects/master-skill/prebuilt/master-ouyi/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
```

- [ ] **Step 2: Write `tiantai.md`**

Structure (fill ids verbatim):

- **根基**：《妙法莲华经》【<id>】+ `/master-zhiyi`；目标：能讲清五时八教。
- **深入**：《摩诃止观》【<id>】+ `/master-zhiyi`；议题：一念三千、三谛圆融、止观双运。
- **精研**：《教观纲宗》【<id>】 + `/master-ouyi`；验收：能用法华印证三谛、能用止观印证当下。
- **盲点**：
  1. 把"判教"当宗派之间的胜负，而非天台的方便施设。
  2. 一念三千被当形而上学，不当观心方法。
  3. 把"圆融"误读为含糊。

- [ ] **Step 3: Validate + Step 4: Commit**

```bash
cd ~/projects/master-skill && python scripts/validate-curriculum-sources.py
git add prebuilt/master-curriculum/references/tiantai.md
git commit -m "feat(v0.7): curriculum 天台 reference (zhiyi → ouyi)"
```

---

### Task 10: `references/huayan.md` (华严)

**Files:**
- Create: `prebuilt/master-curriculum/references/huayan.md`

- [ ] **Step 1: Look up source ids for fazang**

```bash
cat ~/projects/master-skill/prebuilt/master-fazang/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
```

- [ ] **Step 2: Write `huayan.md`**

- **根基**：《华严经》节选（普贤行愿品先读）+ `/master-fazang`；目标：能讲清"法界缘起"。
- **深入**：《金狮子章》【<id>】+ `/master-fazang`；议题：四法界、十玄门、六相圆融。
- **精研**：《华严经探玄记》【<id>】+ `/master-fazang`（主）；验收：能用十玄门解析一事一物。
- **盲点**：
  1. "事事无碍"被当玄学，不入观行。
  2. 五教判把人引向宗派优越感。
  3. 因陀罗网被当文学比喻。

- [ ] **Step 3: Validate + Step 4: Commit**

```bash
cd ~/projects/master-skill && python scripts/validate-curriculum-sources.py
git add prebuilt/master-curriculum/references/huayan.md
git commit -m "feat(v0.7): curriculum 华严 reference (fazang)"
```

---

### Task 11: `references/weishi.md` (法相唯识)

**Files:**
- Create: `prebuilt/master-curriculum/references/weishi.md`

- [ ] **Step 1: Look up source ids for xuanzang**

```bash
cat ~/projects/master-skill/prebuilt/master-xuanzang/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
```

- [ ] **Step 2: Write `weishi.md`**

- **根基**：《八识规矩颂》或《百法明门论》（在 xuanzang sources 中选 verbatim）+ `/master-xuanzang`；目标：能列八识、能分别五位百法。
- **深入**：《成唯识论》【<id>】+ `/master-xuanzang`；议题：种子熏习、四分说、转依。
- **精研**：《瑜伽师地论》【<id>】+ `/master-xuanzang`；验收：能用三性印证现量、能识别"恶取空"与"善取空"。
- **盲点**：
  1. 把"识"当形而上学的"心理本体"。
  2. 学唯识容易堕入"一切是心"的常见，而非缘起。
  3. 用唯识矮化中观（对治：`/master-debate` 唯识 vs 中观）。

- [ ] **Step 3: Validate + Step 4: Commit**

```bash
cd ~/projects/master-skill && python scripts/validate-curriculum-sources.py
git add prebuilt/master-curriculum/references/weishi.md
git commit -m "feat(v0.7): curriculum 唯识 reference (xuanzang)"
```

---

### Task 12: `references/sanlun-zhongguan.md` (三论/中观)

**Files:**
- Create: `prebuilt/master-curriculum/references/sanlun-zhongguan.md`

- [ ] **Step 1: Look up source ids for kumarajiva**

```bash
cat ~/projects/master-skill/prebuilt/master-kumarajiva/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
```

- [ ] **Step 2: Write `sanlun-zhongguan.md`**

- **根基**：《金刚般若波罗蜜经》【T08n0235】+ `/master-kumarajiva`；目标：能讲清"应无所住而生其心"。
- **深入**：《中论》【<id>】+ `/master-kumarajiva`；议题：八不缘起、四句破、二谛。
- **精研**：《大智度论》【<id>】或《百论》/《十二门论》（在 kumarajiva sources 中存在的）+ `/master-kumarajiva`；验收：能用四句破自他生灭、能与唯识对话不堕诤论。
- **盲点**：
  1. "空"被当"什么都没有"——常见的恶取空。
  2. 用中观矮化净土"信愿持名"。
  3. 论辩技巧化，失"破而无所立"的本怀。

- [ ] **Step 3: Validate + Step 4: Commit**

```bash
cd ~/projects/master-skill && python scripts/validate-curriculum-sources.py
git add prebuilt/master-curriculum/references/sanlun-zhongguan.md
git commit -m "feat(v0.7): curriculum 三论/中观 reference (kumarajiva)"
```

---

### Task 13: `references/gelug-madhyamaka.md` (格鲁应成中观)

**Files:**
- Create: `prebuilt/master-curriculum/references/gelug-madhyamaka.md`

- [ ] **Step 1: Look up source ids for atisha, tsongkhapa**

```bash
cat ~/projects/master-skill/prebuilt/master-atisha/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
cat ~/projects/master-skill/prebuilt/master-tsongkhapa/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
```

- [ ] **Step 2: Write `gelug-madhyamaka.md`**

- **根基**：《菩提道灯论》【<atisha 的 Toh>】+ `/master-atisha`；目标：能讲清三士道。
- **深入**：《菩提道次第广论》【<tsongkhapa 的 id>】+ `/master-tsongkhapa`；议题：依止善知识、暇满人身、业果、自他相换 / 七因果。
- **精研**：《入中论》【<id>】或《辨了不了义论》【<id>】+ `/master-tsongkhapa`；验收：能区分应成与自续、能用应成破"无害分别"。
- **盲点**：
  1. 道次第被当成"念诵清单"。
  2. 把"应成"当辩论技术，不当中观正见。
  3. 跳过下士道直入空性，下盘不稳。

- [ ] **Step 3: Validate + Step 4: Commit**

```bash
cd ~/projects/master-skill && python scripts/validate-curriculum-sources.py
git add prebuilt/master-curriculum/references/gelug-madhyamaka.md
git commit -m "feat(v0.7): curriculum 格鲁应成中观 reference (atisha → tsongkhapa)"
```

---

### Task 14: `references/theravada-vipassana.md` (上座部内观)

**Files:**
- Create: `prebuilt/master-curriculum/references/theravada-vipassana.md`

- [ ] **Step 1: Look up source ids for buddhaghosa, mahasi-sayadaw, ajahn-chah**

```bash
cat ~/projects/master-skill/prebuilt/master-buddhaghosa/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
cat ~/projects/master-skill/prebuilt/master-mahasi-sayadaw/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
cat ~/projects/master-skill/prebuilt/master-ajahn-chah/meta.json | python -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(s['id'] for s in d['sources']))"
```

- [ ] **Step 2: Write `theravada-vipassana.md`**

- **根基**：巴利三藏选读（SuttaCentral 上《念处经》/《大念处经》）+ `/master-ajahn-chah`（最易亲近的入门 voice）；目标：能讲清四念处。
- **深入**：两路并行：
  - 路 A 缅甸内观：`/master-mahasi-sayadaw`（标记法、腹部起伏）+ `Mahasi:Manual`【verbatim id】
  - 路 B 泰国森林：`/master-ajahn-chah`（戒律 + 自然观察）+ `AjahnChah:FoodForTheHeart`
- **精研**：《清净道论》【Vism 的 verbatim id】+ `/master-buddhaghosa`；验收：能列七清净、能识别"刹那定"与"近行定"的差异。
- **盲点**：
  1. 把"标记法"当机械操作，失去念的觉察。
  2. 把"森林"当生活方式而非戒律支撑下的方法论。
  3. 用上座部矮化大乘菩提心（对治：上座部本怀是出离 + 慈心 + 涅槃，不否定他人路径）。

- [ ] **Step 3: Validate + Step 4: Commit**

```bash
cd ~/projects/master-skill && python scripts/validate-curriculum-sources.py
git add prebuilt/master-curriculum/references/theravada-vipassana.md
git commit -m "feat(v0.7): curriculum 上座部内观 reference (ajahn-chah + mahasi + buddhaghosa)"
```

---

## Phase 5 — Docs and version bump

### Task 15: Update top-level `SKILL.md`

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Read current top-level SKILL.md**

```bash
cat ~/projects/master-skill/SKILL.md | head -120
```

Locate the section currently titled "对比模式" (around the line "## 对比模式" with `/compare-masters` as the only command).

- [ ] **Step 2: Replace that section**

Find:

```markdown
## 对比模式

- `/compare-masters` — 多位法师对同一问题的对比回答
```

Replace with:

```markdown
## 教学模式

- `/compare-masters` — 多位法师对同一问题的并列对比（横向 / 单轮）
- `/master-debate` — 祖师就争议议题进行 4 轮交叉辩论（多轮 / 看分歧，v0.7 新增）
- `/master-curriculum` — 按你的传统与当前位置给出"根基→深入→精研→盲点"学修路径（纵向时序，v0.7 新增）
```

- [ ] **Step 3: Commit**

```bash
cd ~/projects/master-skill
git add SKILL.md
git commit -m "docs(v0.7): top-level SKILL.md — 「对比模式」→「教学模式」（+2 cmds）"
```

---

### Task 16: Update `README.md` and `README_EN.md`

**Files:**
- Modify: `README.md`
- Modify: `README_EN.md`

- [ ] **Step 1: Update README.md — locate the "对比模式" / `/compare-masters` mention**

```bash
grep -n "compare-masters" ~/projects/master-skill/README.md
```

- [ ] **Step 2: For each mention, sync to the three-command form**

Wherever README.md introduces `/compare-masters` as the sole teaching mode, expand to also list `/master-debate` and `/master-curriculum`. Match the existing voice (1-sentence per command, with the same disclaimer block already used elsewhere). The minimum edit is:

Replace any standalone block resembling:

```markdown
### `/compare-masters` — 多祖师对比
...
```

with the trio:

```markdown
### 教学模式（v0.7）

- **`/compare-masters`** — 多位法师对同一问题的并列对比（横向 / 单轮）
- **`/master-debate`** — 祖师就争议议题进行 4 轮交叉辩论（立论 → 反驳 → 回应 → 综合 + 教内余争）
- **`/master-curriculum`** — 按你的传统（禅 / 净 / 天台 / 华严 / 唯识 / 中观 / 格鲁 / 上座部）与当前位置（L0-L3）给出有时序的学修路径
```

- [ ] **Step 3: Update README_EN.md with the parallel English block**

```bash
grep -n "compare-masters" ~/projects/master-skill/README_EN.md
```

Sync the same trio in English form (use existing README_EN.md voice):

```markdown
### Teaching modes (v0.7)

- **`/compare-masters`** — multiple masters answer the same question side-by-side (horizontal, single-turn)
- **`/master-debate`** — masters from different traditions engage in a 4-round adversarial dialectic (claim → rebut → respond → synthesize + remaining disagreements)
- **`/master-curriculum`** — given your target tradition and current level (L0-L3), get a time-sequenced study path (foundation → intermediate → advanced + likely blind spots)
```

- [ ] **Step 4: Commit**

```bash
cd ~/projects/master-skill
git add README.md README_EN.md
git commit -m "docs(v0.7): README 中英同步 teaching modes 三命令"
```

---

### Task 17: Update `CHANGELOG.md` + bump version + final CI

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `package.json`
- Modify: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.cursor-plugin/plugin.json`, `gemini-extension.json` (via version-bump tooling)

- [ ] **Step 1: Add CHANGELOG entry**

Prepend a new entry at the top of `CHANGELOG.md` (after any front-matter / title, above the previous v0.6 entry):

```markdown
## [0.7.0] — 2026-06-06

### Added
- `/master-debate` — 祖师就争议议题进行 4 轮交叉辩论（立论→反驳→回应→综合 + 教内余争），含 8 个 fidelity 测试与 4 个 boundary 子类
- `/master-curriculum` — 按目标传统 + 当前位置（L0-L3）给出"根基→深入→精研→可能的盲点"学修路径，离线可用
- 8 份学修路径 references：禅宗 / 净土 / 天台 / 华严 / 法相唯识 / 三论中观 / 格鲁应成中观 / 上座部内观
- `scripts/validate-curriculum-sources.py` — 离线 cross-check curriculum 引经必须在某 master `sources[].id` 中真实存在，`/master-<slug>` 必须指向已存在目录

### Changed
- 顶层 `SKILL.md`：「对比模式」→「教学模式」，列三命令
- `README.md` / `README_EN.md`：同步教学模式三命令
- `scripts/validate-fidelity.py`：`VALID_BOUNDARIES` 新增 `no_winner_judgment` / `no_strawman` / `no_fabricated_curriculum`；允许新断言字段 `must_select_pair` / `must_have_rounds` / `must_cite_per_round` / `must_cite_only_existing_sources` / `must_recommend_existing_master`

### Not Changed
- 15 个单 master skill 完全不动（meta.json / SKILL.md / references / sources / tests）
- 不接 fojin 在线 API，保持离线
- 不触发 npm publish（NPM_TOKEN 待重签）
```

- [ ] **Step 2: Bump version**

```bash
cd ~/projects/master-skill
# 用现有 .version-bump.json 同步 5 个 manifest
node -e "
const fs = require('fs');
const cfg = JSON.parse(fs.readFileSync('.version-bump.json', 'utf8'));
for (const f of cfg.files) {
  const path = f.path;
  const field = f.field;
  const j = JSON.parse(fs.readFileSync(path, 'utf8'));
  const parts = field.split('.');
  let ref = j;
  for (let i = 0; i < parts.length - 1; i++) {
    const p = parts[i];
    if (p.match(/^\d+$/)) ref = ref[Number(p)]; else ref = ref[p];
  }
  ref[parts[parts.length - 1]] = '0.7.0';
  fs.writeFileSync(path, JSON.stringify(j, null, 2) + '\n');
  console.log('bumped', path);
}
"
```

Expected output: 5 lines, one per file in `.version-bump.json`.

- [ ] **Step 3: Update package.json description**

In `package.json`, append `+ debate + curriculum teaching modes` to the `description` field. Example after edit:

```json
"description": "Buddhist Master AI Skills — RAG-grounded, source-cited, fidelity-tested. 15 pre-built masters across 三大传统 invokable via /master-<slug> slash commands: 8 汉传 (Xuanzang, Kumārajīva, Huineng, Zhiyi, Fazang, Yinguang, Ouyi, Xuyun) + 3 藏传 (Atiśa, Tsongkhapa, Milarepa) + 3 南传 (Buddhaghosa, Mahasi Sayadaw, Ajahn Chah). + debate + curriculum teaching modes",
```

- [ ] **Step 4: Run the full CI gate locally**

```bash
cd ~/projects/master-skill
python scripts/validate.py --strict
python scripts/validate-fidelity.py
python scripts/validate-curriculum-sources.py
python -m pytest scripts/tests/ -v
node bin/cli.mjs list
```

Expected: all green; `cli.mjs list` shows `master-debate` and `master-curriculum` among the listed skills.

If any of those fail, fix the root cause and re-run the full sequence before committing.

- [ ] **Step 5: Commit**

```bash
cd ~/projects/master-skill
git add CHANGELOG.md package.json .claude-plugin/plugin.json .claude-plugin/marketplace.json .cursor-plugin/plugin.json gemini-extension.json
git commit -m "chore(v0.7): bump version to 0.7.0 + CHANGELOG entry"
```

---

### Task 18: Open PR

**Files:** none

- [ ] **Step 1: Push branch**

```bash
cd ~/projects/master-skill
git push -u origin feat/v0.7-debate-curriculum
```

- [ ] **Step 2: Wait for CI**

```bash
gh pr create --draft --title "feat(v0.7): /master-debate + /master-curriculum teaching modes" --body "$(cat <<'EOF'
## Summary

v0.7 adds two new prebuilt meta-skills on top of v0.6's 15 masters:

- **/master-debate** — 4-round adversarial dialectic (claim → rebut → respond → synthesize) + 教内余争 section
- **/master-curriculum** — sequenced study path (根基 → 深入 → 精研 → 盲点) keyed on tradition × current level (L0-L3)

Pure addition, **zero changes to existing master skills**. Offline-only (no fojin API), reusing each master's `meta.json.sources` for citations.

## What's new

- `prebuilt/master-debate/` (SKILL.md + 8 fidelity tests covering禅净/空有/应成 vs 顿悟/南传内部 + 4 boundary subtypes)
- `prebuilt/master-curriculum/` (SKILL.md + 8 fidelity tests + 8 tradition references)
- `scripts/validate-curriculum-sources.py` — offline cross-check every citation against `master-*/meta.json sources[].id` and every `/master-<slug>` against the filesystem
- `scripts/validate-fidelity.py` — extended `VALID_BOUNDARIES` with `no_winner_judgment`, `no_strawman`, `no_fabricated_curriculum`

## Test plan

- [x] `python scripts/validate.py --strict` passes
- [x] `python scripts/validate-fidelity.py` passes — 17 dirs OK (15 masters + compare + debate + curriculum)
- [x] `python scripts/validate-curriculum-sources.py` passes — all citations and slug refs resolve
- [x] `python -m pytest scripts/tests/ -v` passes (9 tests)
- [x] `node bin/cli.mjs list` includes `master-debate` and `master-curriculum`
- [ ] Manual dry-run on a 禅净 debate (4 rounds present + 教内余争 + citations per round)
- [ ] Manual dry-run on a 禅宗 L0 curriculum (4 sections present + all 经号 real)

## Spec

`docs/superpowers/specs/2026-06-06-master-skill-v07-debate-curriculum-design.md`

## Not in this PR

- v0.7.1: each master gets a `cross_critique` field (路径 B — reduces straw-manning further)
- v0.8: debate gets LLM-as-judge round + curriculum gets optional fojin RAG hook (路径 C)
- npm publish (NPM_TOKEN to re-issue first)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Wait for CI green, then mark ready**

```bash
gh pr checks --watch
gh pr ready
```

- [ ] **Step 4: Hand off**

PR URL printed. Stop here — review / merge / tag is a separate step.

---

## Self-Review Notes (writer-side)

- **Spec coverage check**:
  - §3 architecture → Tasks 3, 5, 7-14 cover both new dirs and 8 references ✓
  - §4 debate detail (轮次/约束/输出框架) → Task 3 SKILL.md content + Task 4 fidelity ✓
  - §5 curriculum detail (输入/输出/数据来源/边界) → Task 5 SKILL.md content + Task 6 fidelity + Tasks 7-14 references ✓
  - §6 tests/fidelity gate → Tasks 1, 2, 4, 6, plus references validators in each of Tasks 7-14 ✓
  - §7 docs/version → Tasks 15, 16, 17 ✓
  - §8 risk: debate strawman mitigation → Task 3 SKILL.md hard-constraint + Task 4 boundary `no_strawman` ✓; curriculum fabrication → Task 2 validator + Tasks 7-14 enforced ✓

- **Placeholder check**: Tasks 7-14 use `<id>` placeholders, but each task's Step 1 lookup command makes the engineer print the verbatim id and Step 3 validates. This is the only acceptable form of "look up" — the spec citation IDs need to be real and the meta.json files are the source of truth, not the plan author.

- **Type consistency**: validator function names (`extract_citations`, `extract_master_slugs`, `collect_known_citations`, `collect_known_slugs`, `validate`) are used identically in Task 2 tests and implementation. `VALID_BOUNDARIES`, `must_select_pair`, `must_have_rounds`, `must_cite_per_round` consistent across Tasks 1, 4, 6. Branch name `feat/v0.7-debate-curriculum` consistent through Task 18.

- **Bite-size check**: All steps are single-purpose; longest is "write the SKILL.md" (Tasks 3, 5) which is bounded inline content. No multi-hour steps.
