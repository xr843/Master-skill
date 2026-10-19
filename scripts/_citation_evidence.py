"""Only labelled original excerpts support direct quotations.

Local excerpts are incomplete: no match means unknown, not fabrication.

Two halves, both tuned on the archived claude-sonnet-4-6 sweep (240 answers,
1838 unverified quotes before this rule set) and a hand check against CBETA
of the tsongkhapa / fazang / nagarjuna misses (2026-10-19): 52 of 100 misses
were not quotations at all, 21 were already in the local excerpts.

* **Extraction** keeps only spans the answer presents as the words of a
  source (`_claims_quotation`). Quotation marks in these answers mostly mark
  terms, the asker's misconceptions, the model's own maxims or suggested
  follow-up questions; a blockquote is just as often a callout or a citation
  line. Whatever is dropped here is never checked, so the rules only drop a
  span that has *no* sign of being presented as a quotation.
* **Matching** strips what the model wrapped around the words — parenthetical
  glosses like 「我说即是无（空）」, citation lines and links inside a
  blockquote — and splits on ellipses. Every segment must occur verbatim in
  one and the same declared work: two genuine halves from two books are a
  splice, not a quotation. There is deliberately no fuzzy match: 「无」 written
  as 「空」 is exactly the kind of one-character change that needs a ruling.
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
_CITATION = re.compile(r"【[^】]+】")
_URL = re.compile(r"https?://\S+")
_SOURCE_LABEL = re.compile(r"(?m)^\s*\**\s*出处\s*\**\s*[:：]")
# Elisions split a quotation into segments; each must be verbatim on its own.
# 「（中略）」 is an elision, not a gloss, so it splits instead of being dropped.
_ELISION = re.compile(r"……|…|⋯+|\.{3,}|[（(](?:上略|中略|下略|略)[）)]")
# Parenthetical glosses the model inserts into a quotation: 「无（空）」,
# 「（梵文对应 śūnyatā，即空）」, 「（颂 9 转述）」. Stripping them never lets
# altered words through — what remains must still be one verbatim run.
_GLOSS = re.compile(r"（[^（）]*）|\([^()]*\)")
_HAN = re.compile("[\u3400-\u9fff\U00020000-\U0002ffff]")
# Under this many Chinese characters a quoted span is, in this corpus, almost
# always a term or a phrase being discussed (「无我」「执筏」「迹门」「升」:
# 1158 of the 1838 sweep hits). Short spans still count when the answer
# introduces them as speech — 经云：「诸行无常。」 — see _claims_quotation.
_SHORT_QUOTE = 8
# A speech verb or a work title right before the quotation: 「经云：」
# 「老和尚说：」「《坛经》〈般若品〉明言」「引《坛经》」「五祖为说《金刚经》至」.
# Not 「《要解》的「六信」」: a title then 的/之 introduces a term from that work.
# Even a bare 说 counts for short spans: 「唯识说“转识成智”」 is a term, but
# 「龙树偈说“空亦复空”」 is a (mis)attributed quotation, and nothing tells them apart.
_SPEECH = r"(?:云|曰|(?<!所)谓|说|言|道|偈|颂|写道|记载|开示)"
_SPEECH_RIGHT_BEFORE = re.compile(
    r"(?:" + _SPEECH + r"[^\s，。、；：！？,.;:!?“”「」\"]{0,4}|[》〉][^\s，。、；：！？,.;:!?“”「」\"的之]{0,4})"
    r"\s*[:：]?$"
)
# Earlier in the same clause, for spans of _SHORT_QUOTE or more: 「巴利经典同样说，
# 涅槃是“……”」「阿底峡反复强调，“……”」「所谓「……」，此禅门内亦有明言」.
_SPEECH_IN_CLAUSE = re.compile(r"云|曰|谓|说|言|道|偈|颂|记载|开示|强调|主张|指出|教导|告诫|[》〉]")
# The speaker named right before (「蕅益大师“教宗天台，行归净土”」), or the span
# called a saying right after (「闻“应无所住而生其心”一句」「以“……”一语」).
_SPEAKER_RIGHT_BEFORE = re.compile(r"(?:大师|祖师|和尚|尊者|菩萨|法师|禅师|论师|佛陀|世尊|如来)$")
_SAYING_RIGHT_AFTER = re.compile(r"[*_」』”\"’]*\s*(?:一句|一语|此语|此句|这句|等句|之语|之句|之说)")
_CLAUSE_START = re.compile(r"[。！？!?\n]")
_SENTENCE_END = re.compile(r"[。！？!?][\s*_」』”\"’]*$")
# Between a quotation and the citation that follows it: only closing marks,
# punctuation, markdown emphasis, line breaks, or a 「出处：」 label.
_ADJACENT_CITATION = re.compile(
    r"\s*(?:[*_，。、；：！？,.;:!?）)」』”\"’>\s]|出处)*\s*【"
)
_ADJACENT_TITLE = re.compile(r"\s*[（(]\s*《")
_PARAGRAPH_BREAK = re.compile(r"\n[ \t>]*\n")
# A paragraph that is only a citation line: 「【《中论》卷4，T30n1564】→ …」「出处：【…】」.
_CITATION_LINE = re.compile(r"\s*(?:>\s*)*[*_]*\s*(?:出处\s*[*_]*\s*[:：]\s*)?[*_]*\s*【")
_QUOTE_OPEN = "“「\"‘『"


def normalize_quote(text: str) -> str:
    text = _simplifier().convert(unicodedata.normalize("NFKC", text)).casefold()
    return "".join(c for c in text if c.isalnum())


def load_quote_evidence(master_dir: Path, declared_ids: set[str],
                        title_aliases: dict[str, str] | None = None) -> dict[str, list[str]]:
    """Original excerpts per declared id.

    ``title_aliases`` (declared title → id, see ``load_title_aliases``) is what
    resolves a compiled teaching cited by its Chinese title alone:
    【《虚云和尚法汇》·开示·篇名】 carries no id, so without it every excerpt of
    the 《法汇》 — and every answer quoting it — resolved to no id at all, and
    all 49 of xuyun's quotations in the 2026-10-19 sweep counted as unverified
    however verbatim they were.
    """
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
            cited = audit_answer(declared_ids, citation.group(), title_aliases=title_aliases)
            for cid in set(cited["offline"]):
                evidence.setdefault(cid, []).append(passage)
    return evidence


def _core(quote: str) -> str:
    """The quoted words: no citation lines, links or 「出处：」 labels."""
    return _SOURCE_LABEL.sub("", _URL.sub("", _CITATION.sub("", quote)))


def _segments(quote: str) -> list[tuple[str, str]]:
    """(as written, glosses stripped) normalized, per elided segment."""
    segments = []
    for part in _ELISION.split(_core(quote)):
        stripped = normalize_quote(_GLOSS.sub("", part))
        if stripped:
            segments.append((normalize_quote(part), stripped))
    return segments


def _supported(segments: list[tuple[str, str]], passages: list[str]) -> bool:
    return all(
        any(raw in passage or stripped in passage for passage in passages)
        for raw, stripped in segments
    )


def _claims_quotation(answer: str, start: int, end: int, core: str,
                      embedded: bool) -> bool:
    """Is this span presented as the words of a source?

    Signs the answer itself gives, any one of which is enough:

    * traditional characters in the span — copied from a source text;
    * a citation inside the span, or right after it (only punctuation, line
      breaks or 「出处：」 between), or a parenthesised 《title》 right after;
    * a speech verb or work title directly before it (「经云：」「明言」「》」).

    A span of _SHORT_QUOTE or more Chinese characters also counts when

    * it is introduced by a colon or a dash (「老和尚说：\n\n> ……」「珠网——」),
      a speech verb occurs earlier in the same clause, the speaker is named
      right before it, or it is called a saying right after (「……”一句」);
    * it stands alone on its line, or is a blockquote wrapped in quotation
      marks (「> “菩萨以普贤行愿为本……”」);
    * a citation follows later in the same paragraph, or the paragraph is
      followed directly by a citation line.

    A shorter span counts only with a citation beside it, a speech verb right
    before it, or as a whole sentence (ending 。！？) after a colon or dash —
    otherwise it is a term (「无我」「执筏」), not a quotation.

    Spans with no sign at all are dropped: in the sweep they are terms, the
    asker's words, misconceptions, the model's maxims and disclaimers, and
    suggested follow-up questions. Whatever is kept is then matched.
    """
    tail = answer[end:end + 40]
    adjacent = embedded or bool(_ADJACENT_CITATION.match(tail) or _ADJACENT_TITLE.match(tail))
    # A citation right before is not a title introducing the span: its 《》 would
    # read as 「》」. 「【《坛经》】云：」 still ends in 云：.
    lead = re.sub(r"[\s>*_「“\"‘『]+$", "", _CITATION.sub("", answer[max(0, start - 60):start]))
    right_before = bool(_SPEECH_RIGHT_BEFORE.search(lead))
    introduced = lead.endswith(("：", ":", "——", "—"))
    words = _GLOSS.sub("", core)
    # Traditional characters in a span are copied from a source text: 「若心有
    # 不善，“念佛往生路遠”」 misquotes the 坛经's 「念佛往生難到」.
    if _simplifier().convert(words) != words:
        return True
    if len(_HAN.findall(words)) < _SHORT_QUOTE:
        return right_before or adjacent or (introduced and bool(_SENTENCE_END.search(words)))
    if adjacent or right_before or introduced:
        return True
    if _SPEECH_IN_CLAUSE.search(_CLAUSE_START.split(lead)[-1]):
        return True
    if _SPEAKER_RIGHT_BEFORE.search(lead) or _SAYING_RIGHT_AFTER.match(answer, end):
        return True
    line_start = answer.rfind("\n", 0, start) + 1
    line_end = answer.find("\n", end)
    line_end = len(answer) if line_end < 0 else line_end
    if (answer[start:start + 1] in _QUOTE_OPEN
            and re.fullmatch(r"[\s>*_]*", answer[line_start:start])
            and re.fullmatch(r"[\s*_，。,.]*", answer[end:line_end])):
        return True
    if answer[start:end].lstrip(" \t>*_").startswith(tuple(_QUOTE_OPEN)) and \
            answer[start:end].lstrip().startswith(">"):
        return True
    brk = _PARAGRAPH_BREAK.search(answer, end - 1 if answer[end - 1:end] == "\n" else end)
    para_end = brk.start() if brk else len(answer)
    if _CITATION.search(answer, end, para_end):
        return True
    return bool(brk and _CITATION_LINE.match(answer, brk.end()))


def _inside(block: tuple[int, int, str], position: int) -> bool:
    return block[0] <= position < block[1]


def unsupported_quotes(answer: str, evidence: dict[str, list[str]],
                       declared_ids: set[str] | None = None,
                       title_aliases: dict[str, str] | None = None) -> list[dict[str, str]]:
    unknown: list[dict[str, str]] = []
    blocks = [(match.start(), match.end(), re.sub(r"(?m)^[ \t]*>\s?", "", match.group()))
              for match in _BLOCKQUOTES.finditer(answer)]
    claimed_blocks = [
        block for block in blocks
        if _segments(block[2])
        and _claims_quotation(answer, block[0], block[1], _core(block[2]),
                              bool(_CITATION.search(block[2])))
    ]
    candidates = list(claimed_blocks)
    for match in _QUOTES.finditer(answer):
        quote = next(g for g in match.groups() if g is not None)
        host = next((block for block in blocks if _inside(block, match.start())), None)
        # A blockquote that is nothing but this quotation is checked once, as
        # the blockquote; before, the two were reported as two misses.
        if host in claimed_blocks and normalize_quote(_core(host[2])) == normalize_quote(_core(quote)):
            continue
        claimed = bool(_segments(quote)) and (
            _claims_quotation(answer, match.start(), match.end(), _core(quote),
                              bool(_CITATION.search(quote)))
            # A longer quotation inside a blockquote that is itself presented
            # as a quotation inherits that claim: 「言：\n\n> 「甲」\n> 「乙」」.
            or (host in claimed_blocks
                and len(_HAN.findall(_GLOSS.sub("", _core(quote)))) >= _SHORT_QUOTE)
        )
        if claimed:
            candidates.append((match.start(), match.end(), quote))
    candidates.sort()
    for start, end, quote in candidates:
        embedded = _CITATION.search(quote)
        segments = _segments(quote)
        tail = answer[end:end + 400]
        citation = embedded or _CITATION.search(tail)
        preceding = answer[max(0, start - 400):start]
        previous = list(_CITATION.finditer(preceding))
        if previous and not embedded:
            gap = preceding[previous[-1].end():]
            if len(gap) <= 32 and re.fullmatch(r"\s*(?:(?:经)?(?:云|曰|说|言)|原文|经文|写道|记载)?\s*[:：]?\s*", gap):
                citation = previous[-1]
        if not citation:
            if not previous:
                continue
            citation = previous[-1]
        ids = audit_answer(declared_ids or set(evidence), citation.group(),
                           title_aliases=title_aliases)["offline"]
        if not any(_supported(segments, evidence.get(cid, [])) for cid in ids):
            unknown.append({"quote": quote, "citation": citation.group()})
    return unknown
