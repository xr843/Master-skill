"""Tests for validate-promptfoo-configs.py.

Exercises the persona-test config validator on synthetic prebuilt/ trees so
the production tests/persona/ files don't get coupled to the unit tests.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import textwrap
from pathlib import Path

import pytest


def _load_module():
    spec_path = Path(__file__).resolve().parents[1] / "validate-promptfoo-configs.py"
    spec = importlib.util.spec_from_file_location("vppc", spec_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["vppc"] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_master(tmp_root: Path, slug: str, *, signature_phrases=None) -> None:
    """Create a minimal prebuilt/master-<slug>/meta.json under tmp_root."""
    if signature_phrases is None:
        signature_phrases = ["本来无一物", "明心见性", "不立文字", "无念为宗"]
    d = tmp_root / "prebuilt" / f"master-{slug}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.json").write_text(
        json.dumps(
            {
                "slug": slug,
                "signature_phrases": signature_phrases,
                "style": {
                    "all": "x" * 40,
                    "qa": "x" * 40,
                    "monologue": "x" * 40,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _persona_dir(tmp_root: Path) -> Path:
    d = tmp_root / "tests" / "persona"
    d.mkdir(parents=True, exist_ok=True)
    return d


SHARED_YAML_HUINENG = textwrap.dedent(
    """\
    huineng_persona_prompt: |
      你扮演中国禅宗六祖慧能大师。请回答用户提问。

      用户问题：{{question}}
    """
)

VALID_CONFIG_BODY = textwrap.dedent(
    """\
    description: "master-huineng persona fidelity — RAW/SPE/CUS"
    providers:
      - id: anthropic:messages:claude-opus-4-7
    defaultTest:
      options:
        provider:
          id: anthropic:messages:claude-opus-4-7
    prompts:
      - |
        你扮演中国禅宗六祖慧能大师。请回答用户提问。

        用户问题：{{question}}
    tests:
      - description: "RAW: 拒答政治"
        vars:
          question: "当代政治怎么看？"
        assert:
          - type: llm-rubric
            value: "回答应礼貌拒绝评论当代政治议题并引回禅宗本怀。"
      - description: "SPE: 顿渐之辨"
        vars:
          question: "请讲顿悟和渐修。"
        assert:
          - type: llm-rubric
            value: "回答应包含南宗禅核心概念并立顿教立场。"
          - type: contains-any
            value:
              - 本来无一物
              - 明心见性
      - description: "SPE: 风幡公案"
        vars:
          question: "风动幡动是什么？"
        assert:
          - type: llm-rubric
            value: "回答应正确叙述风幡公案要旨：非风动非幡动仁者心动。"
      - description: "CUS: 短句直指"
        vars:
          question: "学人初参请师指示。"
        assert:
          - type: llm-rubric
            value: "回答应符合慧能短句直指答疑风格。"
          - type: contains-any
            value:
              - 不立文字
              - 无念为宗
    """
)


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

def test_valid_config_passes(tmp_path, monkeypatch):
    mod = _load_module()
    _write_master(tmp_path, "huineng")
    persona = _persona_dir(tmp_path)
    (persona / "shared.yaml").write_text(SHARED_YAML_HUINENG, encoding="utf-8")
    (persona / "huineng.promptfooconfig.yaml").write_text(
        VALID_CONFIG_BODY, encoding="utf-8"
    )
    monkeypatch.setattr(mod, "PREBUILT_DIR", tmp_path / "prebuilt")
    errors = mod.validate(persona)
    assert errors == [], errors


def test_missing_shared_yaml_is_error(tmp_path, monkeypatch):
    mod = _load_module()
    _write_master(tmp_path, "huineng")
    persona = _persona_dir(tmp_path)
    (persona / "huineng.promptfooconfig.yaml").write_text(
        VALID_CONFIG_BODY, encoding="utf-8"
    )
    monkeypatch.setattr(mod, "PREBUILT_DIR", tmp_path / "prebuilt")
    errors = mod.validate(persona)
    assert any("shared.yaml" in e for e in errors), errors


def test_no_configs_is_error(tmp_path, monkeypatch):
    mod = _load_module()
    persona = _persona_dir(tmp_path)
    (persona / "shared.yaml").write_text(SHARED_YAML_HUINENG, encoding="utf-8")
    monkeypatch.setattr(mod, "PREBUILT_DIR", tmp_path / "prebuilt")
    errors = mod.validate(persona)
    assert any("no *.promptfooconfig.yaml" in e for e in errors), errors


def test_bad_filename_extension(tmp_path, monkeypatch):
    mod = _load_module()
    _write_master(tmp_path, "huineng")
    persona = _persona_dir(tmp_path)
    (persona / "shared.yaml").write_text(SHARED_YAML_HUINENG, encoding="utf-8")
    # wrong suffix: this file won't even be picked up by the glob, so we
    # instead drop a valid-suffix file but rely on the slug check.
    (persona / "huineng.promptfooconfig.yaml").write_text(
        VALID_CONFIG_BODY, encoding="utf-8"
    )
    (persona / "NoSuchMaster.promptfooconfig.yaml").write_text(
        VALID_CONFIG_BODY, encoding="utf-8"
    )
    monkeypatch.setattr(mod, "PREBUILT_DIR", tmp_path / "prebuilt")
    errors = mod.validate(persona)
    assert any("NoSuchMaster" in e for e in errors), errors


def test_slug_with_no_master_dir(tmp_path, monkeypatch):
    mod = _load_module()
    persona = _persona_dir(tmp_path)
    (persona / "shared.yaml").write_text(SHARED_YAML_HUINENG, encoding="utf-8")
    (persona / "ghostmaster.promptfooconfig.yaml").write_text(
        VALID_CONFIG_BODY, encoding="utf-8"
    )
    # Create at least one prebuilt dir so it exists
    (tmp_path / "prebuilt").mkdir()
    monkeypatch.setattr(mod, "PREBUILT_DIR", tmp_path / "prebuilt")
    errors = mod.validate(persona)
    assert any("ghostmaster" in e and "no matching master" in e for e in errors), errors


def test_dimension_coverage_required(tmp_path, monkeypatch):
    mod = _load_module()
    _write_master(tmp_path, "huineng")
    persona = _persona_dir(tmp_path)
    (persona / "shared.yaml").write_text(SHARED_YAML_HUINENG, encoding="utf-8")
    body = textwrap.dedent(
        """\
        description: x
        providers:
          - id: anthropic:messages:claude-opus-4-7
        defaultTest:
          options:
            provider:
              id: anthropic:messages:claude-opus-4-7
        prompts:
          - |
            你扮演中国禅宗六祖慧能大师。请回答用户提问。

            用户问题：{{question}}
        tests:
          - description: "RAW: a"
            vars: {question: q1}
            assert:
              - type: llm-rubric
                value: "this rubric is long enough to satisfy minimum char check."
          - description: "RAW: b"
            vars: {question: q2}
            assert:
              - type: llm-rubric
                value: "this rubric is long enough to satisfy minimum char check."
          - description: "RAW: c"
            vars: {question: q3}
            assert:
              - type: llm-rubric
                value: "this rubric is long enough to satisfy minimum char check."
          - description: "RAW: d"
            vars: {question: q4}
            assert:
              - type: llm-rubric
                value: "this rubric is long enough to satisfy minimum char check."
        """
    )
    (persona / "huineng.promptfooconfig.yaml").write_text(body, encoding="utf-8")
    monkeypatch.setattr(mod, "PREBUILT_DIR", tmp_path / "prebuilt")
    errors = mod.validate(persona)
    assert any("missing dimension 'SPE'" in e for e in errors), errors
    assert any("missing dimension 'CUS'" in e for e in errors), errors


def test_too_few_tests(tmp_path, monkeypatch):
    mod = _load_module()
    _write_master(tmp_path, "huineng")
    persona = _persona_dir(tmp_path)
    (persona / "shared.yaml").write_text(SHARED_YAML_HUINENG, encoding="utf-8")
    body = textwrap.dedent(
        """\
        description: x
        providers:
          - id: anthropic:messages:claude-opus-4-7
        defaultTest:
          options:
            provider:
              id: anthropic:messages:claude-opus-4-7
        prompts:
          - |
            你扮演中国禅宗六祖慧能大师。请回答用户提问。

            用户问题：{{question}}
        tests:
          - description: "RAW: a"
            vars: {question: q1}
            assert:
              - type: llm-rubric
                value: "long enough rubric to clear the floor on chars."
          - description: "SPE: b"
            vars: {question: q2}
            assert:
              - type: llm-rubric
                value: "long enough rubric to clear the floor on chars."
          - description: "CUS: c"
            vars: {question: q3}
            assert:
              - type: llm-rubric
                value: "long enough rubric to clear the floor on chars."
        """
    )
    (persona / "huineng.promptfooconfig.yaml").write_text(body, encoding="utf-8")
    monkeypatch.setattr(mod, "PREBUILT_DIR", tmp_path / "prebuilt")
    errors = mod.validate(persona)
    assert any("at least 4 tests required" in e for e in errors), errors


def test_unknown_dimension_prefix_rejected(tmp_path, monkeypatch):
    mod = _load_module()
    _write_master(tmp_path, "huineng")
    persona = _persona_dir(tmp_path)
    (persona / "shared.yaml").write_text(SHARED_YAML_HUINENG, encoding="utf-8")
    bad = VALID_CONFIG_BODY.replace("RAW: 拒答政治", "XXX: bogus prefix")
    (persona / "huineng.promptfooconfig.yaml").write_text(bad, encoding="utf-8")
    monkeypatch.setattr(mod, "PREBUILT_DIR", tmp_path / "prebuilt")
    errors = mod.validate(persona)
    assert any("must start with one of" in e for e in errors), errors


def test_missing_llm_rubric_rejected(tmp_path, monkeypatch):
    mod = _load_module()
    _write_master(tmp_path, "huineng")
    persona = _persona_dir(tmp_path)
    (persona / "shared.yaml").write_text(SHARED_YAML_HUINENG, encoding="utf-8")
    # Strip every llm-rubric block by replacing the type. Use textwrap.dedent
    # only on the snippet so indentation matches what VALID_CONFIG_BODY has.
    body = VALID_CONFIG_BODY.replace("type: llm-rubric", "type: contains")
    (persona / "huineng.promptfooconfig.yaml").write_text(body, encoding="utf-8")
    monkeypatch.setattr(mod, "PREBUILT_DIR", tmp_path / "prebuilt")
    errors = mod.validate(persona)
    assert any("must have at least one llm-rubric" in e for e in errors), errors


def test_contains_any_value_must_be_anchor(tmp_path, monkeypatch):
    mod = _load_module()
    _write_master(tmp_path, "huineng", signature_phrases=["本来无一物"])
    persona = _persona_dir(tmp_path)
    (persona / "shared.yaml").write_text(SHARED_YAML_HUINENG, encoding="utf-8")
    body = VALID_CONFIG_BODY.replace(
        "- 本来无一物\n              - 明心见性",
        "- 完全不存在的短语\n              - 另一个伪造短语",
    )
    (persona / "huineng.promptfooconfig.yaml").write_text(body, encoding="utf-8")
    monkeypatch.setattr(mod, "PREBUILT_DIR", tmp_path / "prebuilt")
    errors = mod.validate(persona)
    assert any("not in huineng's fidelity anchors" in e for e in errors), errors


def test_prompt_must_match_shared(tmp_path, monkeypatch):
    mod = _load_module()
    _write_master(tmp_path, "huineng")
    persona = _persona_dir(tmp_path)
    (persona / "shared.yaml").write_text(SHARED_YAML_HUINENG, encoding="utf-8")
    bad = VALID_CONFIG_BODY.replace(
        "你扮演中国禅宗六祖慧能大师。请回答用户提问。",
        "你是某个完全不同的角色。",
    )
    (persona / "huineng.promptfooconfig.yaml").write_text(bad, encoding="utf-8")
    monkeypatch.setattr(mod, "PREBUILT_DIR", tmp_path / "prebuilt")
    errors = mod.validate(persona)
    assert any("does not match shared.yaml" in e for e in errors), errors


def test_judge_provider_required(tmp_path, monkeypatch):
    mod = _load_module()
    _write_master(tmp_path, "huineng")
    persona = _persona_dir(tmp_path)
    (persona / "shared.yaml").write_text(SHARED_YAML_HUINENG, encoding="utf-8")
    body = VALID_CONFIG_BODY.replace(
        "defaultTest:\n  options:\n    provider:\n      id: anthropic:messages:claude-opus-4-7\n",
        "",
    )
    (persona / "huineng.promptfooconfig.yaml").write_text(body, encoding="utf-8")
    monkeypatch.setattr(mod, "PREBUILT_DIR", tmp_path / "prebuilt")
    errors = mod.validate(persona)
    assert any("defaultTest.options.provider" in e for e in errors), errors


def test_prompt_missing_question_var_rejected(tmp_path, monkeypatch):
    """A prompt that doesn't reference {{question}} silently no-ops every
    test case — must be flagged. Also serves as a regression guard against
    contributors stripping the var when copying templates."""
    mod = _load_module()
    _write_master(tmp_path, "huineng")
    persona = _persona_dir(tmp_path)
    # Both shared.yaml and the inlined prompt must agree (so the sync check
    # passes), and neither references {{question}} (so the new check fires).
    shared_no_var = textwrap.dedent(
        """\
        huineng_persona_prompt: |
          你扮演中国禅宗六祖慧能大师。请回答用户提问。

          这里故意未引用问题变量。
        """
    )
    (persona / "shared.yaml").write_text(shared_no_var, encoding="utf-8")
    body = VALID_CONFIG_BODY.replace(
        "用户问题：{{question}}",
        "这里故意未引用问题变量。",
    )
    (persona / "huineng.promptfooconfig.yaml").write_text(body, encoding="utf-8")
    monkeypatch.setattr(mod, "PREBUILT_DIR", tmp_path / "prebuilt")
    errors = mod.validate(persona)
    assert any("does not reference" in e and "question" in e for e in errors), errors


def test_unknown_slug_not_in_shared_key_map(tmp_path, monkeypatch):
    mod = _load_module()
    _write_master(tmp_path, "milarepa")  # real prebuilt but not in SHARED_KEY_MAP
    persona = _persona_dir(tmp_path)
    (persona / "shared.yaml").write_text(SHARED_YAML_HUINENG, encoding="utf-8")
    (persona / "milarepa.promptfooconfig.yaml").write_text(
        VALID_CONFIG_BODY, encoding="utf-8"
    )
    monkeypatch.setattr(mod, "PREBUILT_DIR", tmp_path / "prebuilt")
    errors = mod.validate(persona)
    assert any("SHARED_KEY_MAP" in e for e in errors), errors
