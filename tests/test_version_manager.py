"""Tests for version_manager.py — the archive it prunes is someone's only backup.

`skill_writer.update_teacher` archives a master into `versions/v{version}/` before
it rewrites anything, and `prompts/correction_handler.md` and `prompts/merger.md`
both tell the agent to archive before a correction or a merge. version_manager is
what lists, restores and prunes those archives, and until 2026-09-16 it had no test
of any kind — including `cleanup_old_versions`, which calls `shutil.rmtree`.

Two of the cases below fail against the version that shipped:

  - `cleanup_old_versions` selected *every* directory under `versions/`, while
    `list_versions` reports only `v…` ones. Anything else a user kept there was
    deleted once the directory held more than MAX_VERSIONS entries.
  - It counted and deleted `v{version}_before_rollback` too — the backup `rollback`
    makes precisely so a bad rollback can be undone.
"""

import json
import os
import shutil
from pathlib import Path

import pytest
import version_manager
from version_manager import MAX_VERSIONS, cleanup_old_versions, list_versions, rollback


def _teacher(tmp_path: Path, version: str = "1.0.0") -> Path:
    """A master directory shaped the way skill_writer leaves one."""
    teacher = tmp_path / "master-demo"
    (teacher / "versions").mkdir(parents=True)
    for name in ("SKILL.md", "teaching.md", "voice.md"):
        (teacher / name).write_text(f"current {name}\n", encoding="utf-8")
    (teacher / "meta.json").write_text(
        json.dumps({"name": "Demo", "version": version}, ensure_ascii=False), encoding="utf-8"
    )
    return teacher


def _archive(teacher: Path, version: str, marker: str = "old") -> Path:
    """What `skill_writer.update_teacher` writes: versions/v{version}/ with the four files."""
    target = teacher / "versions" / f"v{version}"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("SKILL.md", "teaching.md", "voice.md"):
        (target / name).write_text(f"{marker} {name}\n", encoding="utf-8")
    (target / "meta.json").write_text(
        json.dumps({"name": "Demo", "version": version}, ensure_ascii=False), encoding="utf-8"
    )
    return target


def _age(path: Path, seconds: int) -> None:
    """Make `path` look `seconds` old, so mtime ordering is deterministic."""
    stamp = os.path.getmtime(path) - seconds
    os.utime(path, (stamp, stamp))


# --- list_versions ------------------------------------------------------------


def test_list_versions_is_empty_when_nothing_was_archived(tmp_path):
    teacher = _teacher(tmp_path)
    shutil.rmtree(teacher / "versions")
    assert list_versions(str(teacher)) == []


def test_list_versions_reports_each_archived_version(tmp_path):
    teacher = _teacher(tmp_path)
    _archive(teacher, "1.0.0")
    _archive(teacher, "1.1.0")

    listed = list_versions(str(teacher))

    assert [v["version"] for v in listed] == ["1.0.0", "1.1.0"]
    assert all("meta.json" in v["files"] for v in listed)


def test_list_versions_ignores_a_directory_that_is_not_a_version(tmp_path):
    teacher = _teacher(tmp_path)
    _archive(teacher, "1.0.0")
    (teacher / "versions" / "notes").mkdir()

    assert [v["version"] for v in list_versions(str(teacher))] == ["1.0.0"]


# --- rollback -----------------------------------------------------------------


def test_rollback_refuses_a_version_that_was_never_archived(tmp_path):
    teacher = _teacher(tmp_path)
    assert rollback(str(teacher), "9.9.9") is False


def test_rollback_restores_the_archived_files(tmp_path):
    teacher = _teacher(tmp_path)
    _archive(teacher, "0.9.0", marker="archived")

    assert rollback(str(teacher), "0.9.0") is True
    assert (teacher / "teaching.md").read_text(encoding="utf-8") == "archived teaching.md\n"


