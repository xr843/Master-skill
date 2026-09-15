#!/usr/bin/env python3
"""Gate: a persona's self-audit list must include every source it declares.

Nine personas end SKILL.md with the same pre-answer rule (B1): before replying,
check that each offline citation's identifier "∈ 本 master frontmatter `sources:`
声明的对应字段", and strip any claim that fails. The list the model checks
against is the frontmatter, not meta.json, and nothing compared the two.

master-ouyi declares 《灵峰宗论》 `J36nB348` in meta.json, and its own
references/teaching.md cites it, but its frontmatter never listed it. A model
following the rule to the letter deletes a correct citation of Ouyi's own
collected works. The audit would never notice: it reads meta.json.

Personas whose rule points at meta.json instead are not examined here.

Usage:
    python3 scripts/validate-self-audit-sources.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_citations import audit_answer  # noqa: E402

PREBUILT = Path(__file__).resolve().parent.parent / "prebuilt"

# The phrase every frontmatter-pointing rule uses. If the wording changes, the
# gate examines nothing and says so instead of passing.
_RULE = "frontmatter `sources:`"

# The identifier fields the rule itself enumerates.
_ID_FIELDS = (
    "cbeta_id", "toh_id", "bdrc_id", "pts_id", "suttacentral", "suttacentral_id", "teaching_id",
)


def _frontmatter_ids(text: str) -> list[str]:
    parts = text.split("---", 2)
    if len(parts) < 3 or parts[0].strip():
        return []
    front = yaml.safe_load(parts[1]) or {}
    ids: list[str] = []
    for src in front.get("sources") or []:
        if isinstance(src, dict):
            ids += [str(src[field]) for field in _ID_FIELDS if src.get(field) is not None]
    return ids


def _covered(declared_id: str, listed: list[str]) -> bool:
    """Does some frontmatter identifier name `declared_id`, in a spelling the audit accepts?

    The resolution is the auditor's own. master-zhiyi's frontmatter writes
    `T1716` for the declared `T33n1716`; master-milarepa writes `W1GS56158` for
    `BDRC:W1GS56158`. A model citing either passes the audit, so the list covers
    the source. Reimplementing those rules here would drift from them.
    """
    return any(
        declared_id in audit_answer({declared_id}, f"【{value}】")["offline"] for value in listed
    )


def check_persona(persona: Path) -> tuple[list[str], bool]:
    """Return (problems, whether this persona was examined)."""
    skill, meta = persona / "SKILL.md", persona / "meta.json"
    if not skill.is_file() or not meta.is_file():
        return [], False
    text = skill.read_text(encoding="utf-8")
    if _RULE not in text:
        return [], False
    rule_line = text[: text.index(_RULE)].count("\n") + 1
    listed = _frontmatter_ids(text)
    problems: list[str] = []
    for src in json.loads(meta.read_text(encoding="utf-8")).get("sources", []):
        source_id = src.get("id")
        if source_id and not _covered(source_id, listed):
            problems.append(
                f"{persona.name}: meta.json declares {source_id} ({src.get('title', '')}) "
                f"but the frontmatter `sources:` never lists it. The self-audit rule at "
                f"SKILL.md:{rule_line} checks citations against that list, so a correct "
                f"citation of this source would be stripped."
            )
    return problems, True


def main(prebuilt: Path = PREBUILT) -> int:
    problems: list[str] = []
    examined: list[str] = []
    for persona in sorted(p for p in prebuilt.iterdir() if p.is_dir()):
        found, looked = check_persona(persona)
        problems += found
        if looked:
            examined.append(persona.name)

    if not examined:
        print(f"✗ no persona's SKILL.md contains {_RULE!r} — this check examined nothing")
        return 1
    if problems:
        print(f"✗ {len(problems)} declared source(s) missing from a self-audit list:\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(
        f"✓ self-audit sources ok — {len(examined)} persona(s) check citations against "
        f"their frontmatter: {', '.join(examined)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
