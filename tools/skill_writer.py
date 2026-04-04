"""
Skill Writer — creates and updates teacher skill directories.
Adapted from colleague-skill's skill_writer.py for Buddhist master context.
"""

import json
import os
import shutil
from datetime import datetime
from typing import Optional

try:
    from pypinyin import lazy_pinyin, Style
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False


SKILL_MD_TEMPLATE = """---
name: master_{slug}
description: 依据{name}（{tradition}{school}）的教学风格与教义体系
user-invocable: true
---

# {name}

{disclaimer}

---

## PART A — 教义体系

{teaching_content}

## PART B — 说法风格

{voice_content}

## 运行规则

1. 收到提问后，先依据 voice.md Layer 0 硬规则检查
2. 依据 voice.md Layer 1-3 确定回答的风格和方式
3. 依据 teaching.md 检索相关教义内容
4. 以该法师的风格组织回答
5. 必须附经文出处，格式：【《经名》卷N】→ https://fojin.app/texts/{{text_id}}
6. 遇到超出范围的问题，坦诚说明并建议查阅相关传承
"""

DISCLAIMER = "本内容依据历史佛教文献生成，仅供参考学习。如需正式修行指导，请亲近善知识。所有回答均附经文出处，可通过 FoJin (fojin.app) 查阅原文。"


def slugify(name: str) -> str:
    """Convert teacher name to URL-safe slug."""
    if HAS_PYPINYIN:
        pinyin_list = lazy_pinyin(name, style=Style.NORMAL)
        slug = "-".join(pinyin_list)
    else:
        slug = name.lower().replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    slug = slug.strip("-")
    return slug


def create_teacher(
    base_dir: str,
    name: str,
    tradition: str,
    school: str,
    era: str,
    languages: list,
    teaching_content: str,
    voice_content: str,
    fojin_entity_id: Optional[str] = None,
    sources: Optional[list] = None,
) -> str:
    """Create a new teacher skill directory."""
    slug = slugify(name)
    teacher_dir = os.path.join(base_dir, slug)
    os.makedirs(teacher_dir, exist_ok=True)
    os.makedirs(os.path.join(teacher_dir, "versions"), exist_ok=True)

    with open(os.path.join(teacher_dir, "teaching.md"), "w", encoding="utf-8") as f:
        f.write(teaching_content)

    with open(os.path.join(teacher_dir, "voice.md"), "w", encoding="utf-8") as f:
        f.write(voice_content)

    skill_content = SKILL_MD_TEMPLATE.format(
        slug=slug, name=name, tradition=tradition, school=school,
        disclaimer=DISCLAIMER, teaching_content=teaching_content,
        voice_content=voice_content,
    )
    with open(os.path.join(teacher_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(skill_content)

    meta = {
        "name": name, "slug": slug, "tradition": tradition, "school": school,
        "era": era, "languages": languages, "fojin_entity_id": fojin_entity_id,
        "sources": sources or [], "version": "1.0.0",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "updated_at": datetime.now().strftime("%Y-%m-%d"),
        "disclaimer": DISCLAIMER,
    }
    with open(os.path.join(teacher_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return teacher_dir


def update_teacher(teacher_dir: str, teaching_patch: Optional[str] = None, voice_patch: Optional[str] = None) -> str:
    """Update an existing teacher skill with new content. Archives current version before updating."""
    meta_path = os.path.join(teacher_dir, "meta.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    version = meta.get("version", "1.0.0")
    version_dir = os.path.join(teacher_dir, "versions", f"v{version}")
    os.makedirs(version_dir, exist_ok=True)
    for fname in ["SKILL.md", "teaching.md", "voice.md", "meta.json"]:
        src = os.path.join(teacher_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, version_dir)

    if teaching_patch:
        with open(os.path.join(teacher_dir, "teaching.md"), "a", encoding="utf-8") as f:
            f.write("\n\n" + teaching_patch)

    if voice_patch:
        with open(os.path.join(teacher_dir, "voice.md"), "a", encoding="utf-8") as f:
            f.write("\n\n" + voice_patch)

    parts = version.split(".")
    parts[1] = str(int(parts[1]) + 1)
    new_version = ".".join(parts)

    meta["version"] = new_version
    meta["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    teaching_content = open(os.path.join(teacher_dir, "teaching.md"), encoding="utf-8").read()
    voice_content = open(os.path.join(teacher_dir, "voice.md"), encoding="utf-8").read()
    skill_content = SKILL_MD_TEMPLATE.format(
        slug=meta["slug"], name=meta["name"], tradition=meta["tradition"],
        school=meta["school"], disclaimer=DISCLAIMER,
        teaching_content=teaching_content, voice_content=voice_content,
    )
    with open(os.path.join(teacher_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(skill_content)

    return new_version


def list_teachers(base_dir: str) -> list:
    """List all teacher skills in a directory."""
    teachers = []
    if not os.path.exists(base_dir):
        return teachers
    for entry in sorted(os.listdir(base_dir)):
        meta_path = os.path.join(base_dir, entry, "meta.json")
        if os.path.isfile(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            teachers.append(meta)
    return teachers
