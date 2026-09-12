"""Shipped persona content gets the same character check generated content gets.

`skill_writer.sanitize_generated` strips control, bidi and zero-width
characters from teaching.md and voice.md before writing them — because those
files are loaded into a model's context as instructions, and an ANSI escape or
a right-to-left override can hide text from a human reviewer while the model
still reads it.

The 15 shipped personas under `prebuilt/` never went through that. They are
reviewed by a person reading a PR diff, which is exactly the reader those
characters are designed to fool: GitHub renders a bidi override, and the line
you see is not the line the model gets.

The scan found zero hits when it was written, so this is a tripwire rather than
a fix — the point is that the asymmetry between "generated, sanitized" and
"committed, unchecked" stops being the difference between two paths into the
same context window.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
PREBUILT = ROOT / "prebuilt"
CONTENT_SUFFIXES = {".md", ".json", ".jsonl"}

# Named so a failure says what was found, not just that something was.
_NOTABLE = {
    0x200B: "ZERO WIDTH SPACE",
    0x200C: "ZERO WIDTH NON-JOINER",
    0x200D: "ZERO WIDTH JOINER",
    0x200E: "LEFT-TO-RIGHT MARK",
    0x200F: "RIGHT-TO-LEFT MARK",
    0x202A: "LEFT-TO-RIGHT EMBEDDING",
    0x202B: "RIGHT-TO-LEFT EMBEDDING",
    0x202C: "POP DIRECTIONAL FORMATTING",
    0x202D: "LEFT-TO-RIGHT OVERRIDE",
    0x202E: "RIGHT-TO-LEFT OVERRIDE",
    0x2066: "LEFT-TO-RIGHT ISOLATE",
    0x2067: "RIGHT-TO-LEFT ISOLATE",
    0x2068: "FIRST STRONG ISOLATE",
    0x2069: "POP DIRECTIONAL ISOLATE",
    0xFEFF: "ZERO WIDTH NO-BREAK SPACE / BOM",
}


def _sanitizer_pattern() -> re.Pattern:
    """The generator's own pattern, imported rather than copied.

    Duplicating it here would let the two drift, and the whole point is that
    both paths into the context window are held to one rule.
    """
    tools = ROOT / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    spec = importlib.util.spec_from_file_location("skill_writer", tools / "skill_writer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._CONTROL_CHARS


PATTERN = _sanitizer_pattern()


def _content_files() -> list[Path]:
    return sorted(
        p for p in PREBUILT.rglob("*")
        if p.is_file() and p.suffix in CONTENT_SUFFIXES
    )


def _describe(char: str) -> str:
    code = ord(char)
    name = _NOTABLE.get(code) or unicodedata.name(char, unicodedata.category(char))
    return f"U+{code:04X} ({name})"


@pytest.mark.parametrize(
    "path", _content_files(), ids=lambda p: str(p.relative_to(ROOT))
)
def test_no_hidden_characters_in_shipped_persona_content(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    found = [
        f"line {text[: m.start()].count(chr(10)) + 1}: {_describe(m.group())}"
        for m in PATTERN.finditer(text)
    ]
    assert found == [], (
        f"{path.relative_to(ROOT)} contains characters the generator strips "
        f"from its own output: {found[:5]}"
    )


def test_the_scan_covers_the_files_that_reach_the_model():
    """Guards the whole file against passing over an empty set."""
    files = _content_files()
    assert len(files) > 100, f"only {len(files)} persona files scanned"
    names = {p.name for p in files}
    for required in ("SKILL.md", "meta.json", "fidelity.jsonl"):
        assert required in names, f"no {required} in the scan"


def test_the_pattern_is_the_generators_own():
    """If skill_writer widens its rule, this widens with it."""
    assert PATTERN.search("‮"), "bidi override should match"
    assert PATTERN.search("\x1b"), "ESC should match"
    assert not PATTERN.search("禅宗\n\t正常文本"), "ordinary content must not match"
