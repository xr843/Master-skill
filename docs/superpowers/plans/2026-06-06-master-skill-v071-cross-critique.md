# Master-skill v0.7.1 — `cross_critique` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `cross_critique` field to 10 master `meta.json` files (16 doctrinal entries total covering debate's 8 canonical pairs bidirectionally), wire master-debate SKILL.md to inject these entries at R1-R4, add a new CI validator, ship as v0.7.1.

**Architecture:** Pure data + 1 SKILL.md edit + 1 new validator. Each master's meta.json gains an optional `cross_critique: [{target_master, position, citation}]` array. master-debate runtime looks up entries by pair (A, B) and injects them as context. New `scripts/validate-cross-critique.py` enforces structure + citation reality + 8-pair coverage. Zero changes to non-targeted masters' content.

**Tech Stack:** Python 3.12 validator, JSON edits, Markdown.

**Spec:** `docs/superpowers/specs/2026-06-06-master-skill-v071-cross-critique-design.md`

**Branch:** `feat/v0.7.1-cross-critique` (already on it).

---

## File Map

**Created:**
- `scripts/validate-cross-critique.py` — offline cross-check
- `scripts/tests/test_validate_cross_critique.py` — 8-10 TDD tests

**Modified (meta.json — add `cross_critique` field):**
- `prebuilt/master-huineng/meta.json` (4 entries)
- `prebuilt/master-yinguang/meta.json` (2 entries)
- `prebuilt/master-kumarajiva/meta.json` (1 entry)
- `prebuilt/master-xuanzang/meta.json` (1 entry)
- `prebuilt/master-zhiyi/meta.json` (1 entry)
- `prebuilt/master-tsongkhapa/meta.json` (2 entries)
- `prebuilt/master-ajahn-chah/meta.json` (1 entry)
- `prebuilt/master-mahasi-sayadaw/meta.json` (1 entry)
- `prebuilt/master-atisha/meta.json` (1 entry)
- `prebuilt/master-ouyi/meta.json` (2 entries)

**Modified (other):**
- `prebuilt/master-debate/SKILL.md` — add 「批判点注入」 section
- `CHANGELOG.md` — v0.7.1 entry
- `package.json` + `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` + `.cursor-plugin/plugin.json` + `gemini-extension.json` — version 0.7.0 → 0.7.1
- `README.md` / `README_EN.md` — small note about debate critique injection (optional one-liner)

---

## Phase 1 — Validator (TDD)

### Task 1: Write `scripts/validate-cross-critique.py` test-first

**Files:**
- Create: `scripts/tests/test_validate_cross_critique.py`
- Create: `scripts/validate-cross-critique.py`

- [ ] **Step 1: Write the failing tests**

Create `scripts/tests/test_validate_cross_critique.py`:

