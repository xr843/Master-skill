"""Tests for scripts/_masterpaths.py and the short-name resolution fix
in query.py / cite.py (the documented `--master <slug>` invocation used to
silently find nothing because dirs are named `master-<slug>`)."""

import importlib
import subprocess
import sys
from pathlib import Path

_masterpaths = importlib.import_module("_masterpaths")
resolve_master_dir = _masterpaths.resolve_master_dir

REPO = Path(__file__).resolve().parent.parent


def test_resolve_short_name():
    d = resolve_master_dir("huineng")
    assert d is not None and Path(d).name == "master-huineng"


def test_resolve_full_name():
    d = resolve_master_dir("master-huineng")
    assert d is not None and Path(d).name == "master-huineng"


def test_resolve_missing_returns_none():
    assert resolve_master_dir("nonexistent-master") is None


def test_resolve_never_escapes_base():
    """Defense in depth: even unvalidated traversal / abs paths resolve to None,
    never to a dir outside prebuilt/ (callers also charset-gate, this is backup)."""
    assert resolve_master_dir("../scripts") is None
    assert resolve_master_dir("/etc") is None
    assert resolve_master_dir("") is None


def _run(script, *args):
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / script), *args],
        capture_output=True, text=True,
    )


def test_query_short_name_now_finds_results():
    """Regression: `query.py --master huineng` (short, as SKILL.md documents)
    must return results, not silently empty."""
    r = _run("query.py", "--master", "huineng", "--q", "见性", "--brief")
    assert r.returncode == 0
    assert "未找到" not in r.stdout
    assert "→" in r.stdout  # at least one [section] → file line


def test_cite_short_name_now_works():
    r = _run("cite.py", "--master", "huineng", "--text", "见性")
    assert r.returncode == 0


def test_query_unknown_master_errors_not_silent():
    """Unknown master should error (exit 2), not exit 0 with an empty result."""
    r = _run("query.py", "--master", "nonexistent-master", "--q", "x")
    assert r.returncode == 2
    assert "找不到 master" in r.stderr


def test_query_rejects_traversal():
    r = _run("query.py", "--master", "../../etc", "--q", "x")
    assert r.returncode == 2