def test_rollback_backs_up_what_it_is_about_to_overwrite(tmp_path):
    """The backup is the only way back if the rollback itself was the mistake."""
    teacher = _teacher(tmp_path, version="2.0.0")
    _archive(teacher, "0.9.0", marker="archived")

    rollback(str(teacher), "0.9.0")

    backup = teacher / "versions" / "v2.0.0_before_rollback"
    assert backup.is_dir()
    assert (backup / "teaching.md").read_text(encoding="utf-8") == "current teaching.md\n"


def test_rollback_records_the_version_it_came_from(tmp_path):
    teacher = _teacher(tmp_path, version="2.0.0")
    _archive(teacher, "0.9.0")

    rollback(str(teacher), "0.9.0")

    meta = json.loads((teacher / "meta.json").read_text(encoding="utf-8"))
    assert meta["rollback_from"] == "2.0.0"


# --- cleanup_old_versions -----------------------------------------------------


def test_cleanup_is_a_no_op_before_the_limit(tmp_path):
    teacher = _teacher(tmp_path)
    for i in range(MAX_VERSIONS):
        _archive(teacher, f"1.0.{i}")

    assert cleanup_old_versions(str(teacher)) == 0
    assert len(list_versions(str(teacher))) == MAX_VERSIONS


def test_cleanup_removes_the_oldest_beyond_the_limit(tmp_path):
    teacher = _teacher(tmp_path)
    for i in range(MAX_VERSIONS + 3):
        archived = _archive(teacher, f"1.0.{i}")
        _age(archived, (MAX_VERSIONS + 3 - i) * 60)  # 0 is oldest

    assert cleanup_old_versions(str(teacher)) == 3
    kept = {v["version"] for v in list_versions(str(teacher))}
    assert "1.0.0" not in kept and "1.0.1" not in kept and "1.0.2" not in kept
    assert len(kept) == MAX_VERSIONS


def test_cleanup_leaves_alone_a_directory_that_is_not_a_version(tmp_path):
    """`list_versions` reports only `v…`; pruning must not reach further than that.

    Shipped behaviour deleted it: the selection was every directory under
    `versions/`, so a `notes/` folder a maintainer kept there went away as soon as
    the archive passed MAX_VERSIONS.
    """
    teacher = _teacher(tmp_path)
    notes = teacher / "versions" / "notes"
    notes.mkdir()
    (notes / "why.md").write_text("kept by hand\n", encoding="utf-8")
    _age(notes, 10_000)  # oldest, so the unfiltered version would evict it first
    for i in range(MAX_VERSIONS + 2):
        _age(_archive(teacher, f"1.0.{i}"), (MAX_VERSIONS + 2 - i) * 60)

    cleanup_old_versions(str(teacher))

    assert notes.is_dir(), "cleanup deleted a directory that is not a version"
    assert (notes / "why.md").exists()


def test_cleanup_never_deletes_a_rollback_backup(tmp_path):
    """The `_before_rollback` copy exists so a bad rollback can be undone.

    Shipped behaviour counted it as just another version and evicted it by age,
    which takes away the one thing standing between a wrong rollback and a loss.
    """
    teacher = _teacher(tmp_path, version="2.0.0")
    _archive(teacher, "0.9.0")
    rollback(str(teacher), "0.9.0")
    backup = teacher / "versions" / "v2.0.0_before_rollback"
    assert backup.is_dir()
    _age(backup, 10_000)  # oldest by far
    for i in range(MAX_VERSIONS + 2):
        _age(_archive(teacher, f"3.0.{i}"), (MAX_VERSIONS + 2 - i) * 60)

    cleanup_old_versions(str(teacher))

    assert backup.is_dir(), "cleanup deleted the backup rollback made"


def test_cleanup_on_a_tree_without_an_archive_returns_zero(tmp_path):
    teacher = _teacher(tmp_path)
    shutil.rmtree(teacher / "versions")
    assert cleanup_old_versions(str(teacher)) == 0
