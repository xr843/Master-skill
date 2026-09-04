# Canonical Jiaxing CBETA Identifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct 《靈峰蕅益大師宗論》 to canonical CBETA id `J36nB348` and make both repository source validation and response auditing understand its `JB348` short form.

**Architecture:** Add tests at the two existing identifier boundaries before implementation. Keep metadata validation strict and collection-aware, while keeping answer auditing conservative enough to flag malformed full-looking ids instead of silently ignoring them.

**Tech Stack:** Python 3, pytest, JSON, Markdown, FoJin read-only API

## Global Constraints

- Canonical full id is exactly `J36nB348`; volume-free short id is exactly `JB348`.
- `J36n0348` must be rejected as declared CBETA metadata.
- A response citing canonical `J36nB348` or `JB348` must resolve to declared `J36nB348`.
- A response citing old `J36n0348` must not resolve to declared `J36nB348`.
- FoJin's continued absence of `JB348` must remain visible and tracked by issue #158.
- Do not edit committed report JSON or adjudication verdict JSON.

---

### Task 1: Specify Canonical Jiaxing Behavior

**Files:**
- Modify: `tests/test_verify_sources.py`
- Modify: `tests/test_verify_citations.py`

**Interfaces:**
- Consumes: `FULL_CBETA_RE`, `full_to_short_cbeta()`, and `audit_answer()`
- Produces: regression tests for `J36nB348` / `JB348`

- [x] **Step 1: Replace the incorrect source-tool examples and add rejection coverage**

In `tests/test_verify_sources.py`, require:

```python
def test_full_to_short_cbeta_j_series():
    assert full_to_short_cbeta("J36nB348") == "JB348"


def test_cbeta_id_format_recognition():
    valid_ids = ["T48n2008", "X62n1182", "J36nB348", "T01n0001"]
    for cbeta_id in valid_ids:
        assert FULL_CBETA_RE.match(cbeta_id), f"{cbeta_id} should match FULL_CBETA_RE"
```

Add `J36n0348` to `test_cbeta_id_rejects_invalid()`.

- [x] **Step 2: Add answer-auditor full and short-form tests**

In `tests/test_verify_citations.py`, add:

```python
OUYI_JIAXING = {"J36nB348"}


def test_canonical_jiaxing_full_id_is_offline():
    result = audit_answer(OUYI_JIAXING, "【《靈峰蕅益大師宗論》，J36nB348】")
    assert result["offline"] == ["J36nB348"]
    assert result["fabricated"] == []


def test_canonical_jiaxing_short_id_resolves_to_declared_full_id():
    result = audit_answer(OUYI_JIAXING, "【《靈峰蕅益大師宗論》，JB348】")
    assert result["offline"] == ["J36nB348"]
    assert result["fabricated"] == []


def test_numeric_jiaxing_typo_does_not_resolve_to_canonical_id():
    result = audit_answer(OUYI_JIAXING, "【《靈峰蕅益大師宗論》，J36n0348】")
    assert result["offline"] == []
    assert result["fabricated"] == ["J36n0348"]
```

- [x] **Step 3: Run the targeted tests and verify RED**

Run:

```bash
python3 -m pytest tests/test_verify_sources.py tests/test_verify_citations.py -q
```

Expected: failures show `J36nB348` is not accepted/shortened and is not extracted
by `audit_answer()`; no syntax or import errors.

- [x] **Step 4: Commit the failing specification**

```bash
git add tests/test_verify_sources.py tests/test_verify_citations.py
git commit -m "test(citations): specify canonical Jiaxing ids"
```

### Task 2: Implement Collection-aware CBETA Parsing

**Files:**
- Modify: `tools/verify_sources.py`
- Modify: `scripts/verify_citations.py`

**Interfaces:**
- Consumes: failing tests from Task 1
- Produces: `J36nB348 -> JB348` conversion and full/short response resolution

- [x] **Step 1: Make metadata validation collection-aware**

Define `FULL_CBETA_RE` with named alternatives for existing numeric non-J
identifiers and `B`-prefixed J identifiers. In `full_to_short_cbeta()`, choose the populated
alternative's prefix/text groups and return their concatenation.

```python
FULL_CBETA_RE = re.compile(
    r"^(?:(?P<standard_prefix>[A-IK-Z])(?P<standard_volume>\d+)n"
    r"(?P<standard_text>\d+[a-z]?)|"
    r"(?P<jiaxing_prefix>J)(?P<jiaxing_volume>\d+)n"
    r"(?P<jiaxing_text>B\d+))$"
)

prefix = m.group("standard_prefix") or m.group("jiaxing_prefix")
text_num = m.group("standard_text") or m.group("jiaxing_text")
return f"{prefix}{text_num}"
```

- [x] **Step 2: Extend response extraction and short-form resolution**

Allow an optional uppercase work prefix in full-looking `_CBETA_ID` tokens and
recognise `JB\d{3,}` as a short token. Extend `_SHORT_FORM` / `_FULL_FORM` to
carry `B`-prefixed work numbers, and compare work numbers after removing numeric
leading zeroes while preserving the `B` prefix.

```python
_CBETA_ID = re.compile(
    r"(?<![0-9A-Za-z])(?:"
    r"[A-Z]{1,2}\d+n[A-Z]?\d+[a-z]?|[TX]\d{3,}|JB\d{3,}"
    r")(?![0-9A-Za-z])"
)
_SHORT_FORM = re.compile(r"^([TXJ])(B?\d+)$")
_FULL_FORM = re.compile(r"^([TXJ])\d+n(B?\d+)[a-z]?$")


def _normalize_cbeta_work_number(number: str) -> str:
    prefix = "B" if number.startswith("B") else ""
    digits = number[1:] if prefix else number
    return f"{prefix}{int(digits)}"
```

