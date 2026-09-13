#!/usr/bin/env python3
"""Gate: a skill must not demand verifiable citations and then show a template
that cannot carry one.

`compare-masters/SKILL.md` did exactly that. Line 223 required every doctrinal
claim to "解析到所选 persona 的 meta.json.sources[]" and line 259 required a
"可核验的来源引用" — while the output template two hundred lines earlier read

    > 出处：【《经名》卷N】→ fojin.app 链接

with no identifier in it. The model followed the template, and the 2026-09-12
sweep measured the result: 18 answers, 49 citations, **zero checkable**, audit
coverage 0%. The rule and the example were in the same file and contradicted
each other; nothing was comparing them.

The check is deliberately narrow. It does NOT require every citation format to
carry an identifier — `master-buddhaghosa`, `master-mahasi-sayadaw` and
`master-tsongkhapa` declare formats without one because PTS / SuttaCentral /
BDRC are corpus-level references with no per-passage id, which the citation
contract documents as a known boundary. Requiring an id there would force a
fabricated one, which is worse than an unverifiable citation.

What it requires is consistency: a skill that quotes *other* personas must
defer to their declared `citation_format` rather than inventing a weaker shape
of its own. Deferring is also what makes the boundary above work — quoting
buddhaghosa inherits buddhaghosa's format, id-less and honest.

The second rule was added after the first one turned out to examine 1 of the 3
meta-skills and return early on the other two. `master-debate` requires "至少 1
个本宗 citation" four times over and never says what one looks like; the same
sweep shows it wrote 24 real sutra ids as `《坛经》（T48n2008）`. The auditor's
`_CITATION_BLOCK` parses `【…】` only, so all 24 were invisible and the report
read `audit_coverage: N/A` — the same cell `master-help`, which legitimately
never cites, prints. Requiring citations and not naming an auditable shape
produces citations nobody checks, which reads as clean.

Usage:
    python3 scripts/validate-citation-templates.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PREBUILT = Path(__file__).resolve().parent.parent / "prebuilt"

# A literal citation example: 【…】 with no {placeholder} inside, i.e. a shape
# the writer intended to be copied rather than filled from a declared format.
_LITERAL_CITATION = re.compile(r"【《[^》{]*》[^】{]*】")

# Phrases by which a file asserts its citations are checkable. Kept to the ones
# this repo actually uses, so the check cannot drift into policing prose.
_VERIFIABILITY_CLAIMS = ("可核验", "必须解析到", "可核对")

# Skills that quote other personas rather than speaking as one.
_META_SKILLS = ("compare-masters", "master-debate", "master-curriculum")

# The only shape `verify_citations._CITATION_BLOCK` parses. A citation written
# any other way is served to the reader and audited by nothing.
_AUDITABLE_BLOCK = re.compile(r"【[^】]*】")

# A file demanding citations of its output. Narrow on purpose: `master-help`
# mentions the word without requiring any, and must not be caught.
_REQUIRES_CITATION = (
    re.compile(r"至少\s*\d+\s*(?:个|条)[^。\n]{0,12}citation"),
    re.compile(r"引用必须"),
    re.compile(r"必须附[^。\n]{0,12}引用"),
    re.compile(r"引经必经查证"),
)


def _strip_html_comments(text: str) -> str:
    """Drop <!-- … --> before scanning.

    The first run of this check flagged the comment that explains what the bad
    template used to look like — reading the note about the defect as the
    defect. That is the same "the test matched the docstring" shape this repo
    keeps producing, one level up. A comment is not an instruction to the
    model: SKILL.md is rendered as markdown, and an HTML comment does not
    appear in what the model is shown.

    The newlines are kept, so a reported line number still points at the line a
    maintainer will open. Deleting them outright shifts every later line and
    sends the reader to the wrong place — a small lie in the same family.
    """
    return re.sub(
        r"<!--.*?-->",
        lambda m: "\n" * m.group().count("\n"),
        text,
        flags=re.S,
    )


def check_skill(path: Path) -> tuple[list[str], list[str]]:
    """Return (problems, rules that actually examined this file).

    The second element exists so `main` can print what was looked at. The
    first version of this check returned early on two of the three meta-skills
    and printed a clean line anyway; a gate that says nothing about its own
    reach is how this repo has repeatedly shipped an inert one.
    """
    text = _strip_html_comments(path.read_text(encoding="utf-8"))
    name = path.parent.name
    problems: list[str] = []
    examined: list[str] = []

    declares_own_format = re.search(r"^citation_format:", text, re.M) is not None

    # Rule 1 — a verifiability claim must not sit next to an id-less template.
    claims = [c for c in _VERIFIABILITY_CLAIMS if c in text]
    if claims:
        examined.append("claims-vs-template")
        for match in _LITERAL_CITATION.finditer(text):
            # A persona with its own declared format may show an example of it.
            if declares_own_format and name not in _META_SKILLS:
                continue
            line = text[: match.start()].count("\n") + 1
            problems.append(
                f"{name}/SKILL.md:{line}: the file claims citations are "
                f"{claims[0]} but shows the literal template {match.group()!r}, "
                "which carries no identifier. A skill that quotes personas must "
                "defer to their declared `citation_format`."
            )

    # Rule 2 — requiring citations without naming an auditable shape produces
    # citations the auditor cannot see, which reports as `N/A`, not as a miss.
    demand = next((p for p in _REQUIRES_CITATION if p.search(text)), None)
    if demand is not None:
        examined.append("demand-vs-auditable-shape")
        if not _AUDITABLE_BLOCK.search(text):
            line = text[: demand.search(text).start()].count("\n") + 1
            problems.append(
                f"{name}/SKILL.md:{line}: the file requires citations "
                f"(matched {demand.pattern!r}) but never shows the 【…】 form. "
                "`verify_citations._CITATION_BLOCK` parses that shape and no "
                "other, so whatever the model writes instead is served "
                "unaudited and reports as `audit_coverage: N/A`."
            )

    return problems, examined


def main() -> int:
    skills = sorted(p for p in PREBUILT.glob("*/SKILL.md"))
    if not skills:
        print("no SKILL.md found under prebuilt/ — this check would pass vacuously")
        return 1

    problems: list[str] = []
    reach: dict[str, list[str]] = {}
    for path in skills:
        found, examined = check_skill(path)
        problems += found
        for rule in examined:
            reach.setdefault(rule, []).append(path.parent.name)

    if problems:
        print(f"✗ {len(problems)} citation-template problem(s):\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(f"✓ citation templates ok — {len(skills)} skills scanned")
    for rule in ("claims-vs-template", "demand-vs-auditable-shape"):
        names = reach.get(rule, [])
        if not names:
            print(f"  ✗ {rule}: examined 0 skills — this rule decided nothing")
            return 1
        print(f"  {rule}: {len(names)} skill(s) — {', '.join(sorted(names))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
