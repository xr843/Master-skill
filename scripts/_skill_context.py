"""Shared runtime context for fidelity and persona evaluation."""
from pathlib import Path


def _read_context_file(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"context input is not a regular file: {path}")
    return path.read_text(encoding="utf-8")


def load_skill_context(master_dir: Path) -> str:
    """Load SKILL.md + references as a combined system prompt."""
    parts: list[str] = []

    skill = master_dir / "SKILL.md"
    if skill.exists():
        parts.append(_read_context_file(skill))

    # Load references (voice.md, teaching.md)
    refs_dir = master_dir / "references"
    if refs_dir.exists():
        for f in sorted(refs_dir.glob("*.md")):
            parts.append(f"\n\n---\n# {f.stem}\n\n{_read_context_file(f)}")

    # Load source excerpts
    sources_dir = master_dir / "sources"
    if sources_dir.exists():
        for f in sorted(sources_dir.glob("*.md")):
            if f.name == "INDEX.md":
                continue
            parts.append(f"\n\n---\n# Source: {f.stem}\n\n{_read_context_file(f)}")

    return "\n".join(parts)
