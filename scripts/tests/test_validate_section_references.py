"""Tests for the section-reference gate.

A persona's decision tree says 读 `references/teaching.md` §参话头 and the model
does exactly that. 2026-09-16: 18 of 198 such pointers named a section the file
does not have. The sharpest was master-milarepa sending 那洛六法 / 拙火 questions
to `sources/grubum-excerpts.md` §拙火与气脉 — a file that omits tummo on purpose
and says so under ⚠️ 本目录不收录之内容.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate-section-references.py"


@pytest.fixture
def gate():
    spec = importlib.util.spec_from_file_location("validate_section_references", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GRUBUM = [
    "## §大手印见地（明空双运 · 心性本来）",
    "## ⚠️ 本目录不收录之内容",
    "- 拙火（tummo）具体修法步骤、姿势、宝瓶气、明点运行",
]


def test_a_heading_counts(gate):
    assert gate.section_present("大手印见地", GRUBUM)


def test_a_bold_label_counts(gate):
    """master-yinguang 的 **十念法** 是段内标签，不是标题 —— 模型一样搜得到。"""
    assert gate.section_present("十念法", ["## 修行方法", "**十念法**：每日晨起，面西合掌"])


def test_a_gloss_is_optional_on_either_side(gate):
    heading = ["### 6. 觉受 (nyams) 与证悟 (rtogs pa) 的区分"]
    assert gate.section_present("觉受与证悟", heading)
    assert gate.section_present("正念与觉知", ["## §正念（Sati）与觉知"])
    assert gate.section_present("妄念多", ["## §对治散乱（妄念多怎么办）"])


def test_trailing_prose_is_dropped_but_the_first_word_must_match(gate):
    lines = ["## 版权分级（运行时简表）"]
    assert gate.section_present("版权分级 Tier B/C 流程", lines)
    assert not gate.section_present("版权流程 Tier B/C", lines)


def test_the_milarepa_pointer_is_reported(gate):
    """门禁必须能红 —— 这正是 2026-09-16 米拉日巴那条的形状。"""
    assert not gate.section_present("拙火与气脉", GRUBUM)


def test_a_rename_is_reported(gate):
    assert not gate.section_present("戒律根本", ["### 4. 戒律为根本（三聚戒清净持守）"])


def test_sections_joined_by_a_dunhao_are_each_parsed(gate):
    line = "  → 读 `sources/mohezhiguan-excerpts.md` §圆顿止观开篇、§二十五方便 + 必要时 `references/teaching.md` §修行方法"
    assert gate.references(line) == [
        ("sources/mohezhiguan-excerpts.md", ["圆顿止观开篇", "二十五方便"]),
        ("references/teaching.md", ["修行方法"]),
    ]


def test_a_name_ends_at_a_table_pipe_or_gloss(gate):
    assert gate.references("| 怎么参话头 | `references/teaching.md` §参话头 | 《虚云老和尚开示录》 |") == [
        ("references/teaching.md", ["参话头"])
    ]
    assert gate.references("读 `references/teaching.md` §那洛六法（只有名义与历史）；") == [
        ("references/teaching.md", ["那洛六法"])
    ]


def _repo(tmp_path, gate, monkeypatch, skill_md: str, files: dict[str, str]):
    master = tmp_path / "prebuilt" / "master-x"
    for rel, text in {"SKILL.md": skill_md, **files}.items():
        (master / rel).parent.mkdir(parents=True, exist_ok=True)
        (master / rel).write_text(text, encoding="utf-8")
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    return [master / "SKILL.md"]


def test_a_missing_file_is_reported(gate, tmp_path, monkeypatch):
    docs = _repo(tmp_path, gate, monkeypatch, "读 `sources/gone.md`\n", {})
    examined, problems = gate.dangling(docs)
    assert examined == 1
    assert problems == ["prebuilt/master-x/SKILL.md:1  `sources/gone.md` does not exist"]


def test_a_missing_section_is_reported_with_its_location(gate, tmp_path, monkeypatch):
    docs = _repo(
        tmp_path, gate, monkeypatch,
        "# x\n  → 读 `sources/grubum-excerpts.md` §拙火与气脉\n",
        {"sources/grubum-excerpts.md": "\n".join(GRUBUM)},
    )
    assert gate.dangling(docs) == (
        1, ["prebuilt/master-x/SKILL.md:2  `sources/grubum-excerpts.md` has no section §拙火与气脉"]
    )


def test_a_bare_filename_without_a_section_is_prose(gate, tmp_path, monkeypatch):
    """生成器文档写「生成 `teaching.md`」—— 那是产物名，不是指针。"""
    docs = _repo(tmp_path, gate, monkeypatch, "`prompts/teaching_builder.md` 生成 `teaching.md`\n",
                 {"prompts/teaching_builder.md": "# builder"})
    assert gate.dangling(docs) == (1, [])


def test_a_template_line_is_skipped(gate, tmp_path, monkeypatch):
    docs = _repo(tmp_path, gate, monkeypatch, "加载 `prebuilt/{slug}/meta.json`、`references/teaching.md`\n", {})
    assert gate.dangling(docs) == (0, [])


def test_an_empty_set_fails_instead_of_passing(gate, monkeypatch, capsys):
    """检查了空集合的门禁不能报绿。"""
    monkeypatch.setattr(gate, "model_facing_docs", lambda: [])
    assert gate.main() == 1
    assert "examined an empty set" in capsys.readouterr().out


def test_the_real_repo_passes(gate):
    examined, problems = gate.dangling(gate.model_facing_docs())
    assert examined >= 250, "指针条数骤降，先查解析器"
    assert problems == []
