"""Tests for scripts/validate.py — the strict gate `npm run validate` runs.

parse_frontmatter had no tests, which is how it kept only the last entry of
`sources:` and dropped every `cbeta_id`. The sources[] checks in lint_master
were reading a shape the file never had.
"""

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "validate.py"
SPEC = importlib.util.spec_from_file_location("validate_module", MODULE_PATH)
validate_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate_module)

parse_frontmatter = validate_module.parse_frontmatter

FRONTMATTER = """---
name: master-test
description: Test master.
version: 0.5.0
license: MIT
lineage: 测试宗
dates: 638-713
sources:
  - title: 六祖大师法宝坛经
    cbeta_id: T48n2008
    fojin_text_id: 58
  - title: 金刚般若波罗蜜经
    cbeta_id: T08n0235
    fojin_text_id: 7
  - title: 维摩诘所说经
    cbeta_id: T14n0475
    fojin_text_id: 28
citation_format: "【《{title}》{section}，{cbeta_id}】"
verified_by: xr843
verified_at: 2026-04-06
---

# Body
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "SKILL.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_frontmatter_keeps_every_source(tmp_path):
    """All three declared sources survive, not just the last one."""
    fm, _, _ = parse_frontmatter(_write(tmp_path, FRONTMATTER))

    titles = [s["title"] for s in fm["sources"]]
    assert titles == ["六祖大师法宝坛经", "金刚般若波罗蜜经", "维摩诘所说经"]


def test_parse_frontmatter_keeps_continuation_keys(tmp_path):
    """cbeta_id and fojin_text_id sit on continuation lines and must survive.

    Every citation check downstream keys off cbeta_id; dropping it silently
    empties the data the sources[] rules are supposed to inspect.
    """
    fm, _, _ = parse_frontmatter(_write(tmp_path, FRONTMATTER))

    assert [s.get("cbeta_id") for s in fm["sources"]] == [
        "T48n2008",
        "T08n0235",
        "T14n0475",
    ]
    assert fm["sources"][0].get("fojin_text_id") == 58


def test_parse_frontmatter_reads_scalar_keys(tmp_path):
    """Scalar keys around the list keep working."""
    fm, _, _ = parse_frontmatter(_write(tmp_path, FRONTMATTER))

    assert fm["name"] == "master-test"
    assert fm["lineage"] == "测试宗"
    assert fm["citation_format"] == "【《{title}》{section}，{cbeta_id}】"


def test_parse_frontmatter_surfaces_a_malformed_source_before_the_last(tmp_path):
    """A source with neither title nor cbeta_id must reach lint_master.

    lint_master flags `sources[i] missing 'title' or 'cbeta_id'`, but only
    ever saw the final entry — a malformed one anywhere earlier was invisible.
    """
    text = FRONTMATTER.replace(
        "  - title: 六祖大师法宝坛经\n    cbeta_id: T48n2008\n    fojin_text_id: 58\n",
        "  - fojin_text_id: 58\n    note: no title and no cbeta_id\n",
    )
    fm, _, _ = parse_frontmatter(_write(tmp_path, text))

    assert len(fm["sources"]) == 3
    bad = fm["sources"][0]
    assert "title" not in bad and "cbeta_id" not in bad


def test_parse_frontmatter_without_frontmatter(tmp_path):
    """A file with no frontmatter yields an empty dict, not a crash."""
    fm, body, _ = parse_frontmatter(_write(tmp_path, "# Just a body\n"))

    assert fm == {}
    assert "Just a body" in body


def test_parse_frontmatter_rejects_invalid_yaml(tmp_path):
    """Malformed frontmatter raises instead of being silently mis-parsed.

    The old parser accepted anything, which let two skills ship a description
    holding a bare `: ` — YAML reads that as a nested mapping and rejects the
    whole block. Clients that parse frontmatter strictly see no frontmatter
    at all, so this must fail loudly here.
    """
    text = "---\nname: master-test\ndescription: keyed on 时序: staged plan\n---\n"
    try:
        parse_frontmatter(_write(tmp_path, text))
    except ValueError as exc:
        assert "invalid YAML frontmatter" in str(exc)
    else:
        raise AssertionError("invalid YAML frontmatter was accepted")


def test_every_prebuilt_skill_has_parseable_frontmatter():
    """Every shipped SKILL.md must parse — this is the case that would have
    caught master-curriculum and master-debate before they shipped."""
    prebuilt = Path(__file__).resolve().parents[2] / "prebuilt"
    skills = sorted(prebuilt.glob("*/SKILL.md"))
    assert skills, f"no SKILL.md found under {prebuilt}"

    for skill in skills:
        fm, _, _ = parse_frontmatter(skill)
        assert fm.get("name"), f"{skill.parent.name}: frontmatter has no name"
