"""Tests for skill_writer.py — uses tmp_path fixture."""

import json
import os
import pytest
from skill_writer import slugify, create_teacher, list_teachers, update_teacher, DISCLAIMER


def test_slugify_english():
    # With pypinyin installed, English chars are passed through as-is (no lowercasing);
    # without pypinyin the fallback lowercases. Either result must be alphanumeric+hyphen.
    result = slugify("Hello World")
    assert all(c.isalnum() or c == "-" for c in result)
    assert len(result) > 0


def test_slugify_chinese():
    # Should use pypinyin if available, otherwise lowercase fallback
    result = slugify("印光大师")
    assert "-" in result or result.isalnum()
    assert result.islower()


def test_slugify_strips_punctuation():
    # Punctuation is removed; case depends on pypinyin presence
    result = slugify("Master!@#$")
    assert all(c.isalnum() or c == "-" for c in result)
    assert "master" in result.lower()


def test_create_teacher_writes_files(tmp_path):
    teacher_dir = create_teacher(
        base_dir=str(tmp_path),
        name="测试法师",
        tradition="汉传",
        school="测试宗",
        era="1900-2000",
        languages=["zh"],
        teaching_content="# 教义\n测试教义内容",
        voice_content="# 风格\n测试风格内容",
    )
    assert os.path.exists(os.path.join(teacher_dir, "teaching.md"))
    assert os.path.exists(os.path.join(teacher_dir, "voice.md"))
    assert os.path.exists(os.path.join(teacher_dir, "SKILL.md"))
    assert os.path.exists(os.path.join(teacher_dir, "meta.json"))
    assert os.path.exists(os.path.join(teacher_dir, "versions"))


def test_create_teacher_meta_content(tmp_path):
    teacher_dir = create_teacher(
        base_dir=str(tmp_path),
        name="测试法师",
        tradition="汉传",
        school="测试宗",
        era="1900-2000",
        languages=["zh"],
        teaching_content="教义",
        voice_content="风格",
        sources=[{"type": "cbeta", "id": "T01n0001"}],
    )
    with open(os.path.join(teacher_dir, "meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["name"] == "测试法师"
    assert meta["tradition"] == "汉传"
    assert meta["version"] == "1.0.0"
    assert meta["disclaimer"] == DISCLAIMER
    assert len(meta["sources"]) == 1


def test_create_teacher_skill_md_includes_content(tmp_path):
    teacher_dir = create_teacher(
        base_dir=str(tmp_path),
        name="测试法师",
        tradition="汉传",
        school="测试宗",
        era="1900-2000",
        languages=["zh"],
        teaching_content="UNIQUE_TEACHING_MARKER",
        voice_content="UNIQUE_VOICE_MARKER",
    )
    with open(os.path.join(teacher_dir, "SKILL.md"), encoding="utf-8") as f:
        content = f.read()
    assert "UNIQUE_TEACHING_MARKER" in content
    assert "UNIQUE_VOICE_MARKER" in content
    assert "master_" in content  # frontmatter


def test_list_teachers_empty(tmp_path):
    assert list_teachers(str(tmp_path)) == []


def test_list_teachers_finds_created(tmp_path):
    create_teacher(
        base_dir=str(tmp_path),
        name="法师一", tradition="汉传", school="宗A",
        era="1900", languages=["zh"],
        teaching_content="a", voice_content="b",
    )
    create_teacher(
        base_dir=str(tmp_path),
        name="法师二", tradition="汉传", school="宗B",
        era="1950", languages=["zh"],
        teaching_content="a", voice_content="b",
    )
    teachers = list_teachers(str(tmp_path))
    assert len(teachers) == 2
    names = {t["name"] for t in teachers}
    assert names == {"法师一", "法师二"}


def test_update_teacher_bumps_version(tmp_path):
    teacher_dir = create_teacher(
        base_dir=str(tmp_path),
        name="测试", tradition="汉传", school="宗",
        era="1900", languages=["zh"],
        teaching_content="原教义", voice_content="原风格",
    )
    new_version = update_teacher(teacher_dir, teaching_patch="补充教义")
    assert new_version == "1.1.0"
    with open(os.path.join(teacher_dir, "teaching.md"), encoding="utf-8") as f:
        content = f.read()
    assert "原教义" in content
    assert "补充教义" in content


def test_update_teacher_archives_version(tmp_path):
    teacher_dir = create_teacher(
        base_dir=str(tmp_path),
        name="测试", tradition="汉传", school="宗",
        era="1900", languages=["zh"],
        teaching_content="v1", voice_content="v1",
    )
    update_teacher(teacher_dir, teaching_patch="update")
    assert os.path.exists(os.path.join(teacher_dir, "versions", "v1.0.0"))
