"""Only labelled original excerpts support direct quotations.

Local excerpts are incomplete: no match means unknown, not fabrication.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from verify_citations import audit_answer

@lru_cache(maxsize=1)
def _simplifier():
    # Structural dry-runs are also used by the desktop baseline on plain Python.
    # The converter is required only when actual quotation evidence is checked.
    from opencc import OpenCC
    return OpenCC("t2s")

_QUOTES = re.compile(r'“([^“”]+)”|「([^「」]+)」|"([^"]+)"|‘([^‘’]+)’|『([^『』]+)』')
_BLOCKQUOTES = re.compile(r"(?m)(?:^[ \t]*>[^\n]*(?:\n|$))+")


def normalize_quote(text: str) -> str:
    text = _simplifier().convert(unicodedata.normalize("NFKC", text)).casefold()
    return "".join(c for c in text if c.isalnum())


def load_quote_evidence(master_dir: Path, declared_ids: set[str]) -> dict[str, list[str]]:
    evidence: dict[str, list[str]] = {}
    for path in sorted((master_dir / "sources").glob("*.md")):
        for section in re.split(r"(?m)^#{1,3} ", path.read_text(encoding="utf-8")):
            original = re.search(r"(?m)^原典[^\n]*\n\s*\n?((?:>[^\n]*\n?)+)", section)
            if not original:
                continue
            passage = normalize_quote(re.sub(r"(?m)^>\s?", "", original.group(1)))
            citation = re.search(r"【[^】]+】", section[original.end():])
            if not citation:
                continue
            for cid in set(audit_answer(declared_ids, citation.group())["offline"]):
                evidence.setdefault(cid, []).append(passage)
    return evidence


def unsupported_quotes(answer: str, evidence: dict[str, list[str]],
                       declared_ids: set[str] | None = None) -> list[dict[str, str]]:
    unknown: list[dict[str, str]] = []
    candidates = [(match.start(), match.end(), next(g for g in match.groups() if g is not None))
                  for match in _QUOTES.finditer(answer)]
    candidates += [(match.start(), match.end(), re.sub(r"(?m)^[ \t]*>\s?", "", match.group()))
                   for match in _BLOCKQUOTES.finditer(answer)]
    for start, end, quote in candidates:
        embedded = re.search(r"【[^】]+】", quote)
        normalized = normalize_quote(re.sub(r"【[^】]+】", "", quote))
        if not normalized:
            continue
        tail = answer[end:end + 400]
        citation = embedded or re.search(r"【[^】]+】", tail)
        preceding = answer[max(0, start - 400):start]
        previous = list(re.finditer(r"【[^】]+】", preceding))
        if previous and not embedded:
            gap = preceding[previous[-1].end():]
            if len(gap) <= 32 and re.fullmatch(r"\s*(?:(?:经)?(?:云|曰|说|言)|原文|经文|写道|记载)?\s*[:：]?\s*", gap):
                citation = previous[-1]
        if not citation:
            if not previous:
                continue
            citation = previous[-1]
        ids = audit_answer(declared_ids or set(evidence), citation.group())["offline"]
        if not any(normalized in passage for cid in ids for passage in evidence.get(cid, [])):
            unknown.append({"quote": quote, "citation": citation.group()})
    return unknown
