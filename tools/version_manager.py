"""
Version Manager — archives and rolls back teacher skill versions.
Adapted from colleague-skill's version_manager.py.
"""

import json
import os
import shutil
from datetime import datetime

MAX_VERSIONS = 10


def list_versions(teacher_dir: str) -> list:
    """List all archived versions of a teacher skill."""
    versions_dir = os.path.join(teacher_dir, "versions")
    if not os.path.exists(versions_dir):
        return []

    versions = []
    for entry in sorted(os.listdir(versions_dir)):
        entry_path = os.path.join(versions_dir, entry)
        if os.path.isdir(entry_path) and entry.startswith("v"):
            files = os.listdir(entry_path)
            mtime = os.path.getmtime(entry_path)
            versions.append({
                "version": entry[1:],
                "archived_at": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                "files": files,
            })
    return versions


def rollback(teacher_dir: str, target_version: str) -> bool:
    """Roll back a teacher skill to a previous version. Backs up current state first."""
    target_dir = os.path.join(teacher_dir, "versions", f"v{target_version}")
    if not os.path.isdir(target_dir):
        return False

    meta_path = os.path.join(teacher_dir, "meta.json")
    current_version = "unknown"
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        current_version = meta.get("version", "unknown")
        backup_dir = os.path.join(teacher_dir, "versions", f"v{current_version}_before_rollback")
        os.makedirs(backup_dir, exist_ok=True)
        for fname in ["SKILL.md", "teaching.md", "voice.md", "meta.json"]:
            src = os.path.join(teacher_dir, fname)
            if os.path.exists(src):
                shutil.copy2(src, backup_dir)

    for fname in ["SKILL.md", "teaching.md", "voice.md", "meta.json"]:
        src = os.path.join(target_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(teacher_dir, fname))

    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["rollback_from"] = current_version
        meta["updated_at"] = datetime.now().strftime("%Y-%m-%d")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    return True


def cleanup_old_versions(teacher_dir: str) -> int:
    """Remove archived versions beyond MAX_VERSIONS, oldest first.

    Prunes only what `list_versions` reports — directories named `v…` — and never a
    `_before_rollback` copy. The first version selected *every* directory under
    `versions/`, so anything else a maintainer kept there was deleted once the
    archive passed the limit, and the backup `rollback` writes so that a bad
    rollback can be undone was evicted by age like an ordinary version.
    """
    versions_dir = os.path.join(teacher_dir, "versions")
    if not os.path.exists(versions_dir):
        return 0

    entries = []
    for entry in os.listdir(versions_dir):
        entry_path = os.path.join(versions_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        if not entry.startswith("v") or entry.endswith("_before_rollback"):
            continue
        entries.append((entry_path, os.path.getmtime(entry_path)))

    entries.sort(key=lambda x: x[1], reverse=True)

    removed = 0
    for path, _ in entries[MAX_VERSIONS:]:
        shutil.rmtree(path)
        removed += 1

    return removed
