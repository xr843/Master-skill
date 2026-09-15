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

It reads source ids outside 【…】 too. A routing table is an instruction as
much as a citation template is, and until 2026-09-14 this gate saw only
bracketed citations — while six genuine works that personas' own tables and
prose pointed at had never been declared (see `_bare_ids`).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_citations import (  # noqa: E402
    audit_answer,
    extract_citation_ids,
    load_declared_ids,
    load_member_aliases,
    load_title_aliases,
)

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
# Empty as of 2026-09-14. The first two findings this gate recorded were resolved
# by declaring the source: `Toh:3861` in master-tsongkhapa/meta.json (月称《入
# 中论》is a real Tengyur text Tsongkhapa's tradition treats as its own
# foundation) and `J36nB348` in master-ouyi/meta.json (《灵峰宗论》is Ouyi's own
# collected works). Neither needed a B1 contract change — both simply belonged
# in the declared set. See CHANGELOG.md for the maintainer decision. The six the
# bare-id sweep found on 2026-09-14 were resolved the same way, never entered
# here.
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


# `BDRC W-number` in a persona's own rules names a field, it is not an id:
# master-tsongkhapa says 不得编造未验证的 BDRC W-number, master-atisha asks for
# a BDRC W-ID. `_FAMILY_ID` stays loose on purpose — in an answer, reading too
# much fails safe as fabricated (see the note above `_FOJIN_TEXT_LINK` in
# verify_citations.py) — so it reads both as ids. Only this prose sweep drops
# them: a real BDRC work id is W followed by a digit (W1GS56158, W1KG1252), the
# rule the auditor's own bare-W branch already applies.
_BDRC_FIELD_NAME = re.compile(r"^BDRC:W(?![0-9])")


def _bare_ids(text: str) -> list[str]:
    """Source ids written outside every 【…】 block: table cells, prose, frontmatter.

    `audit_answer` reads only bracketed citations, so a persona's routing table
    was invisible to this gate. master-xuanzang's SKILL.md sent 五位百法
    questions to `《百法明门论》，T31n1614` in a table cell; master-ouyi had an
    offline excerpt file for 《教觀綱宗》 T46n1939. Neither id was declared.

    Callers audit each id alone, as `【id】` with nothing after it, so a FoJin
    link in the same table row cannot make it `live`: in an answer a link can
    vouch for one citation, but in the persona's own material a link is not a
    declaration.
    """
    ids = extract_citation_ids(_BLOCK.sub(" ", text))
    return [cid for cid in ids if not _BDRC_FIELD_NAME.match(cid)]


@dataclass(frozen=True)
class Finding:
    master: str
    citation: str
    path: str


def find_undeclared(prebuilt_dir: Path, reach: Counter | None = None) -> list[Finding]:
    """Every citation the personas' own material makes that meta.json omits.

    `reach`, when given, counts what was read: bracketed citations the audit
    could resolve to an id, and bare ids outside brackets.
    """
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
            # Declared titles, as reaudit-report.py and test-fidelity.py already
            # pass them. Without them a source with no sutra number is unreadable:
            # master-yinguang's own 【《印光法師文鈔正編》卷一】 examples counted as
            # nothing, and the sweep read fewer citations after the Wenchao was
            # re-declared. An alias only makes a block readable; it cannot turn an
            # undeclared id into a declared one.
            titles = load_title_aliases(persona.name, base=str(prebuilt_dir))
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
            bracketed = audit_answer(declared, text, aliases, titles)
            undeclared = list(bracketed["fabricated"])
            bare = _bare_ids(text)
            for cid in bare:
                undeclared += audit_answer(declared, f"【{cid}】", aliases)["fabricated"]
            if reach is not None:
                reach["bracketed"] += sum(
                    len(bracketed[bucket]) for bucket in ("offline", "live", "fabricated")
                )
                reach["bare"] += len(bare)
            for citation in dict.fromkeys(undeclared):
                findings.append(
                    Finding(persona.name, citation, str(doc.relative_to(prebuilt_dir.parent)))
                )
    return findings


def main() -> int:
    reach: Counter = Counter()
    findings = find_undeclared(PREBUILT_DIR, reach)
    print(
        f"Read {reach['bracketed']} bracketed citations and {reach['bare']} bare "
        "source ids in the personas' own docs."
    )
    if not reach["bracketed"] or not reach["bare"]:
        print(
            "FAIL: the sweep read nothing of one kind — it is not looking at what "
            "it claims to check."
        )
        return 1
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
