"""Offline tests for the capability skills (buddhist-quote-trace, buddhist-citation) and the MCP server.

Every network call goes through an injected opener; nothing here touches the internet.
"""
from __future__ import annotations

import importlib.util
import io
import json
import re
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CAP = ROOT / "capabilities"
TRACE_SCRIPTS = CAP / "buddhist-quote-trace" / "scripts"
CITE_SCRIPTS = CAP / "buddhist-citation" / "scripts"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(TRACE_SCRIPTS))
bcite = _load("bcite", TRACE_SCRIPTS / "bcite.py")
qtrace = _load("qtrace", TRACE_SCRIPTS / "qtrace.py")
mcp = _load("master_skill_mcp", ROOT / "mcp" / "master_skill_mcp.py")


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def opener_for(routes):
    """routes: list of (substring, payload | Exception). First match wins; payloads are JSON-encoded."""
    calls = []

    def opener(request, timeout=None):
        url = request.full_url
        calls.append((url, request.data))
        for needle, payload in routes:
            if needle in url:
                if isinstance(payload, BaseException):
                    raise payload
                if callable(payload):
                    payload = payload(request)
                return Response(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        raise AssertionError(f"unexpected URL {url}")

    opener.calls = calls
    return opener


def http_error(code: int, retry_after: str | None = None):
    headers = {"Retry-After": retry_after} if retry_after else {}
    return urllib.error.HTTPError("https://x", code, "err", headers, None)


NO_SLEEP = dict(sleep=lambda s: None, clock=lambda: 0.0)


@pytest.fixture(autouse=True)
def _reset_throttle():
    qtrace._last.clear()


# ----------------------------------------------------------------- packaging

def test_vendored_resolver_is_identical():
    for name in ("bcite.py", "t2s.txt"):
        assert (TRACE_SCRIPTS / name).read_bytes() == (CITE_SCRIPTS / name).read_bytes(), (
            f"capabilities/buddhist-quote-trace/scripts/{name} drifted from buddhist-citation's copy"
        )


@pytest.mark.parametrize("skill", ["buddhist-quote-trace", "buddhist-citation"])
def test_skill_frontmatter_fits_every_host(skill):
    text = (CAP / skill / "SKILL.md").read_text(encoding="utf-8")
    front = text.split("---", 2)[1]
    name = re.search(r"^name: (.+)$", front, re.M).group(1).strip()
    description = re.search(r"^description: (.+)$", front, re.M).group(1).strip()
    assert name == skill
    # claude.ai rejects uploads whose description is over 200 characters.
    assert len(description.encode("utf-8")) <= 200
    for script in re.findall(r"python3 (scripts/\S+\.py)", text):
        assert (CAP / skill / script).is_file(), script


def test_catalog_registers_capabilities():
    catalog = json.loads((ROOT / "skill-catalog.json").read_text(encoding="utf-8"))
    caps = {s["name"]: s for s in catalog["skills"] if s["kind"] == "capability"}
    assert set(caps) == {"buddhist-quote-trace", "buddhist-citation"}
    for name, entry in caps.items():
        assert entry["source"] == f"capabilities/{name}"


def test_scripts_use_only_the_standard_library():
    import ast

    stdlib = getattr(sys, "stdlib_module_names", None)
    if stdlib is None:
        pytest.skip("sys.stdlib_module_names needs Python 3.10+")
    allowed = set(stdlib) | {"bcite", "qtrace", "__future__"}
    for path in [TRACE_SCRIPTS / "qtrace.py", TRACE_SCRIPTS / "bcite.py", ROOT / "mcp" / "master_skill_mcp.py"]:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for mod in names:
                assert mod.split(".")[0] in allowed, f"{path.name} imports {mod}"


def test_misattribution_entries_are_well_formed():
    path = CAP / "buddhist-quote-trace" / "data" / "misattributions.json"
    if not path.exists():
        pytest.skip("misattributions.json not yet written")
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = set()
    for entry in data["entries"]:
        assert entry["id"] not in ids
        ids.add(entry["id"])
        assert entry["lang"] in {"zh", "en"}
        assert entry["status"] in {"misattributed", "paraphrase", "later_saying"}
        assert entry["text"].strip()
        assert entry["explanation_en"].strip() and entry["explanation_zh"].strip()
        assert entry["evidence"], entry["id"]


# ----------------------------------------------------------------- bcite

@pytest.mark.parametrize("citation, expected", [
    ("T48n2008", {"scheme": "cbeta", "work": "T2008"}),
    ("T2008", {"scheme": "cbeta", "work": "T2008"}),
    ("T235", {"scheme": "cbeta", "work": "T0235"}),
    ("J36nB348", {"scheme": "cbeta", "work": "JB348"}),
    ("X0434", {"scheme": "cbeta", "work": "X0434"}),
    ("SN 22.59", {"scheme": "suttacentral", "uid": "sn22.59"}),
    ("Dhp 5", {"scheme": "suttacentral", "uid": "dhp5"}),
    ("snp1.8", {"scheme": "suttacentral", "uid": "snp1.8"}),
    ("W22272", {"scheme": "bdrc", "rid": "W22272"}),
    ("bdr:MW22272", {"scheme": "bdrc", "rid": "MW22272"}),
    ("Toh 3871", {"scheme": "toh", "number": "3871"}),
    ("hello world", {"scheme": None}),
])
def test_parse(citation, expected):
    assert bcite.parse(citation) == expected


def test_titles_agree_folds_traditional_and_abbreviations():
    assert bcite.titles_agree("六祖大师法宝坛经", "六祖大師法寶壇經") is True
    assert bcite.titles_agree("坛经", "六祖大師法寶壇經") is True
    assert bcite.titles_agree("金刚经", "六祖大師法寶壇經") is False
    assert bcite.titles_agree("Platform Sutra", "六祖大師法寶壇經") is None


def test_resolve_cbeta_found_and_missing():
    work = {"num_found": 1, "results": [{"work": "T2008", "file": "T48n2008", "title": "六祖大師法寶壇經", "juan": 1}]}
    out = bcite.resolve("T2008", "坛经", opener=opener_for([("work=T2008", work)]))
    assert (out["exists"], out["canonical"], out["title_matches"]) == (True, "T48n2008", True)
    out = bcite.resolve("T9999", opener=opener_for([("work=T9999", {"num_found": 0, "results": []})]))
    assert out["exists"] is False


def test_network_failure_is_not_checked_never_false():
    out = bcite.resolve("T2008", opener=opener_for([("cbdata", urllib.error.URLError("offline"))]))
    assert out["exists"] is None and "not checked" in out["note"]


def test_suttacentral_range_resolution():
    empty = [{"uid": None}]
    listing = [{"uid": "dhp"}, {"uid": "dhp1-20", "acronym": "Dhp 1–20", "translated_title": "Pairs", "translations": []}]
    out = bcite.resolve("Dhp 5", opener=opener_for([("suttaplex/dhp5", empty), ("suttaplex/dhp", listing)]))
    assert (out["exists"], out["canonical"]) == (True, "dhp1-20")
    out = bcite.resolve("SN 99.99", opener=opener_for([("suttaplex/sn99.99", empty), ("suttaplex/sn99", empty)]))
    assert out["exists"] is False


def test_bdrc_404_means_missing():
    out = bcite.resolve("W1KG14334", opener=opener_for([("W1KG14334", http_error(404))]))
    assert out["exists"] is False


def test_toh_is_link_only():
    out = bcite.resolve("Toh 3871")
    assert out["exists"] is None and out["url"].endswith("toh3871.html")


# ----------------------------------------------------------------- qtrace: text handling

def test_split_and_detect():
    parts = qtrace.split_sentences("一切有为法，如梦幻泡影。Peace comes from within. Do not seek it without.\n放下屠刀")
    assert parts == ["一切有为法，如梦幻泡影。", "Peace comes from within.", "Do not seek it without.", "放下屠刀"]
    assert [qtrace.detect_lang(p) for p in parts] == ["zh", "en", "en", "zh"]
    assert qtrace.split_sentences("What you think, you become. 色即是空，空即是色。") == ["What you think, you become.", "色即是空，空即是色。"]
    long = "，".join(["色即是空空即是色"] * 30)
    assert all(len(p) <= qtrace.MAX_CHARS for p in qtrace.split_sentences(long))


ENTRIES = [
    {"id": "en-peace", "lang": "en", "text": "Peace comes from within. Do not seek it without.", "variants": [],
     "status": "misattributed", "explanation_en": "x", "explanation_zh": "x", "evidence": ["u"]},
    {"id": "zh-tudao", "lang": "zh", "text": "放下屠刀，立地成佛", "variants": [],
     "status": "later_saying", "explanation_en": "x", "explanation_zh": "x", "evidence": ["X0434"]},
]


def test_misattribution_matching():
    assert qtrace.match_misattribution("peace comes from within; do not seek it without!", "en", ENTRIES)["id"] == "en-peace"
    assert qtrace.match_misattribution("放下屠刀，立地成佛。", "zh", ENTRIES)["id"] == "zh-tudao"
    assert qtrace.match_misattribution("放下屠刀", "zh", ENTRIES) is None  # too short a fragment of the entry
    assert qtrace.match_misattribution("Peace", "en", ENTRIES) is None


# ----------------------------------------------------------------- qtrace: Chinese

def fojin_item(text, verdict, found=(True,), source_class="sutra", cid="T0235"):
    return {"text": text, "result": {"verdict": verdict, "source_class": source_class, "segments": [
        {"text": text, "found": f, "sources": [{"cbeta_id": cid, "title_zh": "金剛般若波羅蜜經", "juan_num": 1,
                                               "canon_class": source_class, "reader_url": "https://fojin.app/texts/7/read"}] if f else []}
        for f in found]}}


def test_zh_verdict_mapping():
    sentences = ["一切有为法", "应无所住而生心", "好好学习天天向上", "一切有为法，我编的", "放下屠刀，立地成佛"]

    def reply(request):
        sent = json.loads(request.data)["sentences"]
        assert sent == sentences
        return {"items": [
            fojin_item(sent[0], "sutra"),
            fojin_item(sent[1], "variant"),
            fojin_item(sent[2], "absent", found=(False,)),
            fojin_item(sent[3], "partial", found=(True, False)),
            fojin_item(sent[4], "not_sutra", source_class="later", cid="X0434"),
        ]}

    out = qtrace.trace(sentences=sentences, opener=opener_for([("fojin.app", reply)]), entries=ENTRIES, **NO_SLEEP)
    verdicts = [i["verdict"] for i in out["items"]]
    assert verdicts == ["found", "close", "not_found", "partial", "known_misattribution"]
    assert out["items"][0]["sources"][0]["id"] == "T0235"
    assert "未见不等于伪造" in out["items"][2]["note"]
    assert out["items"][4]["canon_verdict"] == "found" and out["items"][4]["source_class"] == "later"


def test_zh_batches_of_eight():
    sentences = [f"第{i}句经文如是" for i in range(11)]
    sizes = []

    def reply(request):
        sent = json.loads(request.data)["sentences"]
        sizes.append(len(sent))
        return {"items": [fojin_item(s, "sutra") for s in sent]}

    qtrace.trace(sentences=sentences, opener=opener_for([("fojin.app", reply)]), entries=[], **NO_SLEEP)
    assert sizes == [8, 3]


def test_zh_failure_is_unverifiable_never_not_found():
    out = qtrace.trace(sentences=["一切有为法"], opener=opener_for([("fojin.app", urllib.error.URLError("down"))]),
                       entries=[], **NO_SLEEP)
    assert out["items"][0]["verdict"] == "unverifiable"
    assert out["items"][0]["check_url"].startswith("https://fojin.ai/")


def test_zh_retries_429_then_succeeds():
    state = {"n": 0}
    waits = []

    def reply(request):
        state["n"] += 1
        if state["n"] == 1:
            raise http_error(429, "7")
        return {"items": [fojin_item("一切有为法", "sutra")]}

    out = qtrace.trace(sentences=["一切有为法"], opener=opener_for([("fojin.app", reply)]), entries=[],
                       sleep=waits.append, clock=lambda: 0.0)
    assert out["items"][0]["verdict"] == "found"
    assert 7.0 in waits


# ----------------------------------------------------------------- qtrace: English

SC_HIT = {"uid": "dhp1-20", "author_uid": "sujato", "acronym": "Dhp 1–20", "name": "Pairs"}
SC_SEGMENTS = {"translation_text": {"dhp5:1": "For never is hatred ", "dhp5:2": "laid to rest by hate, ",
                                    "dhp5:3": "it’s laid to rest by love: "}}


def test_en_verbatim_across_segment_breaks():
    routes = [("search/instant", {"hits": [SC_HIT]}), ("api/suttas/dhp1-20/sujato", {"translation": {}}),
              ("bilarasuttas/dhp1-20/sujato", SC_SEGMENTS)]
    out = qtrace.trace(sentences=["For never is hatred laid to rest by hate."], opener=opener_for(routes), entries=[], **NO_SLEEP)
    item = out["items"][0]
    assert item["verdict"] == "found" and item["sources"][0]["id"] == "dhp1-20"


def test_en_without_a_verbatim_match_is_unverifiable():
    routes = [("search/instant", {"hits": [SC_HIT]}), ("api/suttas/", {"translation": {}}),
              ("bilarasuttas/", SC_SEGMENTS)]
    out = qtrace.trace(sentences=["Hatred is conquered by love alone in this world of ours."], opener=opener_for(routes),
                       entries=[], **NO_SLEEP)
    assert out["items"][0]["verdict"] == "unverifiable" and out["items"][0]["sources"] == []
    out = qtrace.trace(sentences=["Something nobody ever wrote anywhere at all."],
                       opener=opener_for([("search/instant", {"hits": []})]), entries=[], **NO_SLEEP)
    assert out["items"][0]["verdict"] == "unverifiable"


def test_en_known_fake_short_circuits_network():
    opener = opener_for([])
    out = qtrace.trace(sentences=["Peace comes from within. Do not seek it without."], opener=opener, entries=ENTRIES, **NO_SLEEP)
    assert out["items"][0]["verdict"] == "known_misattribution" and opener.calls == []


# ----------------------------------------------------------------- MCP

def rpc(*messages):
    out = io.StringIO()
    mcp.serve(io.StringIO("\n".join(json.dumps(m) for m in messages) + "\n"), out)
    return [json.loads(line) for line in out.getvalue().splitlines()]


def test_mcp_handshake_and_tools(monkeypatch):
    monkeypatch.setattr(mcp.bcite, "resolve", lambda c, t=None: {"input": c, "exists": True})
    replies = rpc(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "resolve_citation", "arguments": {"citation": "T2008"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "trace_quotes", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "nope", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 6, "method": "bogus"},
    )
    assert [r["id"] for r in replies] == [1, 2, 3, 4, 5, 6]  # the notification gets no reply
    assert replies[0]["result"]["protocolVersion"] == "2025-03-26"
    assert {t["name"] for t in replies[1]["result"]["tools"]} == {"trace_quotes", "resolve_citation"}
    assert replies[2]["result"]["structuredContent"] == {"input": "T2008", "exists": True}
    assert replies[3]["result"]["isError"] is True
    assert replies[4]["error"]["code"] == -32602
    assert replies[5]["error"]["code"] == -32601


def test_canon_outranks_the_misattribution_list():
    entries = [{"id": "zh-x", "lang": "zh", "text": "一切有为法，如梦幻泡影", "variants": [], "status": "misattributed",
                "explanation_en": "x", "explanation_zh": "x", "evidence": ["u"]}]
    reply = lambda request: {"items": [fojin_item("一切有为法，如梦幻泡影", "sutra")]}
    out = qtrace.trace(sentences=["一切有为法，如梦幻泡影"], opener=opener_for([("fojin.app", reply)]), entries=entries, **NO_SLEEP)
    assert out["items"][0]["verdict"] == "found"
    assert out["items"][0]["misattribution_conflict"]["id"] == "zh-x"


def test_clauses_found_in_different_works_are_partial():
    item = {"text": "万法皆空，因果不空", "result": {"verdict": "sutra", "source_class": "sutra", "segments": [
        {"text": "万法皆空", "found": True, "sources": [{"cbeta_id": "T0001"}]},
        {"text": "因果不空", "found": True, "sources": [{"cbeta_id": "T0002"}]}]}}
    out = qtrace.trace(sentences=["万法皆空，因果不空"], opener=opener_for([("fojin.app", {"items": [item]})]), entries=[], **NO_SLEEP)
    assert out["items"][0]["verdict"] == "partial" and "不同典籍" in out["items"][0]["note"]
    item["result"]["segments"][1]["sources"].append({"cbeta_id": "T0001"})
    out = qtrace.trace(sentences=["万法皆空，因果不空"], opener=opener_for([("fojin.app", {"items": [item]})]), entries=[], **NO_SLEEP)
    assert out["items"][0]["verdict"] == "found" and out["items"][0]["sources"][0]["id"] == "T0001"
