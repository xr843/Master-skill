import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def tree(tmp_path):
    master = tmp_path / "prebuilt" / "master-demo"
    master.mkdir(parents=True)
    (master / "SKILL.md").write_text("Answer from original sources.\n")
    (master / "meta.json").write_text('{"sources": []}')
    (master / "sources").mkdir()
    (master / "sources" / "excerpt.md").write_text("original\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "test-fidelity.py").write_text("grader = 1\n")
    return master


def test_identity_tracks_runtime_and_grader_but_not_readme(tmp_path):
    master = tree(tmp_path)
    identity = importlib.import_module("_evaluation_identity").evaluation_identity
    before = identity(master)
    (tmp_path / "README.md").write_text("new documentation")
    assert identity(master) == before
    (master / "SKILL.md").write_text("New instruction.\n")
    assert identity(master)["skill_sha256"] != before["skill_sha256"]
    assert identity(master)["grader_sha256"] == before["grader_sha256"]
    (tmp_path / "scripts" / "test-fidelity.py").write_text("grader = 2\n")
    assert identity(master)["grader_sha256"] != before["grader_sha256"]


def test_teaching_mode_identity_tracks_sibling_sources_and_crlf(tmp_path):
    master = tree(tmp_path)
    mode = tmp_path / "prebuilt" / "compare-masters"
    mode.mkdir()
    (mode / "SKILL.md").write_text("Compare sources.\n")
    identity = importlib.import_module("_evaluation_identity").evaluation_identity
    before = identity(mode)
    (master / "sources" / "excerpt.md").write_bytes(b"original\r\n")
    assert identity(mode) == before
    (master / "sources" / "excerpt.md").write_text("changed original\n")
    assert identity(mode)["skill_sha256"] != before["skill_sha256"]


def test_source_declarations_and_fixture_assertions_are_inputs(tmp_path):
    master = tree(tmp_path)
    identity = importlib.import_module("_evaluation_identity").evaluation_identity
    before = identity(master)
    (master / "meta.json").write_text('{"sources": [{"id":"T48n2008"}]}')
    assert identity(master)["skill_sha256"] != before["skill_sha256"]
