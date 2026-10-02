"""Fingerprint the runtime files and grading implementation behind a run."""
from __future__ import annotations

import hashlib
from pathlib import Path

_MODES = {"compare-masters", "master-debate", "master-curriculum", "master-help"}


def _digest(root: Path, paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        path.relative_to(root)
        for ancestor in (path, *path.parents):
            if ancestor.is_symlink():
                raise ValueError(f"evaluation input is a symlink: {ancestor}")
            if ancestor == root:
                break
        name = path.relative_to(root).as_posix().encode()
        if path.is_dir():
            kind, body = b"directory", b""
        elif path.is_file():
            kind, body = b"file", path.read_bytes().replace(b"\r\n", b"\n")
        else:
            # File tools can list these entries but refuse to read special nodes.
            # Do not open a FIFO or device while computing an input fingerprint.
            kind, body = b"unreadable", b""
        for part in (name, kind, body):
            digest.update(len(part).to_bytes(8, "big"))
            digest.update(part)
    return digest.hexdigest()


def evaluation_identity(master_dir: Path) -> dict[str, str]:
    root = master_dir.parent.parent
    runtime: list[Path] = []
    if master_dir.name in _MODES:
        # SkillFiles can read any installed skill, not just persona excerpts.
        # Bind file contents AND list_dir-visible entries to the measurement.
        runtime = [master_dir.parent] + [
            path for path in master_dir.parent.rglob("*")
            if not any(part.casefold() == "tests"
                       for part in path.relative_to(master_dir.parent).parts)
        ]
    else:
        directory = master_dir
        for name in ("SKILL.md", "meta.json"):
            if (directory / name).is_file():
                runtime.append(directory / name)
        for name in ("sources", "references"):
            if (directory / name).exists() or (directory / name).is_symlink():
                runtime.append(directory / name)
            runtime.extend((directory / name).rglob("*.md"))
    for name in ("routing.json", "skill-catalog.json", "ETHICS.md"):
        if (root / name).is_file():
            runtime.append(root / name)
    grader: list[Path] = []
    for directory in ("scripts", "tools"):
        grader.extend((root / directory).glob("*.py"))
        grader.extend((root / directory).glob("*.json"))
    grader.extend((root / "prompts").glob("*.md"))
    for name in ("requirements.txt", "requirements-eval.txt"):
        if (root / name).is_file():
            grader.append(root / name)
    return {"skill_sha256": _digest(root, runtime), "grader_sha256": _digest(root, grader)}
