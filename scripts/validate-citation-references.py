#!/usr/bin/env python3
"""Gate: a persona must not instruct a citation its own contract forbids.

`validate-citation-contract.py` checks that `meta.json` declares the right
*fields*. Nothing checked whether the persona's own SKILL.md, sources/ and
references/ tell it to cite sources that `meta.json` never declares — and that
is a shipped defect, not a hypothetical: `master-tsongkhapa`'s SKILL.md gives

    印度大乘论典所引：`【月称《入中论》§第六章】（Toh 3861）`

as the prescribed format while `meta.json` declares five sources, none of them
`Toh:3861`. Every use of that instruction violates the B1 citation rule.

That was found by a ¥3.89 graded run over 211 fixtures, which caught it only
because one fixture happened to trigger it. This finds every instance of the
class deterministically, for free, on every PR.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_citations import audit_answer, load_declared_ids, load_member_aliases  # noqa: E402

PREBUILT_DIR = Path(__file__).resolve().parent.parent / "prebuilt"

_BLOCK = re.compile(r"【([^】]*)】")
# Same attribution region verify_citations uses, so a tag documented after the
# block (（BDRC: Wxxxxx）) is judged together with the block it belongs to.
_LINK_WINDOW = 120

# Documentation showing the citation *format* is not a citation. Every marker
# here appears in shipped persona docs; none can occur in a real reference.
_TEMPLATE_MARKERS = (
    re.compile(r"\{"),            # 【《{title}》，{source_id}】
    re.compile(r"[A-Za-z][xX]{3,}"),  # （BDRC: Wxxxxx） / Txxnxxxx
    re.compile(r"卷N"),           # 【《法華玄義》卷N，T1716】
    re.compile(r"典籍名|章节名"),   # 【《典籍名》§章节】
)

# Open findings, each awaiting a maintainer decision. This is a ratchet, not an
# allowlist: an entry here is a defect that has been *seen*, not one that has
# been permitted. Do not add to it to turn a red build green — that is exactly
# the failure this gate exists to prevent.
#
# Empty as of 2026-09-03. Both findings this gate ever recorded were resolved
# by declaring the source: `Toh:3861` in master-tsongkhapa/meta.json (月称《入
# 中论》is a real Tengyur text Tsongkhapa's tradition treats as its own
# foundation) and `J36nB348` in master-ouyi/meta.json (《灵峰宗论》is Ouyi's own
# collected works). Neither needed a B1 contract change — both simply belonged
# in the declared set. See CHANGELOG.md for the maintainer decision.
KNOWN_UNDECLARED: dict[tuple[str, str], str] = {}


def is_template_block(text: str) -> bool:
    """Is this citation documenting the format rather than citing a source?"""
    return any(marker.search(text) for marker in _TEMPLATE_MARKERS)


def _strip_template_citations(text: str) -> str:
    """Drop format-documentation citations, with their attribution regions."""
    blocks = list(_BLOCK.finditer(text))
    out: list[str] = []
    prev = 0
    for index, match in enumerate(blocks):
        next_start = blocks[index + 1].start() if index + 1 < len(blocks) else len(text)
        region_end = min(next_start, match.end() + _LINK_WINDOW)
        context = match.group(1) + text[match.end():region_end]
        if is_template_block(context):
            out.append(text[prev:match.start()])
            prev = region_end
    out.append(text[prev:])
    return "".join(out)


@dataclass(frozen=True)
class Finding:
    master: str
    citation: str
    path: str


def find_undeclared(prebuilt_dir: Path) -> list[Finding]:
    """Every citation the personas' own material makes that meta.json omits."""
    findings: list[Finding] = []
    for persona in sorted(Path(prebuilt_dir).iterdir()):
        meta_path = persona / "meta.json"
        if not persona.is_dir() or not meta_path.is_file():
            continue
        # Found by an independent code-review pass (2026-09-03): this used to
        # reimplement its own meta.json parsing instead of calling
        # verify_citations.py's own loader — a real drift risk, since a future
        # change to how sources/notes are parsed there would silently stop
        # applying here. `persona.name` round-trips through resolve_master_dir
        # (it already accepts the full `master-<slug>` form).
        try:
            declared = load_declared_ids(persona.name, base=str(prebuilt_dir))
            aliases = load_member_aliases(persona.name, base=str(prebuilt_dir))
        except (FileNotFoundError, ValueError):
            continue  # meta.json exists (meta_path.is_file() above) but is unreadable
        if not declared:
            continue  # nothing to audit against; see master-debate
        docs = [persona / "SKILL.md"]
        docs += sorted(persona.glob("sources/*.md"))
        docs += sorted(persona.glob("references/*.md"))
        for doc in docs:
            if not doc.is_file():
                continue
            text = _strip_template_citations(doc.read_text(encoding="utf-8"))
            for citation in dict.fromkeys(audit_answer(declared, text, aliases)["fabricated"]):
                findings.append(
                    Finding(persona.name, citation, str(doc.relative_to(prebuilt_dir.parent)))
                )
    return findings


def main() -> int:
    findings = find_undeclared(PREBUILT_DIR)
    known, new = [], []
    for f in findings:
        (known if (f.master, f.citation) in KNOWN_UNDECLARED else new).append(f)

    if known:
        print(f"Known undeclared citations ({len(known)}) — open findings, not permissions:")
        for f in known:
            print(f"  {f.master}: {f.citation}  ({f.path})")
        for key in dict.fromkeys((f.master, f.citation) for f in known):
            print(f"\n  {key[0]} / {key[1]}:\n    {KNOWN_UNDECLARED[key]}")

    if new:
        print(f"\nFAIL: {len(new)} citation(s) not declared in the persona's meta.json:")
        for f in new:
            print(f"  {f.master}: {f.citation}  ({f.path})")
        print(
            "\nThe persona's own material instructs a citation its citation contract "
            "forbids.\nDeclare the source in meta.json, or stop citing it. Adding it to "
            "KNOWN_UNDECLARED\nwithout a maintainer decision defeats the point of this gate."
        )
        return 1

    print(f"\nOK: no new undeclared citations across {len(list(PREBUILT_DIR.iterdir()))} skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
