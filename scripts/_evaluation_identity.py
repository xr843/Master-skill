"""Fingerprint the runtime files and grading implementation behind a run."""
from __future__ import annotations

import hashlib
from pathlib import Path

_MODES = {"compare-masters", "master-debate", "master-curriculum", "master-help"}


def _digest(root: Path, paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        if path.is_symlink():
            raise ValueError(f"evaluation input is a symlink: {path}")
        name = path.relative_to(root).as_posix().encode()
        body = path.read_bytes().replace(b"\r\n", b"\n")
        for part in (name, body):
            digest.update(len(part).to_bytes(8, "big"))
            digest.update(part)
    return digest.hexdigest()


def evaluation_identity(master_dir: Path) -> dict[str, str]:
    root = master_dir.parent.parent
    directories = [master_dir]
    if master_dir.name in _MODES:
        directories += sorted(p for p in master_dir.parent.glob("master-*") if p.is_dir())
    runtime: list[Path] = []
    for directory in directories:
        for name in ("SKILL.md", "meta.json"):
            if (directory / name).is_file():
                runtime.append(directory / name)
        for name in ("sources", "references"):
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
