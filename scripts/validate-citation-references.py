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
from verify_citations import audit_answer  # noqa: E402

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
KNOWN_UNDECLARED = {
    ("master-tsongkhapa", "Toh:3861"): (
        "SKILL.md:125 and sources/INDEX.md:15 prescribe 【月称《入中论》§第六章】"
        "（Toh 3861）. Toh 3861 is Candrakirti's Madhyamakavatara — a real id, not a "
        "hallucination — but meta.json declares five sources and none is it. Resolve by "
        "declaring it (this persona may cite Candrakirti's root text) or by deleting the "
        "example (it may cite only what Tsongkhapa wrote). Those assert different things."
    ),
    ("master-ouyi", "J36n0348"): (
        "references/teaching.md cites 【《灵峰宗论》】 — Ouyi's own collected works — with a "
        "cbetaonline.dila.edu.tw link to J36n0348, which meta.json does not declare. Two "
        "fixes: declare J36n0348, or extend the B1 live-citation rule to accept CBETA "
        "Online links the way it accepts fojin.app ones. The contract currently names only FoJin."
    ),
}


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


def _declared_ids(meta_path: Path) -> set[str]:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    ids = {s["id"] for s in meta.get("sources", []) if s.get("id")}
    ids.update(meta.get("search_scope", {}).get("primary_cbeta_ids", []))
    return ids


def find_undeclared(prebuilt_dir: Path) -> list[Finding]:
    """Every citation the personas' own material makes that meta.json omits."""
    findings: list[Finding] = []
    for persona in sorted(Path(prebuilt_dir).iterdir()):
        meta_path = persona / "meta.json"
        if not persona.is_dir() or not meta_path.is_file():
            continue
        declared = _declared_ids(meta_path)
        if not declared:
            continue  # nothing to audit against; see master-debate
        docs = [persona / "SKILL.md"]
        docs += sorted(persona.glob("sources/*.md"))
        docs += sorted(persona.glob("references/*.md"))
        for doc in docs:
            if not doc.is_file():
                continue
            text = _strip_template_citations(doc.read_text(encoding="utf-8"))
            for citation in dict.fromkeys(audit_answer(declared, text)["fabricated"]):
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
