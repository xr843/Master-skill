"""Every module the project claims runs on Python 3.9 must actually import there.

README.md advertises "Python 3.9+" and CI runs a `python-compat` job on 3.9 —
but that job only *executes* three modules under tools/, and the `compileall`
step ahead of it checks syntax, not evaluation. `X | Y` in an annotation is
valid syntax on 3.9 and raises TypeError when the `def` runs, so a module can
pass both and still break on import.

That is not hypothetical: `tools/fojin_bridge.py` shipped
`deadline: float | None` with no `from __future__ import annotations`, and
because sutra_collector.py imports it at module level, the 3.9 job failed. It
was caught by review, not by any check here.

This turns the class into a deterministic test that needs no 3.9 interpreter:
an annotation containing `|` is only safe if the module postpones evaluation.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent

# Everything an installed user or the 3.9 job can reach. hooks/ is included
# because session_start.py runs on whatever python3 the host provides.
SCANNED_DIRS = ("tools", "scripts", "hooks")


def _modules() -> list[Path]:
    return sorted(
        p
        for d in SCANNED_DIRS
        for p in (ROOT / d).glob("*.py")
        if p.is_file()
    )


def _runtime_evaluated_unions(tree: ast.AST) -> list[str]:
    """Annotations that are evaluated when the statement executes.

    Function signatures and annotated assignments both evaluate their
    annotations eagerly without `from __future__ import annotations`. Bodies of
    `if TYPE_CHECKING:` are not reached at all, but nothing here uses that.
    """
    found = []
    for node in ast.walk(tree):
        annotations = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
                if arg.annotation:
                    annotations.append(arg.annotation)
            if node.returns:
                annotations.append(node.returns)
            label = node.name
        elif isinstance(node, ast.AnnAssign):
            annotations = [node.annotation]
            label = ast.unparse(node.target)
        else:
            continue
        for annotation in annotations:
            for sub in ast.walk(annotation):
                if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.BitOr):
                    found.append(f"{label} (line {node.lineno})")
                    break
    return found


@pytest.mark.parametrize("module", _modules(), ids=lambda p: str(p.relative_to(ROOT)))
def test_pep604_annotations_are_postponed(module: Path):
    source = module.read_text(encoding="utf-8")
    tree = ast.parse(source)
    offenders = _runtime_evaluated_unions(tree)
    if not offenders:
        return
    assert "from __future__ import annotations" in source, (
        f"{module.relative_to(ROOT)} uses `X | Y` annotations that Python 3.9 "
        f"evaluates at import ({', '.join(offenders[:3])}). Add "
        "`from __future__ import annotations`, or the module cannot be imported "
        "on the floor this project advertises."
    )


def test_the_scan_actually_examined_modules():
    """Guards the whole file against passing over an empty set."""
    modules = _modules()
    assert len(modules) > 20, f"only {len(modules)} modules scanned"
    assert any(m.name == "fojin_bridge.py" for m in modules), (
        "the module that shipped this exact defect is not in the scan"
    )
