# Cross-Tradition Citation Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace CBETA-only project rules with a deterministic declared-source citation contract valid across Chinese, Tibetan, and Pali source families.

**Architecture:** Every persona metadata file declares the exact source types it permits. A standalone Python validator enforces the versioned shape and equality with `sources[].type`; runtime instructions and reviewer prompts consume the source-neutral policy.

**Tech Stack:** Python 3.11+, JSON metadata, pytest, Markdown skill instructions.

## Global Constraints

- Exactly 15 persona metadata files receive `citation_contract`; meta-skills do not.
- `allowed_source_types` equals sorted unique `sources[].type` for the same persona.
- The required policy string is `declared_sources_only`; coverage is numeric `0.9`.
- No source ID, quotation, excerpt, or doctrinal position changes.
- Do not edit npm/CLI files, CI workflows, fidelity runner, voice tests, or Rust files.

---

### Task 1: Build the deterministic citation-contract validator

**Files:**
- Create: `scripts/validate-citation-contract.py`
- Create: `scripts/tests/test_validate_citation_contract.py`

**Interfaces:**
- Produces: `validate(prebuilt_dir: Path) -> list[str]` and CLI exit 0/1.

- [ ] **Step 1: Write validator tests first**

Create helpers that write `prebuilt/master-<slug>/meta.json`, import the hyphenated script with `importlib.util`, and use these complete cases:

```python
def contract(*types: str) -> dict:
    return {
        "version": 1,
        "claim_policy": "declared_sources_only",
        "required_for": ["doctrinal_claim", "practice_guidance", "text_interpretation"],
        "allowed_source_types": sorted(types),
        "minimum_claim_coverage": 0.9,
        "live_retrieval_allowed": True,
    }

def write_meta(prebuilt: Path, slug: str, source_types: list[str], value: dict | None) -> None:
    directory = prebuilt / f"master-{slug}"
    directory.mkdir(parents=True)
    data = {
        "slug": slug,
        "sources": [
            {"type": source_type, "id": f"id-{index}", "title": f"source-{index}"}
            for index, source_type in enumerate(source_types)
        ],
    }
    if value is not None:
        data["citation_contract"] = value
    (directory / "meta.json").write_text(json.dumps(data), encoding="utf-8")

@pytest.mark.parametrize("source_types", [
    ["cbeta"],
    ["tibetan_canon", "tibetan_treatise"],
    ["compiled_teaching", "pali_canon", "pali_treatise"],
])
def test_valid_source_family_contracts_pass(validator, fake_tree, source_types):
    write_meta(fake_tree, "demo", source_types, contract(*source_types))
    assert validator.validate(fake_tree) == []

def test_missing_contract_fails(validator, fake_tree):
    write_meta(fake_tree, "demo", ["cbeta"], None)
    errors = validator.validate(fake_tree)
    assert any("master-demo/meta.json" in error and "citation_contract" in error for error in errors)

@pytest.mark.parametrize("allowed", [[], ["cbeta", "pali_canon"]])
def test_source_type_drift_fails(validator, fake_tree, allowed):
    value = contract("cbeta")
    value["allowed_source_types"] = allowed
    write_meta(fake_tree, "demo", ["cbeta"], value)
    errors = validator.validate(fake_tree)
    assert any("master-demo/meta.json" in error and "allowed_source_types" in error for error in errors)

@pytest.mark.parametrize(("field", "invalid"), [
    ("version", 2),
    ("claim_policy", "any_source"),
    ("required_for", ["doctrinal_claim"]),
    ("minimum_claim_coverage", True),
    ("minimum_claim_coverage", 0.8),
    ("live_retrieval_allowed", "yes"),
])
def test_fixed_contract_values_are_enforced(validator, fake_tree, field, invalid):
    value = contract("cbeta")
    value[field] = invalid
    write_meta(fake_tree, "demo", ["cbeta"], value)
    errors = validator.validate(fake_tree)
    assert any("master-demo/meta.json" in error and field in error for error in errors)

def test_meta_skill_without_sources_is_ignored(validator, fake_tree):
    write_meta(fake_tree, "debate", [], None)
    assert validator.validate(fake_tree) == []
```

