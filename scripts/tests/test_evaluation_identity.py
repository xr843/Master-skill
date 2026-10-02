import importlib
import sys
import pytest
import os
import subprocess
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


def test_mode_identity_tracks_every_tool_readable_skill_file_and_directory(tmp_path):
    master = tree(tmp_path)
    mode = tmp_path / "prebuilt" / "master-help"
    mode.mkdir()
    (mode / "SKILL.md").write_text("Recommend masters")
    identity = importlib.import_module("_evaluation_identity").evaluation_identity
    before = identity(mode)
    (master / "notes.txt").write_text("Additional teaching material")
    assert identity(mode)["skill_sha256"] != before["skill_sha256"]
    before = identity(mode)
    other = tmp_path / "prebuilt" / "create-master"
    other.mkdir()
    assert identity(mode)["skill_sha256"] != before["skill_sha256"]
    before = identity(mode)
    (other / "README.md").write_text("Tool-readable instructions")
    assert identity(mode)["skill_sha256"] != before["skill_sha256"]


def test_mode_identity_excludes_inaccessible_fixture_directories(tmp_path):
    master = tree(tmp_path)
    mode = tmp_path / "prebuilt" / "master-help"
    mode.mkdir()
    (mode / "SKILL.md").write_text("Recommend masters")
    identity = importlib.import_module("_evaluation_identity").evaluation_identity
    before = identity(mode)
    (master / "TESTS").mkdir()
    (master / "TESTS" / "answers.md").write_text("Grader-only information")
    assert identity(mode) == before


@pytest.mark.parametrize("mode", [False, True])
def test_symlinked_source_directory_cannot_hide_untracked_inputs(tmp_path, mode):
    master = tree(tmp_path)
    (master / "sources" / "excerpt.md").unlink()
    (master / "sources").rmdir()
    external = tmp_path / "external"
    external.mkdir()
    (external / "original.md").write_text("Outside source content")
    (master / "sources").symlink_to(external, target_is_directory=True)
    if mode:
        subject = tmp_path / "prebuilt" / "master-help"
        subject.mkdir()
        (subject / "SKILL.md").write_text("Recommend masters")
    else:
        subject = master
    with pytest.raises(ValueError, match="symlink"):
        importlib.import_module("_evaluation_identity").evaluation_identity(subject)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="named pipes require POSIX")
def test_tool_visible_named_pipe_does_not_block_fingerprinting(tmp_path):
    tree(tmp_path)
    mode = tmp_path / "prebuilt" / "master-help"
    mode.mkdir()
    (mode / "SKILL.md").write_text("Recommend masters")
    pipe = mode / "queue"
    os.mkfifo(pipe)
    program = '''import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from _evaluation_identity import evaluation_identity
mode = Path(sys.argv[2])
before = evaluation_identity(mode)
pipe = mode / "queue"
pipe.unlink()
pipe.write_text("")
assert evaluation_identity(mode)["skill_sha256"] != before["skill_sha256"]
'''
    result = subprocess.run([sys.executable, "-S", "-c", program,
        str(Path(__file__).resolve().parents[1]), str(mode)],
        capture_output=True, text=True, timeout=3)
    assert result.returncode == 0, result.stderr