```python
"""Tests for validate-cross-critique.py."""
from __future__ import annotations

import json
from pathlib import Path

import importlib.util
import sys

import pytest


def _load_module():
    spec_path = Path(__file__).resolve().parents[1] / "validate-cross-critique.py"
    spec = importlib.util.spec_from_file_location("vcc", spec_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["vcc"] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_master(prebuilt: Path, slug: str, sources: list[dict], cross_critique=None):
    d = prebuilt / f"master-{slug}"
    d.mkdir(parents=True, exist_ok=True)
    data = {"slug": slug, "sources": sources}
    if cross_critique is not None:
        data["cross_critique"] = cross_critique
    (d / "meta.json").write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def fake_tree(tmp_path):
    prebuilt = tmp_path / "prebuilt"
    # build enough masters to satisfy required_pairs in tests that need them
    for slug in [
        "huineng", "yinguang", "kumarajiva", "xuanzang", "zhiyi",
        "tsongkhapa", "ajahn-chah", "mahasi-sayadaw", "atisha", "ouyi",
    ]:
        _write_master(prebuilt, slug, [{"type": "cbeta", "id": "T00n0001", "title": "demo"}])
    return prebuilt


def test_empty_cross_critique_is_ok(fake_tree):
    vcc = _load_module()
    # No master has cross_critique; structural check passes,
    # but required_pairs check still fails (no coverage).
    errors = vcc.validate(fake_tree, check_coverage=False)
    assert errors == []


def test_well_formed_entry_passes(fake_tree):
    vcc = _load_module()
    _write_master(fake_tree, "huineng",
        [{"type": "cbeta", "id": "T48n2008", "title": "坛经"}],
        cross_critique=[
            {"target_master": "yinguang", "position": "对净土：本性弥陀唯心净土，何曾离自心。", "citation": "T48n2008"},
        ])
    errors = vcc.validate(fake_tree, check_coverage=False)
    # Only the huineng→yinguang structural check should pass.
    huineng_errors = [e for e in errors if "huineng" in e]
    assert huineng_errors == []


def test_missing_required_field(fake_tree):
    vcc = _load_module()
    _write_master(fake_tree, "huineng",
        [{"type": "cbeta", "id": "T48n2008", "title": "坛经"}],
        cross_critique=[{"target_master": "yinguang"}])  # no position, no citation
    errors = vcc.validate(fake_tree, check_coverage=False)
    assert any("position" in e for e in errors)
    assert any("citation" in e for e in errors)


def test_cannot_target_self(fake_tree):
    vcc = _load_module()
    _write_master(fake_tree, "huineng",
        [{"type": "cbeta", "id": "T48n2008", "title": "坛经"}],
        cross_critique=[{"target_master": "huineng", "position": "x" * 50, "citation": "T48n2008"}])
    errors = vcc.validate(fake_tree, check_coverage=False)
    assert any("self" in e.lower() for e in errors)


def test_cannot_target_meta_skill(fake_tree):
    vcc = _load_module()
    _write_master(fake_tree, "huineng",
        [{"type": "cbeta", "id": "T48n2008", "title": "坛经"}],
        cross_critique=[{"target_master": "curriculum", "position": "x" * 50, "citation": "T48n2008"}])
    errors = vcc.validate(fake_tree, check_coverage=False)
    assert any("meta-skill" in e or "curriculum" in e for e in errors)


def test_unknown_target_master(fake_tree):
    vcc = _load_module()
    _write_master(fake_tree, "huineng",
        [{"type": "cbeta", "id": "T48n2008", "title": "坛经"}],
        cross_critique=[{"target_master": "ghost", "position": "x" * 50, "citation": "T48n2008"}])
    errors = vcc.validate(fake_tree, check_coverage=False)
    assert any("ghost" in e for e in errors)


def test_citation_not_in_own_sources(fake_tree):
    vcc = _load_module()
    _write_master(fake_tree, "huineng",
        [{"type": "cbeta", "id": "T48n2008", "title": "坛经"}],
        cross_critique=[{"target_master": "yinguang", "position": "x" * 50, "citation": "T99n9999"}])
    errors = vcc.validate(fake_tree, check_coverage=False)
    assert any("T99n9999" in e for e in errors)


def test_position_length_bounds(fake_tree):
    vcc = _load_module()
    _write_master(fake_tree, "huineng",
        [{"type": "cbeta", "id": "T48n2008", "title": "坛经"}],
        cross_critique=[
            {"target_master": "yinguang", "position": "短", "citation": "T48n2008"},  # < 10
            {"target_master": "zhiyi", "position": "x" * 400, "citation": "T48n2008"},  # > 300
        ])
    errors = vcc.validate(fake_tree, check_coverage=False)
    assert any("length" in e for e in errors)


def test_coverage_fails_when_pairs_missing(fake_tree):
    vcc = _load_module()
    errors = vcc.validate(fake_tree, check_coverage=True)
    # Should report all 16 missing critique entries.
    missing_errors = [e for e in errors if "missing critique" in e]
    assert len(missing_errors) == 16


def test_coverage_succeeds_with_full_pairs(fake_tree):
    vcc = _load_module()
    pairs = [
        ("huineng", "yinguang"), ("yinguang", "huineng"),
        ("kumarajiva", "xuanzang"), ("xuanzang", "kumarajiva"),
        ("huineng", "zhiyi"), ("zhiyi", "huineng"),
        ("tsongkhapa", "huineng"), ("huineng", "tsongkhapa"),
        ("ajahn-chah", "mahasi-sayadaw"), ("mahasi-sayadaw", "ajahn-chah"),
        ("atisha", "huineng"), ("huineng", "atisha"),
        ("ouyi", "yinguang"), ("yinguang", "ouyi"),
        ("ouyi", "tsongkhapa"), ("tsongkhapa", "ouyi"),
    ]
    by_slug: dict[str, list[dict]] = {}
    for src, tgt in pairs:
        by_slug.setdefault(src, []).append(
            {"target_master": tgt, "position": "x" * 50, "citation": "T00n0001"})
    for slug, cc in by_slug.items():
        _write_master(fake_tree, slug, [{"type": "cbeta", "id": "T00n0001", "title": "demo"}], cc)
    errors = vcc.validate(fake_tree, check_coverage=True)
    assert errors == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ~/projects/master-skill && python3 -m pytest scripts/tests/test_validate_cross_critique.py -v 2>&1 | tail -15
```
Expected: all tests fail (module doesn't exist yet).

- [ ] **Step 3: Implement the validator**

Create `scripts/validate-cross-critique.py`:

```python
#!/usr/bin/env python3
"""Validate cross_critique field structure across master meta.json files.

Verifies:
  1. Each cross_critique entry has target_master, position, citation
  2. target_master is a real master (not self, not meta-skill, exists)
  3. citation is a real id in this master's own sources[].id
  4. position length in [10, 300]
  5. Coverage: 8 canonical debate pairs are covered bidirectionally

Pure offline structural check.

Usage:
    python3 scripts/validate-cross-critique.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PREBUILT_DIR = Path(__file__).resolve().parent.parent / "prebuilt"

META_SKILL_SLUGS = {"curriculum", "debate", "compare-masters"}

REQUIRED_PAIRS = [
    ("huineng", "yinguang"),
    ("kumarajiva", "xuanzang"),
    ("huineng", "zhiyi"),
    ("tsongkhapa", "huineng"),
    ("ajahn-chah", "mahasi-sayadaw"),
    ("atisha", "huineng"),
    ("ouyi", "yinguang"),
    ("ouyi", "tsongkhapa"),
]

POSITION_MIN = 10
POSITION_MAX = 300


def _load(meta_path: Path) -> dict:
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def collect_master_slugs(prebuilt: Path) -> set[str]:
    return {p.parent.name.removeprefix("master-")
            for p in prebuilt.glob("master-*/meta.json")}


def collect_sources_by_slug(prebuilt: Path) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for meta_path in prebuilt.glob("master-*/meta.json"):
        slug = meta_path.parent.name.removeprefix("master-")
        ids = set()
        for s in _load(meta_path).get("sources", []):
            sid = s.get("id")
            if sid:
                ids.add(sid)
        out[slug] = ids
    return out


def collect_critique_pairs(prebuilt: Path) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for meta_path in prebuilt.glob("master-*/meta.json"):
        src = meta_path.parent.name.removeprefix("master-")
        for e in _load(meta_path).get("cross_critique", []) or []:
            tgt = e.get("target_master")
            if isinstance(tgt, str):
                pairs.add((src, tgt))
    return pairs


def validate(prebuilt: Path, *, check_coverage: bool = True) -> list[str]:
    errors: list[str] = []
    known_slugs = collect_master_slugs(prebuilt)
    sources_by_slug = collect_sources_by_slug(prebuilt)

    for meta_path in sorted(prebuilt.glob("master-*/meta.json")):
        slug = meta_path.parent.name.removeprefix("master-")
        data = _load(meta_path)
        cc = data.get("cross_critique")
        if cc is None:
            continue
        if not isinstance(cc, list):
            errors.append(f"{slug}: cross_critique must be list, got {type(cc).__name__}")
            continue
        for i, entry in enumerate(cc):
            prefix = f"{slug}#{i}"
            if not isinstance(entry, dict):
                errors.append(f"{prefix}: entry must be object")
                continue
            for k in ("target_master", "position", "citation"):
                v = entry.get(k)
                if not v or not isinstance(v, str):
                    errors.append(f"{prefix}: missing or empty {k}")
            tm = entry.get("target_master") or ""
            if tm == slug:
                errors.append(f"{prefix}: cannot target self")
            elif tm in META_SKILL_SLUGS:
                errors.append(f"{prefix}: cannot target meta-skill '{tm}'")
            elif tm and tm not in known_slugs:
                errors.append(f"{prefix}: target_master '{tm}' not a known master")
            cit = entry.get("citation") or ""
            if cit and cit not in sources_by_slug.get(slug, set()):
                errors.append(f"{prefix}: citation '{cit}' not in {slug}'s sources[].id")
            pos = entry.get("position") or ""
            if pos and not (POSITION_MIN <= len(pos) <= POSITION_MAX):
                errors.append(f"{prefix}: position length {len(pos)} out of [{POSITION_MIN}, {POSITION_MAX}]")

    if check_coverage:
        pairs = collect_critique_pairs(prebuilt)
        for a, b in REQUIRED_PAIRS:
            if (a, b) not in pairs:
                errors.append(f"missing critique: {a} → {b}")
            if (b, a) not in pairs:
                errors.append(f"missing critique: {b} → {a}")

    return errors


def main() -> int:
    errors = validate(PREBUILT_DIR)
    if errors:
        print(f"{len(errors)} cross_critique error(s):")
        for e in errors:
            print(f"  ERROR: {e}")
        return 1
    print("cross_critique OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd ~/projects/master-skill && python3 -m pytest scripts/tests/test_validate_cross_critique.py -v 2>&1 | tail -15
```
Expected: 10 passed.

- [ ] **Step 5: Smoke-run on real tree**

```bash
cd ~/projects/master-skill && python3 scripts/validate-cross-critique.py; echo "exit=$?"
```
Expected: prints 16 "missing critique" errors and exits 1 (no master has the field yet). That's fine — Tasks 3-12 fill them in.

- [ ] **Step 6: Commit**

```bash
cd ~/projects/master-skill
git add scripts/validate-cross-critique.py scripts/tests/test_validate_cross_critique.py
git commit -m "feat(validate): add validate-cross-critique.py

Enforces cross_critique field structure (target_master / position /
citation), self-reference + meta-skill targets blocked, citation must
be in this master's own sources[].id, position length [10, 300],
and the 8 canonical debate pairs must be covered bidirectionally
(16 entries minimum). Test-first, 10 unit tests."
```

---

## Phase 2 — master-debate wiring

### Task 2: Add 「批判点注入」 section to `master-debate/SKILL.md`

**Files:**
- Modify: `prebuilt/master-debate/SKILL.md`

- [ ] **Step 1: Locate insertion point**

The section goes BETWEEN `## 名称解析` and `## 轮次结构`. Verify:

```bash
cd ~/projects/master-skill && grep -n "^## " prebuilt/master-debate/SKILL.md
```

- [ ] **Step 2: Insert new section**

After the `## 名称解析` block (which lists slug → 全称 mappings) and BEFORE `## 轮次结构`, insert:

```markdown
## 批判点注入（v0.7.1）

选定配对 (A, B) 后，runtime **必须**：

1. 读 `prebuilt/master-<A>/meta.json` 的 `cross_critique`，筛选 `target_master == B` 的 entry
2. 读 `prebuilt/master-<B>/meta.json` 的 `cross_critique`，筛选 `target_master == A` 的 entry
3. 把筛到的 `position` 文 + 对应 `citation` 当作"本祖师对对方的标准立场"上下文注入：
   - R1（A 立论）：A 关于 B 的立场，作为立论时区别于 B 的依据
   - R2（B 反驳）：B 关于 A 的立场，作为反驳 A 立论的 grounding
   - R3（A 回应）：A 再次引用本人立场
   - R4（B 综合）：B 引用以呈现"教内余争"中的"仍异"

若任一 master 的 `cross_critique` 缺对应 entry，注入留空——退回到「禁稻草人」+「引经必经查证」硬约束兜底，**不阻塞流程**。
```

- [ ] **Step 3: Commit**

```bash
cd ~/projects/master-skill
git add prebuilt/master-debate/SKILL.md
git commit -m "feat(v0.7.1): master-debate — add cross_critique injection guidance

Runtime now instructed to look up cross_critique entries by pair (A, B)
and inject 'this master's stance toward that tradition' into R1/R2/R3/R4
context. Missing entries fall back to v0.7 hard-constraint guards."
```

---

## Phase 3 — Master meta.json edits (10 masters, 16 entries)

Each task adds the `cross_critique` field after the `sources` field, before `version` (or wherever JSON ordering is convenient). The JSON must remain valid; after every edit run `python3 -m json.tool` to verify.

**Common pattern** — add as the last key in the meta.json (after `search_scope`, before the trailing `}`):

```json
  ,
  "cross_critique": [
    { "target_master": "<slug>", "position": "<text>", "citation": "<id>" }
  ]
```

(Note the leading comma — the previous block (typically `search_scope`) must end with `}` not `},` BEFORE this edit. After insertion, the previous key gets a trailing comma. Use `python3 -m json.tool < meta.json` to validate after each edit.)

After ALL meta.json edits done, run once:

```bash
cd ~/projects/master-skill && python3 scripts/validate-cross-critique.py
```
Expected: `cross_critique OK` (exit 0) after Task 12 is done. Intermediate tasks may still report missing-pair errors — that's fine.

---

### Task 3: huineng (4 entries)

**File:** `prebuilt/master-huineng/meta.json`

- [ ] **Step 1: Verify huineng sources** (must include T48n2008)

```bash
cd ~/projects/master-skill && python3 -c "import json; d=json.load(open('prebuilt/master-huineng/meta.json')); print([s['id'] for s in d['sources']])"
```
Expected: `['T48n2008', 'T08n0235', 'T14n0475']`

- [ ] **Step 2: Add cross_critique field** with EXACTLY these 4 entries:

```json
"cross_critique": [
  { "target_master": "yinguang", "position": "对净土：本性弥陀，唯心净土；念佛不离自心，即心见佛，何须外求？以无心为有心是诳。", "citation": "T48n2008" },
  { "target_master": "zhiyi", "position": "对天台：判教为方便引摄初机；然观心一念已具三千，何须开权？顿入直指即是究竟，不假阶级。", "citation": "T48n2008" },
  { "target_master": "tsongkhapa", "position": "对应成：分判应成自续，破立有所皆是名言假施设；离破立处即真见，何须辨了不了义？", "citation": "T48n2008" },
  { "target_master": "atisha", "position": "对噶当：下中上次第为初机方便；若识自本心，三士不二，烦恼即菩提。本来无次第，何处立三士？", "citation": "T48n2008" }
]
```

- [ ] **Step 3: Validate JSON**

```bash
cd ~/projects/master-skill && python3 -m json.tool prebuilt/master-huineng/meta.json > /dev/null && echo "valid JSON"
```

- [ ] **Step 4: Commit**

```bash
cd ~/projects/master-skill
git add prebuilt/master-huineng/meta.json
git commit -m "feat(v0.7.1): huineng cross_critique — 4 entries (yinguang/zhiyi/tsongkhapa/atisha)"
```

---

### Task 4: yinguang (2 entries)

**File:** `prebuilt/master-yinguang/meta.json` — citation must be in `['X62n1182', 'X62n1183', 'X62n1184', 'T12n0366', 'T12n0365', 'T12n0360']`

Add:
```json
"cross_critique": [
  { "target_master": "huineng", "position": "对禅宗：见性须现量证悟，末法众生根机陋劣，难当此任；信愿持名是阿弥陀佛大悲普被，老实念佛即是真见性。", "citation": "X62n1182" },
  { "target_master": "ouyi", "position": "对天台净土合修：要解六信极是；然事持理持终归一念，今人务理而废事，唯老实持名方为稳妥。", "citation": "X62n1182" }
]
```

JSON valid → commit:
```bash
cd ~/projects/master-skill && python3 -m json.tool prebuilt/master-yinguang/meta.json > /dev/null && git add prebuilt/master-yinguang/meta.json && git commit -m "feat(v0.7.1): yinguang cross_critique — 2 entries (huineng/ouyi)"
```

---

### Task 5: kumarajiva (1 entry)

**File:** `prebuilt/master-kumarajiva/meta.json` — citation in `['T09n0262', 'T08n0235', 'T14n0475', 'T30n1564', 'T25n1509', 'T12n0366']`

Add:
```json
"cross_critique": [
  { "target_master": "xuanzang", "position": "对唯识：诸法因缘生，我说即是空；说万法唯识，识亦缘起，不可执为实有自体。空有非二，皆为破执而设。", "citation": "T30n1564" }
]
```

```bash
cd ~/projects/master-skill && python3 -m json.tool prebuilt/master-kumarajiva/meta.json > /dev/null && git add prebuilt/master-kumarajiva/meta.json && git commit -m "feat(v0.7.1): kumarajiva cross_critique — 1 entry (xuanzang)"
```

---

### Task 6: xuanzang (1 entry)

**File:** `prebuilt/master-xuanzang/meta.json` — citation in `['T07n0220', 'T30n1579', 'T31n1585', 'T08n0251', 'T29n1558', 'T51n2087']`

Add:
```json
"cross_critique": [
  { "target_master": "kumarajiva", "position": "对中观：唯识三性三无性具足空义，不堕断空；中观破而无立易使学人不知次第，先立五位百法方可入空。", "citation": "T31n1585" }
]
```

```bash
cd ~/projects/master-skill && python3 -m json.tool prebuilt/master-xuanzang/meta.json > /dev/null && git add prebuilt/master-xuanzang/meta.json && git commit -m "feat(v0.7.1): xuanzang cross_critique — 1 entry (kumarajiva)"
```

---

### Task 7: zhiyi (1 entry)

**File:** `prebuilt/master-zhiyi/meta.json` — citation in `['T46n1911', 'T33n1718', 'T34n1718', 'T46n1915', 'T09n0262']`

Add:
```json
"cross_critique": [
  { "target_master": "huineng", "position": "对禅宗顿悟：顿悟一念固是事；须知一念三千、性具善恶，理观事造皆备方为圆顿；离开教相判摄，恐落孤山顿悟。", "citation": "T46n1911" }
]
```

```bash
cd ~/projects/master-skill && python3 -m json.tool prebuilt/master-zhiyi/meta.json > /dev/null && git add prebuilt/master-zhiyi/meta.json && git commit -m "feat(v0.7.1): zhiyi cross_critique — 1 entry (huineng)"
```

---

### Task 8: tsongkhapa (2 entries)

**File:** `prebuilt/master-tsongkhapa/meta.json` — citation in `['BDRC:gsung-bum', 'Lam-rim-chen-mo', 'sNgags-rim-chen-mo', 'Drang-nges-legs-bshad-snying-po', 'Lam-gtso-rnam-gsum']`

Add:
```json
"cross_critique": [
  { "target_master": "huineng", "position": "对禅宗顿悟：无次第直指乃极利根所行；中根以下若不依应成正理分别自相，离名言假施设即立自性见，反成执碍。", "citation": "Lam-rim-chen-mo" },
  { "target_master": "ouyi", "position": "对天台净土合修：教观判摄虽善，然空性正见须用应成因明遮遣自相；若未破自性见，所行虽多终为有漏。", "citation": "Drang-nges-legs-bshad-snying-po" }
]
```

```bash
cd ~/projects/master-skill && python3 -m json.tool prebuilt/master-tsongkhapa/meta.json > /dev/null && git add prebuilt/master-tsongkhapa/meta.json && git commit -m "feat(v0.7.1): tsongkhapa cross_critique — 2 entries (huineng/ouyi)"
```

---

### Task 9: ajahn-chah (1 entry)

**File:** `prebuilt/master-ajahn-chah/meta.json` — citation in `['SuttaCentral', 'AjahnChah:FoodForTheHeart', 'AjahnChah:StillForestPool', 'AjahnChah:LivingDhamma']`

Add:
```json
"cross_critique": [
  { "target_master": "mahasi-sayadaw", "position": "对马哈希标记法：标记引人入念是巧方便；然过分细标易成造作，不如观自然呼吸、自然念头来去，戒律为基方稳。", "citation": "AjahnChah:StillForestPool" }
]
```

```bash
cd ~/projects/master-skill && python3 -m json.tool prebuilt/master-ajahn-chah/meta.json > /dev/null && git add prebuilt/master-ajahn-chah/meta.json && git commit -m "feat(v0.7.1): ajahn-chah cross_critique — 1 entry (mahasi-sayadaw)"
```

---

### Task 10: mahasi-sayadaw (1 entry)

**File:** `prebuilt/master-mahasi-sayadaw/meta.json` — citation in `['Mahasi:ManualOfInsight', 'Mahasi:ProgressOfInsight', 'Mahasi:PracticalVipassana', 'Mahasi:DiscoursesOnSuttas', 'SuttaCentral', 'PTS:Vism']`

Add:
```json
"cross_critique": [
  { "target_master": "ajahn-chah", "position": "对森林禅：自然观察殊胜，然初学者无所依易散乱；标记法令心住于所缘，使念念分明、十六观智次第现起。", "citation": "Mahasi:ManualOfInsight" }
]
```

```bash
cd ~/projects/master-skill && python3 -m json.tool prebuilt/master-mahasi-sayadaw/meta.json > /dev/null && git add prebuilt/master-mahasi-sayadaw/meta.json && git commit -m "feat(v0.7.1): mahasi-sayadaw cross_critique — 1 entry (ajahn-chah)"
```

---

### Task 11: atisha (1 entry)

**File:** `prebuilt/master-atisha/meta.json` — citation in `['Toh:4465', 'Toh:3948', 'BDRC:Pha-chos-Bu-chos']`

Add:
```json
"cross_critique": [
  { "target_master": "huineng", "position": "对禅宗顿悟：顿入心性诚为上根所行；然依止善知识、暇满业果须先建立；不立三士道径求自性，恐落空知见。", "citation": "Toh:4465" }
]
```

```bash
cd ~/projects/master-skill && python3 -m json.tool prebuilt/master-atisha/meta.json > /dev/null && git add prebuilt/master-atisha/meta.json && git commit -m "feat(v0.7.1): atisha cross_critique — 1 entry (huineng)"
```

---

### Task 12: ouyi (2 entries)

**File:** `prebuilt/master-ouyi/meta.json` — citation in `['T37n1762', 'T09n0262', 'T24n1484', 'T12n0366', 'T31n1585']`

Add:
```json
"cross_critique": [
  { "target_master": "yinguang", "position": "对净土：信愿持名极是；然不解教理事理之分，难免被禅家'老实'二字所误；要解六信须并参方为圆解。", "citation": "T37n1762" },
  { "target_master": "tsongkhapa", "position": "对应成中观：应成破自相极利；然性相二宗未会、空有未融，恐落'非有非无'之偏；天台一念三千圆收性相。", "citation": "T37n1762" }
]
```

```bash
cd ~/projects/master-skill && python3 -m json.tool prebuilt/master-ouyi/meta.json > /dev/null && git add prebuilt/master-ouyi/meta.json && git commit -m "feat(v0.7.1): ouyi cross_critique — 2 entries (yinguang/tsongkhapa)"
```

---

## Phase 4 — Final gate

### Task 13: CHANGELOG + version bump + full CI

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `package.json` + 4 plugin manifests (via .version-bump.json)

- [ ] **Step 1: CHANGELOG entry**

Insert at top of `CHANGELOG.md` (above the v0.7.0 entry):

```markdown
## [0.7.1] — 2026-06-06

### Added
- `cross_critique` field on 10 master `meta.json` files — 16 doctrinal entries covering all 8 canonical debate pairs bidirectionally. Each entry is `{target_master, position, citation}` where citation must be in the master's own `sources[].id`.
- `scripts/validate-cross-critique.py` — offline CI gate enforcing structure + citation reality + 8-pair coverage. 10 unit tests.
- `prebuilt/master-debate/SKILL.md`: new 「批判点注入」 section instructing runtime to inject `cross_critique` entries into R1-R4 turns when present.

### Changed
- Version bump 0.7.0 → 0.7.1 across `package.json` + 4 plugin manifests.

### Not Changed
- master-debate 4 轮结构 / 输出框架 / 硬约束 全部不动
- master-curriculum / compare-masters 不动
- 单 master SKILL.md / references / sources / tests 全部不动
- 不触发 npm publish（NPM_TOKEN 仍待重签）
```

- [ ] **Step 2: Version bump**

```bash
cd ~/projects/master-skill && node -e "
const fs = require('fs');
const cfg = JSON.parse(fs.readFileSync('.version-bump.json', 'utf8'));
for (const f of cfg.files) {
  const j = JSON.parse(fs.readFileSync(f.path, 'utf8'));
  const parts = f.field.split('.');
  let ref = j;
  for (let i = 0; i < parts.length - 1; i++) {
    const p = parts[i];
    ref = p.match(/^\d+$/) ? ref[Number(p)] : ref[p];
  }
  ref[parts[parts.length - 1]] = '0.7.1';
  fs.writeFileSync(f.path, JSON.stringify(j, null, 2) + '\n');
  console.log('bumped', f.path);
}
"
```

Expected: 5 lines, all `bumped <path>`.

- [ ] **Step 3: Full CI gate**

```bash
cd ~/projects/master-skill
python3 scripts/validate.py --strict 2>&1 | tail -3
python3 scripts/validate-fidelity.py 2>&1 | tail -3
python3 scripts/validate-curriculum-sources.py
python3 scripts/validate-cross-critique.py
python3 -m pytest scripts/tests/ -q 2>&1 | tail -3
node bin/cli.mjs list 2>&1 | grep -E "master-debate|master-curriculum" | head -5
```

Expected:
- validate.py: green
- validate-fidelity.py: green (17 masters)
- validate-curriculum-sources.py: `curriculum sources OK`
- validate-cross-critique.py: `cross_critique OK`
- pytest: 22 passed (12 v0.7 + 10 v0.7.1)
- cli.mjs: shows both

If any fails, stop and fix the root cause — do not commit.

- [ ] **Step 4: Commit**

```bash
cd ~/projects/master-skill
git add CHANGELOG.md package.json .claude-plugin/plugin.json .claude-plugin/marketplace.json .cursor-plugin/plugin.json gemini-extension.json
git commit -m "chore(v0.7.1): bump version to 0.7.1 + CHANGELOG entry"
```

---

### Task 14: Open PR + merge

- [ ] **Step 1: Push**

```bash
cd ~/projects/master-skill && git push -u origin feat/v0.7.1-cross-critique
```

- [ ] **Step 2: Open PR**

```bash
cd ~/projects/master-skill && gh pr create --title "feat(v0.7.1): cross_critique field — reduce debate strawman risk" --body "$(cat <<'EOF'
## Summary

Implements v0.7 spec §11 路径 B 增量: add `cross_critique` field to 10 single-master `meta.json` files (16 doctrinal entries) and wire `master-debate` to inject them into R1-R4 turns when present.

## What's new

- `cross_critique: [{target_master, position, citation}]` on huineng (4), yinguang (2), kumarajiva (1), xuanzang (1), zhiyi (1), tsongkhapa (2), ajahn-chah (1), mahasi-sayadaw (1), atisha (1), ouyi (2)
- `scripts/validate-cross-critique.py` — enforces structure + citation reality + 8 canonical pair bidirectional coverage (10 unit tests)
- `prebuilt/master-debate/SKILL.md` new 「批判点注入」 section

## Test plan

- [x] `python3 scripts/validate.py --strict` passes
- [x] `python3 scripts/validate-fidelity.py` passes (17 masters)
- [x] `python3 scripts/validate-curriculum-sources.py` passes
- [x] `python3 scripts/validate-cross-critique.py` passes (16 entries, full coverage)
- [x] `python3 -m pytest scripts/tests/ -q` 22 passed
- [ ] Manual dry-run 禅净 debate (R2/R3 now reference 印光对禅 / 慧能对净 specific position rather than generic rebuttal)

## Spec / Plan

- Spec: `docs/superpowers/specs/2026-06-06-master-skill-v071-cross-critique-design.md`
- Plan: `docs/superpowers/plans/2026-06-06-master-skill-v071-cross-critique.md`

## Doctrinal disclaimer

All 16 position texts are scholarly approximations of each master's well-attested stance toward the named tradition, each anchored to a real citation from that master's own sources[].id. They are not strawman statements. Treat them as PR-reviewable doctrinal claims; suggestions welcome.

## Not in this PR

- buddhaghosa / fazang / xuyun / milarepa cross_critique (out of debate pair table; v0.7.2 if needed)
- v0.8: LLM-as-judge round + fojin RAG hook
- npm publish (NPM_TOKEN still revoked)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Wait for CI**

```bash
cd ~/projects/master-skill && sleep 10 && gh pr checks --watch --interval 10 2>&1 | tail -10
```

Expected all green.

- [ ] **Step 4: Merge with --merge (NOT --squash)**

Per memory `feedback_merge_not_squash`: preserve all individual commits.

```bash
cd ~/projects/master-skill && gh pr merge --merge --delete-branch 2>&1 | tail -5
```

If fast-forward conflict (main moved): `git fetch origin main && git merge origin/main --no-ff` locally, push, then merge.

- [ ] **Step 5: Sync local main**

```bash
cd ~/projects/master-skill && git checkout main && git pull origin main && git log --oneline -3
```

---

## Self-Review Notes

- **Spec coverage**: Spec §3 (schema) → Tasks 3-12. Spec §5 (wiring) → Task 2. Spec §6 (validator) → Task 1. Spec §7 (CHANGELOG/version) → Task 13. ✓
- **Placeholder scan**: All 16 position texts inline, all citations verified against pre-fetched sources data. No TBD. ✓
- **Type consistency**: All slugs verified (kebab-case), all citation IDs verified against meta.json. `target_master`/`position`/`citation` consistent across spec/plan/tests/impl. ✓
- **Bite-size**: Each meta.json edit is one task, validate after each. Tasks 5/6/7/9/10/11 are tiny (1-entry each).
