"""Pilot only (pilot/quote-lookup): a look-up tool for personas, so a rule can
require that every quotation be retrieved before it is quoted.

`lookup_original(query)` searches, in order: the persona's own 原典 blocks,
the pinned 《印光法师文钞》 corpus when the persona declares it, and CBETA full
text. It returns the passages verbatim with the citation to use, so a
quotation can be copied rather than recalled.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path

CBETA = "https://cbdata.dila.edu.tw/stable/"
ROOT = Path(__file__).resolve().parents[1]
TOOL_NAME = "lookup_original"
DESCRIPTION = (
    "Search the original text of a passage before quoting it. Give a short "
    "phrase (4–20 Chinese characters) you remember from the passage. Returns "
    "verbatim passages with the citation to use: first this skill's own 原典 "
    "excerpts, then 《印光法师文钞》 when this skill declares it, then CBETA "
    "full text. Quote only what it returns; if nothing matches, do not use "
    "quotation marks."
)
SCHEMA = {
    "type": "object",
    "properties": {"query": {"type": "string"}},
    "required": ["query"],
}
_WINDOW = 90
_MAX_HITS = 5


@lru_cache(maxsize=1)
def _converters():
    from opencc import OpenCC
    return OpenCC("s2tw"), OpenCC("t2s")


def _simplified(text: str) -> str:
    return _converters()[1].convert(text)


def _traditional(text: str) -> str:
    return _converters()[0].convert(text).replace("爲", "為").replace("衆", "眾")


def _get(path: str):
    with urllib.request.urlopen(CBETA + path, timeout=30) as response:
        return json.load(response)


@lru_cache(maxsize=256)
def _work(work: str) -> dict:
    data = _get("works?" + urllib.parse.urlencode({"work": work}))
    return (data.get("results") or [{}])[0]


@lru_cache(maxsize=256)
def _juan_text(work: str, juan: int) -> str:
    data = _get("juans?" + urllib.parse.urlencode({"work": work, "juan": juan}))
    html = (data.get("results") or [""])[0]
    html = re.split(r"<div class=['\"]footnote", html)[0]
    html = re.sub(r'<span class="lb"[^>]*>.*?</span>', "", html)
    html = re.sub(r"<[^>]+>", "", html)
    return re.sub(r"\s+", "", html)


@lru_cache(maxsize=1)
def _wenchao() -> list[tuple[str, str]]:
    """(title, full text) of 正编、续编、三编, from the pinned 殆知阁 commit step 3i uses."""
    manifest = json.loads((ROOT / "tools" / "compiled-teaching-sources.json").read_text(encoding="utf-8"))
    out = []
    for corpus in manifest["corpora"]:
        if corpus.get("master") != "master-yinguang":
            continue
        for text in corpus.get("texts", []):
            scheme, rest = text["url"].split("://", 1)
            with urllib.request.urlopen(f"{scheme}://{urllib.parse.quote(rest)}", timeout=60) as response:
                out.append((text["title"], response.read().decode("utf-8")))
    return out


def _windows(text: str, needle: str, simplify: bool):
    """Original-text windows around each occurrence of ``needle``.

    ``needle`` is simplified and letters/digits only; the text is compared the
    same way (punctuation dropped), and the window is cut from the original.
    """
    keep = [(i, ch) for i, ch in enumerate(text) if ch.isalnum()]
    hay = "".join(ch for _, ch in keep)
    if simplify:
        hay = _simplified(hay)
    start = 0
    while True:
        k = hay.find(needle, start)
        if k < 0:
            return
        first, last = keep[k][0], keep[k + len(needle) - 1][0]
        yield text[max(0, first - _WINDOW): last + 1 + _WINDOW]
        start = k + len(needle)


class QuoteLookup:
    def __init__(self, master_dir: Path):
        self.master_dir = master_dir
        self.log: list[dict] = []
        self.rounds = 0
        self.max_rounds = 0
        self.agent = "main"
        meta = json.loads((master_dir / "meta.json").read_text(encoding="utf-8"))
        self.works = []
        for source in meta.get("sources", []):
            m = re.fullmatch(r"([A-Z]{1,2})\d+n(B?\d+)[a-z]?", str(source.get("id") or ""))
            if m and source.get("type") == "cbeta":
                self.works.append(m.group(1) + m.group(2))
        self.wenchao = any("文钞" in (s.get("title") or "") or "Wenchao" in (s.get("id") or "")
                           for s in meta.get("sources", []))

    def _own(self, needle: str) -> list[str]:
        hits = []
        for path in sorted((self.master_dir / "sources").glob("*.md")):
            for section in re.split(r"(?m)^#{1,3} ", path.read_text(encoding="utf-8")):
                block = re.search(r"(?m)^原典[^\n]*\n\s*\n?((?:>[^\n]*\n?)+)", section)
                if not block:
                    continue
                passage = re.sub(r"(?m)^>\s?", "", block.group(1)).replace("\n", "")
                citation = re.search(r"【[^】]+】", section[block.end():])
                for window in _windows(passage, needle, simplify=True):
                    hits.append(f"[本 skill 原典] {window}\n引用格式：{citation.group() if citation else '（见摘录）'}")
        return hits

    def _cbeta(self, needle: str) -> list[str]:
        # This persona's declared works first, then the whole canon.
        rows = []
        for work in self.works:
            data = _get("search?" + urllib.parse.urlencode({"q": _traditional(needle), "work": work, "rows": 5}))
            rows += data.get("results") or []
        data = _get("search?" + urllib.parse.urlencode({"q": _traditional(needle), "rows": 10}))
        rows += data.get("results") or []
        hits, seen = [], set()
        for row in rows:
            if (row.get("work"), row.get("juan")) in seen:
                continue
            seen.add((row.get("work"), row.get("juan")))
            work, juan = row.get("work"), row.get("juan")
            if not work or not juan:
                continue
            info = _work(work)
            text = _juan_text(work, int(juan))
            for window in _windows(text, needle, simplify=True):
                cite = f"【《{info.get('title') or row.get('title')}》卷{juan}，{info.get('file') or work}】"
                hits.append(f"[CBETA] {window}\n引用格式：{cite}（{info.get('byline') or ''}）")
                break
            if len(hits) >= _MAX_HITS:
                break
        return hits

    def call(self, name: str, arguments: dict) -> str:
        query = str((arguments or {}).get("query") or "").strip()
        needle = "".join(ch for ch in _simplified(query) if ch.isalnum())
        try:
            if name != TOOL_NAME:
                raise ValueError(f"unknown tool {name}")
            if len(needle) < 4:
                raise ValueError("query must have at least 4 characters")
            hits = self._own(needle)
            if self.wenchao and len(hits) < _MAX_HITS:
                for title, text in _wenchao():
                    for window in _windows(re.sub(r"\s+", "", text), needle, simplify=True):
                        hits.append(f"[{title}] {window}\n引用格式：【《{title}》】")
                        break
            if len(hits) < _MAX_HITS:
                hits += self._cbeta(needle)
        except Exception as error:  # noqa: BLE001 — a failed look-up is data for the model
            self.log.append({"tool": name, "query": query, "ok": False, "error": str(error)[:200]})
            return f"error: {error}"
        self.log.append({"tool": name, "query": query, "ok": True, "hits": len(hits)})
        if not hits:
            return "没有找到逐字相同的原文。不要给这句话加引号；写成「大意是……」并附出处。"
        return "\n\n".join(hits[:_MAX_HITS])
