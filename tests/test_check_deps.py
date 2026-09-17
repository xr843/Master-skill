"""create-master's dependency check.

Every generator tool imports `fojin_bridge` (→ requests) or `skill_writer`
(→ yaml, pypinyin) at module level, so a missing package stops each tool before it
does anything. `check_deps.py` is the standard-library-only probe the generator runs
first (Step 0) and that `master-skill doctor` asks.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import check_deps

ROOT = Path(check_deps.__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
STDLIB = set(sys.stdlib_module_names)
LOCAL = {path.stem for path in TOOLS.glob("*.py")}


def test_reports_exactly_the_distributions_that_cannot_be_imported():
    absent = {"yaml"}
    assert check_deps.missing(lambda module: None if module in absent else object()) == ["pyyaml"]
    assert check_deps.missing(lambda module: object()) == []


def test_exits_1_with_install_steps_when_something_is_missing(monkeypatch, capsys):
    monkeypatch.setattr(check_deps, "missing", lambda: ["requests"])
    assert check_deps.main([]) == 1
    out = capsys.readouterr().out
    assert "requests" in out
    assert "requirements.txt" in out
    assert "externally-managed-environment" in out  # PEP 668 refuses the plain pip line
    assert "venv" in out


def test_exits_0_when_everything_imports(monkeypatch, capsys):
    monkeypatch.setattr(check_deps, "missing", lambda: [])
    assert check_deps.main([]) == 0
    assert capsys.readouterr().out.startswith("OK:")


def test_it_imports_nothing_outside_the_standard_library():
    """It has to run exactly where the tools it checks cannot."""
    tree = ast.parse((TOOLS / "check_deps.py").read_text(encoding="utf-8"))
    imported = {
        (alias.name if isinstance(node, ast.Import) else node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported - {"__future__"} <= STDLIB


def test_every_third_party_module_a_tool_imports_at_startup_is_checked():
    """A tool that grows a new top-level dependency must not slip past the check."""
    third_party = set()
    for tool in TOOLS.glob("*.py"):
        tree = ast.parse(tool.read_text(encoding="utf-8"))
        for node in tree.body:
            nodes = [node] + (list(ast.walk(node)) if isinstance(node, ast.Try) else [])
            for inner in nodes:
                if isinstance(inner, ast.Import):
                    names = [alias.name for alias in inner.names]
                elif isinstance(inner, ast.ImportFrom) and inner.level == 0:
                    names = [inner.module or ""]
                else:
                    continue
                for name in names:
                    top = name.split(".")[0]
                    if top and top not in STDLIB and top not in LOCAL and top != "__future__":
                        third_party.add(top)
    assert third_party, "found no third-party imports — check the scan"
    assert third_party <= set(check_deps.REQUIRED), sorted(third_party - set(check_deps.REQUIRED))


def test_the_generator_runs_the_check_before_step_1():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    step0 = skill.index('tools/check_deps.py"')
    assert step0 < skill.index("### Step 1")
