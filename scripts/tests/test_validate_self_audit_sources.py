"""Tests for the self-audit sources gate.

Nine personas tell the model to strip any citation whose identifier is not in
the SKILL.md frontmatter `sources:` list. master-ouyi's list omitted
《灵峰宗论》 `J36nB348`, which its meta.json declares and its references cite.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate-self-audit-sources.py"

RULE = "   - 离线引文：该标识必须 ∈ 本 master frontmatter `sources:` 声明的对应字段；\n"


@pytest.fixture
def gate():
    spec = importlib.util.spec_from_file_location("validate_self_audit_sources", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_self_audit_sources"] = module
    spec.loader.exec_module(module)
    return module


def _persona(root: Path, frontmatter_sources: str, meta_sources: list[dict], *, rule: bool = True) -> Path:
    persona = root / "master-example"
    persona.mkdir(parents=True)
    body = RULE if rule else "   - 离线引文：该标识必须 ∈ meta.json 的 sources[]；\n"
    (persona / "SKILL.md").write_text(
        f"---\nname: master-example\nsources:\n{frontmatter_sources}---\n\n{body}",
        encoding="utf-8",
    )
    (persona / "meta.json").write_text(
        json.dumps({"sources": meta_sources}, ensure_ascii=False), encoding="utf-8"
    )
    return persona


def test_a_declared_source_missing_from_the_self_audit_list_is_named(gate, tmp_path):
    persona = _persona(
        tmp_path,
        "  - title: 阿彌陀經要解\n    cbeta_id: T37n1762\n",
        [{"type": "cbeta", "id": "T37n1762", "title": "阿弥陀经要解"},
         {"type": "cbeta", "id": "J36nB348", "title": "灵峰宗论"}],
    )
    problems, examined = gate.check_persona(persona)
    assert examined is True
    assert len(problems) == 1 and "J36nB348" in problems[0]


def test_a_short_form_frontmatter_id_covers_the_declared_full_id(gate, tmp_path):
    persona = _persona(
        tmp_path,
        "  - title: 妙法蓮華經玄義\n    cbeta_id: T1716\n",
        [{"type": "cbeta", "id": "T33n1716", "title": "妙法莲华经玄义"}],
    )
    assert gate.check_persona(persona) == ([], True)


def test_a_teaching_id_covers_a_compiled_teaching_source(gate, tmp_path):
    persona = _persona(
        tmp_path,
        "  - title: 印光法師文鈔正編\n    teaching_id: Yinguang:WenchaoZhengbian\n",
        [{"type": "compiled_teaching", "id": "Yinguang:WenchaoZhengbian", "title": "t"}],
    )
    assert gate.check_persona(persona) == ([], True)


def test_a_persona_whose_rule_reads_meta_json_is_not_examined(gate, tmp_path):
    persona = _persona(
        tmp_path, "  - title: x\n    cbeta_id: T37n1762\n",
        [{"type": "cbeta", "id": "J36nB348", "title": "灵峰宗论"}], rule=False,
    )
    assert gate.check_persona(persona) == ([], False)


def test_a_tree_where_no_persona_uses_the_rule_fails(gate, tmp_path):
    _persona(tmp_path, "  - title: x\n    cbeta_id: T37n1762\n", [], rule=False)
    assert gate.main(tmp_path) == 1


def test_the_real_repo_passes_and_examines_master_ouyi(gate):
    assert gate.main(ROOT / "prebuilt") == 0
    problems, examined = gate.check_persona(ROOT / "prebuilt" / "master-ouyi")
    assert examined is True and problems == []
