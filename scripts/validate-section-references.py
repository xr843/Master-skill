#!/usr/bin/env python3
"""Gate: a "read `file.md` §section" instruction must land on something.

Every persona's SKILL.md routes a question to material: a decision tree says
读 `references/teaching.md` §参话头, a Quick Reference row says the same. The
model follows those pointers literally. Nothing checked that the section they
name exists, and the files they point into have been rewritten many times since
the routing was written — sections renamed to a book's real chapter titles,
material moved from references/ to sources/.

2026-09-16, measured across the repo: 18 of 198 section pointers in nine personas
named a section the target file does not have, and so did one in the generator's
own SKILL.md. Most were renames (§戒律根本 for 戒律为根本), but not all were
harmless:

  - master-milarepa routed 那洛六法 / 拙火 / 气脉明点 to
    `sources/grubum-excerpts.md` §拙火与气脉. That file has no such section on
    purpose — it lists tummo among what it deliberately does not hold, with the
    answer to give instead. The pointer sent the model to look for exactly the
    material the persona is forbidden to supply.
  - master-mahasi-sayadaw routed 十六观智 to §十六观智 in an excerpt file whose
    section is 观智次第 and which says the book numbers seventeen, not sixteen.
  - master-ajahn-chah sent 心的训练 to references/teaching.md; the section is in
    sources/teachings-excerpts.md.

A section counts as present when the name appears, ignoring punctuation and
spacing, in a heading of the target file or in a **bold label** — the persona
docs use bold labels (**十念法**, **数息观**) as sub-section markers, and a model
searching for the name finds either. Parenthesised glosses are optional on both
sides of the match, so §觉受与证悟 finds `6. 觉受 (nyams) 与证悟 (rtogs pa) 的区分`.
Prose may run on after a name (§版权分级 Tier B/C 流程), so trailing words split
off by spaces are dropped one at a time; the first word must still be found.

A path with a directory in it must name a file that exists even with no section.
A bare `teaching.md` without one is prose — the generator docs name the files
they produce that way — and is not a pointer.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREBUILT_DIR = ROOT / "prebuilt"

# The docs the model is told to follow: every persona and mode, and the
# generator skill with its references.
DOC_GLOBS = ("prebuilt/**/*.md", "SKILL.md", "references/*.md")

_PATH = re.compile(r"`((?:[\w-]+/)*[\w.-]+\.md)`")
# A section name ends at the next separator a routing line uses: `+`, a table
# pipe, CJK punctuation, a backtick or an opening gloss.
_SECTIONS = re.compile(r"(?:[ \t、]*§[^§`+＋\n，、；;|。（）()]*)+")
_SECTION = re.compile(r"§([^§、]*)")
_BOLD = re.compile(r"\*\*([^*\n]+)\*\*")
_GLOSS = re.compile(r"[（(][^（）()]*[）)]")
_NUMBERING = re.compile(r"^\s*(?:\d+\.|[①-⑳])\s*")
_NOISE = re.compile(r"[\s·、，,。.:：—\-–《》「」\"'`*§⚠️]")


def _norm(text: str) -> str:
    return _NOISE.sub("", _NUMBERING.sub("", text)).lower()


def anchor_forms(anchor: str) -> set[str]:
    """一个标题或粗体标签可被匹配的写法：连同括注，或去掉括注。"""
    return {_norm(re.sub(r"[（）()]", "", anchor)), _norm(_GLOSS.sub("", anchor))}


def anchors(lines: list[str]) -> list[str]:
    found = [line.lstrip("#").strip() for line in lines if line.startswith("#")]
    for line in lines:
        found.extend(_BOLD.findall(line))
    return found


def section_present(name: str, lines: list[str]) -> bool:
    forms = {form for anchor in anchors(lines) for form in anchor_forms(anchor)}
    words = name.split()
    while words:
        wanted = _norm(" ".join(words))
        if wanted and any(wanted in form for form in forms):
            return True
        words.pop()
    return not _norm(name)


def references(line: str) -> list[tuple[str, list[str]]]:
    """[(路径, [小节名…])]：这一行里的每个文件指针及其所指小节。"""
    out = []
    for m in _PATH.finditer(line):
        tail = _SECTIONS.match(line, m.end())
        names = []
        if tail:
            names = [n.strip() for n in _SECTION.findall(tail.group(0)) if n.strip()]
        out.append((m.group(1), names))
    return out


def _skill_root(doc: Path) -> Path:
    rel = doc.relative_to(ROOT)
    return ROOT / rel.parts[0] / rel.parts[1] if rel.parts[0] == "prebuilt" else ROOT


def resolve(doc: Path, rel: str) -> Path | None:
    for base in (_skill_root(doc), doc.parent, ROOT):
        if (base / rel).is_file():
            return base / rel
    return None


def dangling(docs: list[Path]) -> tuple[int, list[str]]:
    """(检查过的指针数, [问题…])。"""
    examined, problems = 0, []
    cache: dict[Path, list[str]] = {}
    for doc in docs:
        for number, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            if "{" in line:
                continue  # 模板行，如 `prebuilt/{slug}/…` 下的 `references/teaching.md`
            where = f"{doc.relative_to(ROOT)}:{number}"
            for rel, names in references(line):
                if "/" not in rel and not names:
                    continue  # 裸文件名是行文，不是指针
                examined += 1
                target = resolve(doc, rel)
                if target is None:
                    problems.append(f"{where}  `{rel}` does not exist")
                    continue
                if target not in cache:
                    cache[target] = target.read_text(encoding="utf-8").splitlines()
                for name in names:
                    if not section_present(name, cache[target]):
                        problems.append(f"{where}  `{rel}` has no section §{name}")
    return examined, problems


def model_facing_docs() -> list[Path]:
    return sorted({p for pattern in DOC_GLOBS for p in ROOT.glob(pattern) if p.is_file()})


def main() -> int:
    examined, problems = dangling(model_facing_docs())
    if examined == 0:
        print("FAIL: found no file pointers at all — this gate examined an empty set.")
        return 1
    if problems:
        print(f"FAIL: {len(problems)} of {examined} file pointer(s) do not land:")
        for problem in problems:
            print(f"  {problem}")
        print(
            "\nThe model follows these pointers literally. A section that is not there\n"
            "leaves it to improvise the material it was sent to read. Point at a heading\n"
            "or **bold label** the file actually has, or drop the § and name the file."
        )
        return 1
    print(f"OK: all {examined} file pointers land on a file and section that exist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
