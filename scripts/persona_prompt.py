"""Promptfoo Python prompt function using the fidelity runner's real context."""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _skill_context import load_skill_context

from _skill_io import ROOT


def create_prompt(context: dict) -> list[dict[str, str]]:
    variables = context["vars"]
    master, question = variables.get("master"), variables.get("question")
    if not isinstance(master, str) or not re.fullmatch(r"master-[a-z0-9-]+", master):
        raise ValueError("master must be a persona slug")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a nonempty string")
    directory = ROOT / "prebuilt" / master
    if not (directory / "SKILL.md").is_file():
        raise ValueError(f"persona has no SKILL.md: {master}")
    return [{"role": "system", "content": load_skill_context(directory)},
            {"role": "user", "content": question}]
