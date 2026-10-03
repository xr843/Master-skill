"""Shared repo paths and file readers for the scripts under scripts/.

Twenty-odd scripts each spelled `Path(__file__).resolve().parent.parent`, and
the same few readers — SKILL.md frontmatter, the fidelity fixtures, a JSON file
that may be missing — were written out again wherever they were needed. This
module is the one copy. It is stdlib-only at import time (pyyaml is imported
only when frontmatter is parsed) and Python 3.9 compatible: the generator
compatibility job compiles every script under 3.9.

Scripts import it as a sibling (`from _skill_io import ROOT`): running
`python3 scripts/x.py` puts scripts/ on sys.path, and the pytest conftests do
the same for in-process tests.

tools/ does not import it, deliberately. The create-master install copies
tools/ without scripts/ (skill-catalog.json `bundle_paths`), so tools/ must
stay self-contained; the dependency runs only scripts/ -> tools/. That is why
tools/verify_sources.py and tools/master_builder.py keep their own
`text.split("---", 2)` readers.

Two frontmatter readers, on purpose. They disagree on malformed input and each
caller's behaviour is kept exactly (scripts/tests/test_skill_io.py pins both):

* `split_frontmatter` / `load_frontmatter` split on the first two `---`
  substrings anywhere in the text. Leading whitespace before the opening
  `---` is accepted; a `---` inside a value (`name: a---b`) ends the block
  early. Same semantics as tools/verify_sources.py's two readers.
* `parse_frontmatter_lines` (validate.py) needs the opening and closing
  fences as whole lines, so `a---b` is read whole and a leading blank line
  means no frontmatter; a non-mapping or invalid block raises ValueError.

On every prebuilt SKILL.md the two return the same mapping.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
PREBUILT_DIR = ROOT / "prebuilt"


# --- SKILL.md frontmatter -------------------------------------------------


def split_frontmatter(text: str) -> Optional[str]:
    """Raw YAML between the first two `---`, or None when there is no block.

    No block means: fewer than two `---` in the text, or anything other than
    whitespace before the first one.
    """
    parts = text.split("---", 2)
    if len(parts) < 3 or parts[0].strip():
        return None
    return parts[1]


def load_frontmatter(text: str) -> Any:
    """`split_frontmatter` parsed with yaml.safe_load; {} when absent or empty.

    YAML errors propagate. A block that parses to a non-mapping is returned
    as parsed, not coerced — callers that call `.get` on it fail as before.
    """
    raw = split_frontmatter(text)
    if raw is None:
        return {}
    import yaml

    return yaml.safe_load(raw) or {}


def parse_frontmatter_lines(text: str, source: object = "<string>") -> Tuple[dict, str, List[str]]:
    """Line-fenced frontmatter: returns (mapping, body, lines).

    The first line must be `---` (surrounding whitespace ignored) and the block
    ends at the next such line. Without both fences the result is
    ({}, text, lines). Invalid YAML or a non-mapping block raises ValueError
    prefixed with `source`.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text, lines

    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}, text, lines

    import yaml

    try:
        fm = yaml.safe_load("\n".join(lines[1:end])) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{source}: invalid YAML frontmatter — {exc}") from exc
    if not isinstance(fm, dict):
        raise ValueError(f"{source}: frontmatter is not a mapping")

    body = "\n".join(lines[end + 1 :])
    return fm, body, lines


# --- sources/*.md sections ------------------------------------------------


def parse_sections(text: str) -> List[Tuple[str, str]]:
    """按 ## 标题分段，返回 [(title, body), ...]"""
    sections = []
    parts = re.split(r'^## ', text, flags=re.MULTILINE)
    for part in parts[1:]:
        lines = part.split('\n', 1)
        title = lines[0].strip()
        body = lines[1] if len(lines) > 1 else ''
        sections.append((title, body))
    return sections


# --- fixtures and JSON ----------------------------------------------------


def load_fixtures(prebuilt: Path = PREBUILT_DIR) -> Dict[str, List[dict]]:
    """{skill dir name: [fixture, ...]} from every `<prebuilt>/*/tests/fidelity.jsonl`.

    Read with the platform default encoding, as both former copies did.
    """
    fixtures: Dict[str, List[dict]] = {}
    for path in sorted(prebuilt.glob("*/tests/fidelity.jsonl")):
        fixtures[path.parent.parent.name] = [
            json.loads(line) for line in path.read_text().splitlines() if line.strip()
        ]
    return fixtures


def try_read_json(path: Path) -> Tuple[Any, Optional[Exception]]:
    """(parsed, None), or (None, error) when the file is unreadable or not JSON."""
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (json.JSONDecodeError, OSError) as err:
        return None, err