Use `_normalize_cbeta_work_number()` on both regex number groups inside
`_resolve_short_form()` before comparing them.

- [x] **Step 3: Run the targeted tests and verify GREEN**

Run:

```bash
python3 -m pytest tests/test_verify_sources.py tests/test_verify_citations.py -q
```

Expected: 86 tests pass.

- [x] **Step 4: Commit the parser implementation**

```bash
git add tools/verify_sources.py scripts/verify_citations.py
git commit -m "fix(citations): support canonical Jiaxing ids"
```

### Task 3: Correct The Shipped Source Declaration

**Files:**
- Modify: `prebuilt/master-ouyi/meta.json`
- Modify: `prebuilt/master-ouyi/references/teaching.md`
- Modify: `scripts/validate-citation-references.py`
- Modify: `scripts/tests/test_validate_citation_references.py`
- Modify: `docs/v1-framework-roadmap.md`
- Modify: `eval/reports/BASELINE-deepseek.md`
- Modify: `docs/superpowers/specs/2026-09-05-evaluation-docs-consistency-design.md`
- Modify: `docs/superpowers/plans/2026-09-05-evaluation-docs-consistency.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: canonical parser behavior from Task 2
- Produces: one canonical source id across persona content and current prose

- [x] **Step 1: Replace the shipped id and CBETA Online URLs**

Change `J36n0348` to `J36nB348` in Ouyi metadata and all three teaching-reference
URLs. Update current comments/tests/docs to the canonical id and update the prior
evaluation-consistency record to say the apparent `J0348` external miss was
subsequently diagnosed as a local typo plus a continuing canonical `JB348` FoJin
gap.

- [x] **Step 2: Add the changelog correction**

At the top of `[Unreleased]`, state that official CBETA records use
`J36nB348`, the old declaration dropped `B`, both auditors now support
`J36nB348` / `JB348`, and FoJin still does not resolve `JB348` (#158). Correct
the older `[Unreleased]` mentions of the id because this version has not shipped.

```markdown
### Fixed — Ouyi's Jiaxing source uses its canonical CBETA identifier
- **《靈峰蕅益大師宗論》 is `J36nB348`, not `J36n0348`.** The earlier declaration dropped the Jiaxing catalogue's `B`, producing the invalid FoJin lookup `J0348`. Metadata validation now accepts canonical Jiaxing ids, source and answer auditors map `J36nB348` to short form `JB348`, and Ouyi's declaration and CBETA Online links use the canonical id. FoJin still does not resolve `JB348`; that external coverage gap remains tracked in #158.
```

- [x] **Step 3: Run static source gates**

Run:

```bash
python3 scripts/validate-citation-references.py
python3 tools/verify_sources.py --check-links prebuilt/master-ouyi/meta.json
```

Expected: no undeclared citations and `declared sources OK`.

- [x] **Step 4: Run the FoJin dry run**

Run:

```bash
python3 tools/verify_sources.py
```

Expected: 34/35 resolve, `J36nB348 (-> JB348)` is the sole external miss, and
there are zero URL replacements.

- [x] **Step 5: Commit the source correction**

```bash
git add CHANGELOG.md prebuilt/master-ouyi/meta.json prebuilt/master-ouyi/references/teaching.md scripts/validate-citation-references.py scripts/tests/test_validate_citation_references.py docs/v1-framework-roadmap.md eval/reports/BASELINE-deepseek.md docs/superpowers/specs/2026-09-05-evaluation-docs-consistency-design.md docs/superpowers/plans/2026-09-05-evaluation-docs-consistency.md
git commit -m "fix(ouyi): declare canonical Jiaxing source id"
```

### Task 4: Verify And Deliver

**Files:**
- Create: `docs/superpowers/specs/2026-09-05-canonical-jiaxing-id-design.md`
- Create: `docs/superpowers/plans/2026-09-05-canonical-jiaxing-id.md`

**Interfaces:**
- Consumes: Tasks 1-3
- Produces: reviewed branch evidence and a GitHub correction for issue #158

- [x] **Step 1: Run the full deterministic suite**

Run:

```bash
npm test
```

Expected: all validators, 73 Node tests, and the expanded Python suite pass.

- [x] **Step 2: Review source-id drift and whitespace**

Run:

```bash
rg -n 'J36n0348|J0348' CHANGELOG.md prebuilt scripts tests tools docs eval
git diff --check origin/main...HEAD
```

Expected: the obsolete ids do not remain in current files except where the new
correction explicitly names the old typo; no whitespace errors.

- [x] **Step 3: Update issue #158 with the corrected diagnosis**

Comment with the official CBETA evidence, explain `J36nB348 -> JB348`, and state
that the issue remains open because FoJin still returns no lookup/title result
for the canonical id.

- [x] **Step 4: Mark the plan complete and commit it**

Change every completed checkbox in this plan to `[x]`, then run:

```bash
git add docs/superpowers/specs/2026-09-05-canonical-jiaxing-id-design.md docs/superpowers/plans/2026-09-05-canonical-jiaxing-id.md
git commit -m "docs(plan): record canonical Jiaxing id fix"
```
