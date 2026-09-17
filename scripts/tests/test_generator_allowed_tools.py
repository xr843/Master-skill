"""The generator must not pre-approve tools that act on the world without a check.

`allowed-tools` in a skill's frontmatter lets Claude use those tools without asking
during the turn that invokes the skill. create-master listed plain `Bash`, `Write`,
`Edit` and `WebFetch`. That turn is exactly when it pulls FoJin knowledge-graph and
text content into context — content `tools/master_builder.py` itself calls untrusted,
because FoJin enriches its graph from third-party-editable sources. An instruction
smuggled into that content could have run any shell command, written any file or
fetched any URL with no prompt in front of the user.

Nothing the generator does in that turn needs more than reading and its own Python
tools: every shell command it documents is `python3 ${CLAUDE_SKILL_DIR}/tools/...`,
and it never uses WebFetch. Files are written in Step 5, after the user confirms the
preview — a later message, by which time the grant has already cleared (Claude Code
docs: "The grant clears when you send your next message").
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Tools that change files, run arbitrary commands or reach the network.
_ACTING = {"Bash", "Write", "Edit", "MultiEdit", "NotebookEdit", "WebFetch", "WebSearch"}


def allowed_tools(skill_md: Path) -> list[str]:
    frontmatter = skill_md.read_text(encoding="utf-8").split("---", 2)[1]
    block = re.search(r"^allowed-tools:[ \t]*\n((?:[ \t]+-.*\n)+)", frontmatter, re.MULTILINE)
    if not block:
        return []
    return [line.strip()[1:].strip() for line in block.group(1).splitlines()]


def test_no_unrestricted_acting_tool_is_preapproved():
    tools = allowed_tools(ROOT / "SKILL.md")
    assert tools, "frontmatter parse returned nothing — check the parser"
    unrestricted = [tool for tool in tools if tool in _ACTING]
    assert not unrestricted, f"pre-approved without a pattern: {unrestricted}"


def test_bash_is_limited_to_the_generators_own_tools():
    for tool in allowed_tools(ROOT / "SKILL.md"):
        if tool.startswith("Bash("):
            assert re.fullmatch(r'Bash\(python3 "?\$\{CLAUDE_SKILL_DIR\}/tools/\*\)', tool), tool


def test_every_documented_generator_command_is_covered():
    """If Step 1-3 grows a command outside tools/, this names it before users meet a prompt."""
    text = "\n".join(
        (ROOT / rel).read_text(encoding="utf-8")
        for rel in ("SKILL.md", "references/workflow-details.md")
    )
    commands = re.findall(r"python3 \"?\$\{CLAUDE_SKILL_DIR\}/(\S+?)[\s\"]", text)
    assert commands, "no generator commands found — check the pattern"
    assert all(c.startswith("tools/") for c in commands), sorted(set(commands))
