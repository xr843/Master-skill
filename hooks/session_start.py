#!/usr/bin/env python3
"""Build the SessionStart context block for Master-skill.

This used to live entirely in `hooks/session-start` as a bash loop that
invoked `python3` once per master to sanitize one `lineage:` value, plus once
more to JSON-encode the result. With 16 masters that is 17 interpreter
starts on a hook the harness runs with `"async": false` — measured at 0.37s
per session start / clear / compact on Linux, and worse on Windows where the
wrapper adds a shell hop and process creation costs more. One process does
the same work in about 0.03s.

Two correctness fixes came with the move, both in the old bash:

  - the *directory name* was spliced into the context unsanitized, on the same
    line as a carefully sanitized `lineage` — a lopsided defence;
  - the JSON encoding had `|| echo "\\"$CONTEXT\\""` as a fallback, which on a
    python3-less machine emitted an unescaped multi-line string as if it were
    JSON. Failing closed is the only safe direction for something spliced into
    a system prompt.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Whitelist: CJK Unified, ASCII alphanumerics, fullwidth parens, space, · _ ( ) -
# Everything else — backticks, dollars, quotes, slashes, control characters —
# is dropped. An attacker who lands a malicious SKILL.md (or a contributor with
# a typo) must not be able to reach the system prompt through it.
_ALLOWED = re.compile(r"[^一-鿿0-9A-Za-z _\-·（）()]", re.UNICODE)
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_WHITESPACE = re.compile(r"\s+")

MAX_LINEAGE_CHARS = 80

# Directory names are already constrained by the installer's `isSafeName`, but
# this is the last hop before a system prompt: enforce it here too rather than
# trusting a check made somewhere else.
_SAFE_DIR_NAME = re.compile(r"^[A-Za-z0-9_-]+$")

_LINEAGE_LINE = re.compile(r"^lineage:\s*(.*)$", re.MULTILINE)


def sanitize_lineage(raw: str) -> str:
    """Normalize one raw `lineage:` frontmatter value for prompt splicing."""
    text = _CONTROL.sub("", raw or "")
    text = _ALLOWED.sub("", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text[:MAX_LINEAGE_CHARS]


def read_lineage(skill_file: Path) -> str:
    try:
        content = skill_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    match = _LINEAGE_LINE.search(content)
    return sanitize_lineage(match.group(1)) if match else ""


def collect_masters(plugin_root: Path) -> list[tuple[str, str]]:
    """Every prebuilt master with a usable name and lineage, sorted by name."""
    prebuilt = plugin_root / "prebuilt"
    if not prebuilt.is_dir():
        return []
    found = []
    for entry in sorted(prebuilt.iterdir()):
        if not entry.is_dir() or entry.name == "compare":
            continue
        if not _SAFE_DIR_NAME.match(entry.name):
            # Unreachable through a normal install; skipped rather than
            # spliced, because this string ends up in a system prompt.
            continue
        skill_file = entry / "SKILL.md"
        if not skill_file.is_file():
            continue
        lineage = read_lineage(skill_file)
        if lineage:
            found.append((entry.name, lineage))
    return found


def build_context(masters: list[tuple[str, str]]) -> str:
    lines = "".join(
        # The bracketed marker gives the model an unambiguous boundary even if
        # a future lineage sneaks something past the sanitizer.
        f"  /{name} — [lineage:{lineage}]\n"
        for name, lineage in masters
    )
    return (
        "Master-skill plugin loaded. Available Buddhist masters:\n"
        f"{lines}"
        "  /master-help — not sure which master or mode? start here\n"
        "  /compare-masters — multi-tradition comparison\n"
        "  /master-debate — 4-round adversarial dialectic between masters\n"
        "  /master-curriculum — staged learning path within a tradition\n"
        "  /create-master — generate new master from FoJin knowledge graph\n"
        "\n"
        "All doctrinal responses include CBETA citations linked to fojin.app."
    )


def wrap_for_host(context: str, env: dict) -> dict:
    """The same payload in whichever shape this host reads."""
    if env.get("CURSOR_PLUGIN_ROOT"):
        return {"additional_context": context}
    if env.get("CLAUDE_PLUGIN_ROOT") and not env.get("COPILOT_CLI"):
        return {"hookSpecificOutput": {"additionalContext": context}}
    return {"additionalContext": context}


def main(argv: list[str]) -> int:
    # `--sanitize-lineage <value>` is the seam hooks/tests/test_session_start.sh
    # drives; it prints the sanitized value and nothing else.
    if len(argv) >= 2 and argv[0] == "--sanitize-lineage":
        sys.stdout.write(sanitize_lineage(argv[1]))
        return 0

    plugin_root = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent
    context = build_context(collect_masters(plugin_root))
    print(json.dumps(wrap_for_host(context, os.environ), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