The passing fixtures use `sources` containing the same types passed to `contract`. Every failing assertion checks that the error includes `master-<slug>/meta.json` and the invalid field name.

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest scripts/tests/test_validate_citation_contract.py -v`  
Expected: FAIL because the validator module does not exist.

- [ ] **Step 3: Implement the validator**

The validator iterates `prebuilt/master-*/meta.json`, skips entries whose `sources` is missing or empty, and validates exact keys:

```python
EXPECTED_REQUIRED_FOR = [
    "doctrinal_claim", "practice_guidance", "text_interpretation",
]
EXPECTED_KEYS = {
    "version", "claim_policy", "required_for", "allowed_source_types",
    "minimum_claim_coverage", "live_retrieval_allowed",
}
```

Reject booleans as numeric coverage, require every source type to be a non-empty string, and compare allowed types to `sorted(set(source_types))`. The CLI defaults to repository `prebuilt/`, prints every error to stderr, prints `citation contracts OK (15 personas)` on success, and exits 1 when errors exist.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest scripts/tests/test_validate_citation_contract.py -v`  
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/validate-citation-contract.py scripts/tests/test_validate_citation_contract.py
git commit -m "feat(citations): add source-neutral contract validator"
```

### Task 2: Add contracts to all persona metadata

**Files:**
- Modify: `prebuilt/master-*/meta.json` for the 15 personas with non-empty `sources`.

**Interfaces:**
- Consumes: validator from Task 1.
- Produces: valid per-persona `citation_contract` objects.

- [ ] **Step 1: Run the validator and verify RED against repository data**

Run: `python scripts/validate-citation-contract.py`  
Expected: exit 1 with 15 missing-contract errors.

- [ ] **Step 2: Add each contract mechanically**

For each persona, insert:

```json
"citation_contract": {
  "version": 1,
  "claim_policy": "declared_sources_only",
  "required_for": ["doctrinal_claim", "practice_guidance", "text_interpretation"],
  "allowed_source_types": [],
  "minimum_claim_coverage": 0.9,
  "live_retrieval_allowed": true
}
```

Replace the empty array with the sorted unique types already present in that same file's `sources`. Do not change any other metadata value.

- [ ] **Step 3: Verify contracts and metadata diffs**

Run:

```bash
python scripts/validate-citation-contract.py
python scripts/validate-persona-fidelity.py
git diff -- prebuilt/master-*/meta.json
```

Expected: both validators exit 0; metadata diffs contain only `citation_contract` additions.

- [ ] **Step 4: Commit**

```bash
git add prebuilt/master-*/meta.json
git commit -m "feat(citations): declare persona source contracts"
```

### Task 3: Align runtime and governance wording

**Files:**
- Modify: `SKILL.md`
- Modify: `prebuilt/compare/SKILL.md`
- Modify: `prompts/doctrine_reviewer.md`
- Modify: `references/ethics-runtime.md`
- Modify: `references/source-conventions.md`
- Modify: `docs/PRD.md`
- Modify: `docs/v1-framework-roadmap.md`
- Modify: `scripts/tests/test_validate_citation_contract.py`

**Interfaces:**
- Consumes: the metadata contract from Task 2.
- Produces: source-neutral runtime instructions and a regression scan.

- [ ] **Step 1: Add a failing repository wording test**

Add a test that reads the owned runtime files and asserts:

```python
forbidden = [
    "NO DOCTRINAL CLAIM WITHOUT CBETA CITATION",
    "每位祖师的回答必须附 CBETA 引用",
    "CBETA 经证覆盖率 ≥ 90%",
    "primary_cbeta_ids 过滤结果",
]
for path in runtime_paths:
    text = path.read_text(encoding="utf-8")
    for phrase in forbidden:
        assert phrase not in text, f"{path}: stale source-family rule: {phrase}"
```

Also assert that root and compare contain `NO DOCTRINAL CLAIM WITHOUT A DECLARED SOURCE CITATION` and mention `citation_contract.allowed_source_types`.

- [ ] **Step 2: Run the wording test and verify RED**

Run: `python -m pytest scripts/tests/test_validate_citation_contract.py -k wording -v`  
Expected: FAIL on current CBETA-only wording.

- [ ] **Step 3: Replace the stale rules**

Use this exact hard-gate heading in root and compare:

```text
NO DOCTRINAL CLAIM WITHOUT A DECLARED SOURCE CITATION.
```

State that citations must resolve to the selected persona's `meta.json.sources[]`, must use a type listed by `citation_contract.allowed_source_types`, and may use live retrieval only when `live_retrieval_allowed` is true. Change the reviewer threshold to `minimum_claim_coverage` from metadata. Change compare retrieval filtering from `primary_cbeta_ids` to the persona's declared source identifiers.

Update governance documentation to identify CBETA, BDRC/Toh, PTS/SuttaCentral, and compiled teachings as equal contract families subject to their own quotation and copyright rules.

- [ ] **Step 4: Run focused and full validation**

Run:

```bash
python -m pytest scripts/tests/test_validate_citation_contract.py -v
python scripts/validate-citation-contract.py
python scripts/validate.py --strict
python scripts/validate-persona-fidelity.py
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```bash
git add SKILL.md prebuilt/compare/SKILL.md prompts/doctrine_reviewer.md \
  references/ethics-runtime.md references/source-conventions.md docs/PRD.md \
  docs/v1-framework-roadmap.md scripts/tests/test_validate_citation_contract.py
git commit -m "fix(citations): enforce declared sources across traditions"
```
