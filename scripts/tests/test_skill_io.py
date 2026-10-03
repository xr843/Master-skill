"""Characterization tests for scripts/_skill_io.py.

The expected values below were recorded, before the switch, from the readers
this module replaced: validate.py's line-fenced parser and the
`text.split("---", 2)` reader in validate-self-audit-sources.py (the same
semantics tools/verify_sources.py keeps its own copy of, since tools/ ships
without scripts/). The two readers disagree on malformed input; these cases
pin each one, so a later "unification" has to change a test to change a gate.
"""
import json

import pytest
import yaml

import _skill_io as io

EDGE = {
    "normal": "---\nname: a\nsources:\n  - cbeta_id: T1\n---\nbody\n",
    "none": "# body only\n",
    "leading_blank": "\n---\nname: a\n---\nbody\n",
    "leading_spaces": "  ---\nname: a\n---\nbody\n",
    "unclosed": "---\nname: a\nbody\n",
    "dash_in_value": "---\nname: a---b\ndescription: x\n---\nbody\n",
    "closing_trailing_space": "---\nname: a\n--- \nbody\n",
    "four_dashes": "----\nname: a\n---\nbody\n",
    "empty": "---\n---\nbody\n",
    "crlf": "---\r\nname: a\r\n---\r\nbody\r\n",
    "nonmapping": "---\n- a\n- b\n---\nbody\n",
    "invalid_yaml": "---\nname: [x\n---\nbody\n",
    "bom": "﻿---\nname: a\n---\nbody\n",
    "hr_in_body": "---\nname: a\n---\nbody\n---\nmore\n",
}

# split-based reader: raw block (None = no block).
SPLIT_RAW = {
    "normal": "\nname: a\nsources:\n  - cbeta_id: T1\n",
    "none": None,
    "leading_blank": "\nname: a\n",
    "leading_spaces": "\nname: a\n",
    "unclosed": None,
    "dash_in_value": "\nname: a",
    "closing_trailing_space": "\nname: a\n",
    "four_dashes": "-\nname: a\n",
    "empty": "\n",
    "crlf": "\r\nname: a\r\n",
    "nonmapping": "\n- a\n- b\n",
    "invalid_yaml": "\nname: [x\n",
    "bom": None,
    "hr_in_body": "\nname: a\n",
}

# split-based reader, parsed. An exception class means yaml raises it.
SPLIT_LOADED = {
    "normal": {"name": "a", "sources": [{"cbeta_id": "T1"}]},
    "none": {},
    "leading_blank": {"name": "a"},
    "leading_spaces": {"name": "a"},
    "unclosed": {},
    "dash_in_value": {"name": "a"},
    "closing_trailing_space": {"name": "a"},
    "four_dashes": yaml.YAMLError,
    "empty": {},
    "crlf": {"name": "a"},
    "nonmapping": ["a", "b"],
    "invalid_yaml": yaml.YAMLError,
    "bom": {},
    "hr_in_body": {"name": "a"},
}

# line-fenced reader: (mapping, body, number of lines), or the ValueError text.
LINES = {
    "normal": ({"name": "a", "sources": [{"cbeta_id": "T1"}]}, "body", 6),
    "none": ({}, "# body only\n", 1),
    "leading_blank": ({}, "\n---\nname: a\n---\nbody\n", 5),
    "leading_spaces": ({"name": "a"}, "body", 4),
    "unclosed": ({}, "---\nname: a\nbody\n", 3),
    "dash_in_value": ({"name": "a---b", "description": "x"}, "body", 5),
    "closing_trailing_space": ({"name": "a"}, "body", 4),
    "four_dashes": ({}, "----\nname: a\n---\nbody\n", 4),
    "empty": ({}, "body", 3),
    "crlf": ({"name": "a"}, "body", 4),
    "nonmapping": "X.md: frontmatter is not a mapping",
    "invalid_yaml": "X.md: invalid YAML frontmatter — ",
    "bom": ({}, "﻿---\nname: a\n---\nbody\n", 4),
    "hr_in_body": ({"name": "a"}, "body\n---\nmore", 6),
}


@pytest.mark.parametrize("case", sorted(EDGE))
def test_split_frontmatter(case):
    assert io.split_frontmatter(EDGE[case]) == SPLIT_RAW[case]


@pytest.mark.parametrize("case", sorted(EDGE))
def test_load_frontmatter(case):
    expected = SPLIT_LOADED[case]
    if isinstance(expected, type):
        with pytest.raises(expected):
            io.load_frontmatter(EDGE[case])
    else:
        assert io.load_frontmatter(EDGE[case]) == expected


@pytest.mark.parametrize("case", sorted(EDGE))
def test_parse_frontmatter_lines(case):
    expected = LINES[case]
    if isinstance(expected, str):
        with pytest.raises(ValueError) as err:
            io.parse_frontmatter_lines(EDGE[case], "X.md")
        assert str(err.value).startswith(expected)
    else:
        fm, body, lines = io.parse_frontmatter_lines(EDGE[case], "X.md")
        assert (fm, body, len(lines)) == expected


@pytest.mark.parametrize("skill", sorted(io.PREBUILT_DIR.glob("*/SKILL.md")), ids=lambda p: p.parent.name)
def test_both_readers_agree_on_every_prebuilt_skill(skill):
    text = skill.read_text(encoding="utf-8")
    fm, _, _ = io.parse_frontmatter_lines(text, skill)
    assert fm and fm == io.load_frontmatter(text)


def test_paths():
    assert (io.ROOT / "package.json").is_file()
    assert io.SCRIPTS_DIR == io.ROOT / "scripts"
    assert io.PREBUILT_DIR == io.ROOT / "prebuilt"


def test_parse_sections():
    text = "preamble\n## 一\nbody 1\n## 二\n## 三 \nlast"
    assert io.parse_sections(text) == [("一", "body 1\n"), ("二", ""), ("三", "last")]


def test_load_fixtures(tmp_path):
    (tmp_path / "m-a" / "tests").mkdir(parents=True)
    (tmp_path / "m-a" / "tests" / "fidelity.jsonl").write_text('{"q": 1}\n\n{"q": 2}\n')
    (tmp_path / "m-b").mkdir()
    assert io.load_fixtures(tmp_path) == {"m-a": [{"q": 1}, {"q": 2}]}
    real = io.load_fixtures()
    assert real and all(cases for cases in real.values())


def test_try_read_json(tmp_path):
    good = tmp_path / "g.json"
    good.write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert io.try_read_json(good) == ({"a": 1}, None)
    bad = tmp_path / "b.json"
    bad.write_text("{oops", encoding="utf-8")
    data, err = io.try_read_json(bad)
    assert data is None and isinstance(err, json.JSONDecodeError)
    data, err = io.try_read_json(tmp_path / "missing.json")
    assert data is None and isinstance(err, OSError)
