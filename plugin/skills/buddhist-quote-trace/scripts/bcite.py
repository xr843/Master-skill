#!/usr/bin/env python3
"""Resolve a Buddhist canon citation to a canonical id, title and link.

    python3 bcite.py "T48n2008"
    python3 bcite.py "SN 22.59" "Dhp 5" "W22272" --title 六祖大师法宝坛经
    echo '{"citation": "T2008", "title": "坛经"}' | python3 bcite.py --json

Supported schemes:
    cbeta         T48n2008, T2008, T235, X0434, J36nB348      (cbdata.dila.edu.tw)
    suttacentral  SN 22.59, MN 10, AN 1.5, Dhp 5, Snp 1.8     (suttacentral.net)
    bdrc          W22272, MW22272                              (ldspdi.bdrc.io)
    toh           Toh 3871 / D3871                             (link only, not verified)

Output is JSON. `exists` is true / false / null; null means "not checked"
(network failure, or a scheme that cannot be verified online) — never read
null as false. Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENGINE = "buddhist-citation/1"
USER_AGENT = "master-skill-capability/1 (+https://github.com/xr843/Master-skill)"
TIMEOUT_S = 20.0

CBETA_WORKS = "https://cbdata.dila.edu.tw/stable/works"
CBETA_READ = "https://cbetaonline.dila.edu.tw/zh/{}"
SC_SUTTAPLEX = "https://suttacentral.net/api/suttaplex/{}"
SC_READ = "https://suttacentral.net/{}"
BDRC_RESOURCE = "https://ldspdi.bdrc.io/resource/{}.json"
BDRC_READ = "https://library.bdrc.io/show/bdr:{}"
TOH_READ = "https://read.84000.co/translation/toh{}.html"

_CBETA_FULL = re.compile(r"^([A-Z]{1,2})(\d{1,3})n([A-Z]?)(\d{1,4})([a-zA-Z]?)$")
_CBETA_SHORT = re.compile(r"^([A-Z]{1,2})([A-Z]?)(\d{1,4})([a-zA-Z]?)$")
_SC_BOOKS = {
    "dn": "dn", "mn": "mn", "sn": "sn", "an": "an", "kp": "kp", "khp": "kp",
    "dhp": "dhp", "ud": "ud", "iti": "iti", "it": "iti", "snp": "snp", "sn p": "snp",
    "thag": "thag", "thig": "thig", "vv": "vv", "pv": "pv", "ja": "ja",
}
_SC = re.compile(r"^(dn|mn|sn|an|kp|khp|dhp|ud|iti|it|snp|thag|thig|vv|pv|ja)\s*(\d+(?:\.\d+)*)$", re.I)
_BDRC = re.compile(r"^(?:bdrc:|bdr:)?(M?W[0-9][A-Za-z0-9_]*)$", re.I)
_TOH = re.compile(r"^(?:toh\.?|d)\s*(\d{1,4}[a-z]?)$", re.I)

_T2S: dict[str, str] | None = None


def _t2s() -> dict[str, str]:
    global _T2S
    if _T2S is None:
        _T2S = {}
        path = Path(__file__).with_name("t2s.txt")
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if len(line) == 2 and not line.startswith("#"):
                    _T2S[line[0]] = line[1]
    return _T2S


def simplify(text: str) -> str:
    table = _t2s()
    return "".join(table.get(ch, ch) for ch in text)


def _cjk_only(text: str) -> str:
    bare = re.sub(r"[（(][^）)]*[）)]", "", text or "")
    return "".join(ch for ch in simplify(bare) if "㐀" <= ch <= "鿿" or "豈" <= ch <= "﫿")


def _latin_key(text: str) -> str:
    """Fold diacritics, case, spaces and punctuation: 'Anattalakkhaṇa Sutta' -> 'anattalakkhanasutta'."""
    import unicodedata
    bare = unicodedata.normalize("NFKD", text or "")
    return re.sub(r"[^a-z0-9]", "", "".join(ch for ch in bare if not unicodedata.combining(ch)).lower())


def titles_agree(declared: str | None, actual: str | None) -> bool | None:
    """Declared title is the actual title, or an abbreviation of it (a subsequence),
    after folding traditional to simplified. None when either side has no CJK."""
    mine, theirs = _cjk_only(declared or ""), _cjk_only(actual or "")
    if not mine or not theirs:
        return None
    pos = 0
    for ch in theirs:
        if pos < len(mine) and mine[pos] == ch:
            pos += 1
    return pos == len(mine)


# --------------------------------------------------------------------------- parsing

def parse(citation: str) -> dict:
    """Recognise the scheme. Returns {"scheme": ..., ...}; scheme None if unknown."""
    raw = (citation or "").strip()
    compact = re.sub(r"\s+", "", raw)
    if re.match(r"^[a-z]{1,2}\d", compact):  # t2008, x0434: CBETA ids are upper case
        compact = compact[:2].upper() + compact[2:] if compact[1].isalpha() else compact[0].upper() + compact[1:]
    m = _CBETA_FULL.match(compact)
    if m:
        canon, vol, prefix, num, suffix = m.groups()
        return {"scheme": "cbeta", "work": f"{canon}{prefix}{num.zfill(4 if not prefix else 3)}{suffix}"}
    m = _SC.match(raw.replace(" ", " "))
    if m:
        book = _SC_BOOKS[m.group(1).lower()]
        return {"scheme": "suttacentral", "uid": f"{book}{m.group(2)}"}
    m = _TOH.match(raw)
    if m:
        return {"scheme": "toh", "number": m.group(1).lower()}
    m = _BDRC.match(compact)
    if m:
        rid = m.group(1)
        rid = "MW" + rid[2:] if rid[:2].upper() == "MW" else "W" + rid[1:]
        return {"scheme": "bdrc", "rid": rid}
    m = _CBETA_SHORT.match(compact)
    if m and m.group(4) != "n":  # "T48n" is a volume with the number missing, not a work
        canon, prefix, num, suffix = m.groups()
        if len(canon) == 2 and not prefix and len(num) <= 3:
            # JB348: canon J, prefixed number B348 (prefixed numbers have 3 digits;
            # two-letter canons such as GA, ZW, CC have 4).
            canon, prefix = canon[0], canon[1]
        return {"scheme": "cbeta", "work": f"{canon}{prefix}{num.zfill(4 if not prefix else 3)}{suffix}"}
    return {"scheme": None}


# --------------------------------------------------------------------------- network

def fetch_json(url: str, *, opener=None, retries: int = 2, sleep=time.sleep):
    """GET JSON. Raises on failure after retrying transient errors."""
    opener = opener or urllib.request.urlopen
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    attempt = 0
    while True:
        try:
            with opener(request, timeout=TIMEOUT_S) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code == 404:
                raise
            if attempt >= retries or error.code not in (429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, OSError, TimeoutError):
            if attempt >= retries:
                raise
        attempt += 1
        sleep(2.0 * attempt)


def _base(citation: str, parsed: dict) -> dict:
    return {
        "engine": ENGINE, "input": citation, "scheme": parsed.get("scheme"),
        "canonical": None, "exists": None, "title": None, "url": None,
        "title_matches": None, "note": None,
    }


def _resolve_cbeta(out: dict, parsed: dict, title: str | None, opener) -> dict:
    work = parsed["work"]
    out["url"] = CBETA_READ.format(work)
    data = fetch_json(f"{CBETA_WORKS}?{urllib.parse.urlencode({'work': work})}", opener=opener)
    results = data.get("results") or []
    if not results:
        out["exists"] = False
        out["note"] = f"CBETA has no work {work}"
        return out
    r = results[0]
    out.update({
        "exists": True, "canonical": r.get("file") or work, "work": r.get("work"),
        "title": r.get("title"), "byline": r.get("byline"), "juan_count": r.get("juan"),
        "dynasty": r.get("time_dynasty"), "category": r.get("category"),
    })
    out["title_matches"] = titles_agree(title, out["title"]) if title else None
    return out


def _sc_entry(data) -> dict | None:
    node = data[0] if isinstance(data, list) and data else data
    return node if isinstance(node, dict) and node.get("uid") else None


def _sc_range_parent(uid: str) -> tuple[str, int] | None:
    """dhp5 -> ("dhp", 5); an1.5 -> ("an1", 5)."""
    m = re.match(r"^([a-z]+(?:\d+(?:\.\d+)*)?)\.(\d+)$", uid) or re.match(r"^([a-z]+)(\d+)$", uid)
    return (m.group(1), int(m.group(2))) if m else None


def _resolve_sc(out: dict, parsed: dict, title: str | None, opener) -> dict:
    uid = parsed["uid"]
    entry = _sc_entry(fetch_json(SC_SUTTAPLEX.format(uid), opener=opener))
    if entry is None:
        parent = _sc_range_parent(uid)
        if parent:
            listing = fetch_json(SC_SUTTAPLEX.format(parent[0]), opener=opener)
            for node in listing if isinstance(listing, list) else []:
                cand = (node or {}).get("uid") or ""
                m = re.match(rf"^{re.escape(parent[0])}\.?(\d+)-(\d+)$", cand)
                if m and int(m.group(1)) <= parent[1] <= int(m.group(2)):
                    entry = node
                    out["note"] = f"{uid} is inside the range {cand}"
                    break
    if entry is None:
        out["exists"] = False
        out["note"] = f"SuttaCentral has no text {uid}"
        return out
    canonical = entry["uid"]
    out.update({
        "exists": True, "canonical": canonical, "acronym": entry.get("acronym"),
        "title": (entry.get("translated_title") or "").strip() or None,
        "pali_title": entry.get("original_title"), "root_lang": entry.get("root_lang"),
        "url": SC_READ.format(canonical),
        "translations": sorted({t.get("lang") for t in entry.get("translations") or [] if t.get("lang")}),
    })
    if title and re.search(r"[a-z]", title, re.I):
        mine = _latin_key(title).removesuffix("sutta").removesuffix("sutra")
        names = [_latin_key(x) for x in (out["title"], out["pali_title"], out.get("acronym")) if x]
        out["title_matches"] = bool(mine) and any(mine in n for n in names)
    return out


def _bdrc_labels(document: dict, rid: str) -> list[str]:
    labels = []
    for subject, props in (document or {}).items():
        if not subject.endswith("/" + rid):
            continue
        for key, values in props.items():
            if key.endswith(("prefLabel", "altLabel")):
                labels += [v.get("value") for v in values if isinstance(v, dict) and v.get("value")]
    return labels


def _resolve_bdrc(out: dict, parsed: dict, title: str | None, opener) -> dict:
    rid = parsed["rid"]
    out["url"] = BDRC_READ.format(rid)
    try:
        doc = fetch_json(BDRC_RESOURCE.format(rid), opener=opener)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            out["exists"] = False
            out["note"] = f"BDRC has no resource {rid}"
            return out
        raise
    out["exists"] = True
    out["canonical"] = rid
    labels = _bdrc_labels(doc, rid)
    if not labels and rid.startswith("W"):
        try:
            labels = _bdrc_labels(fetch_json(BDRC_RESOURCE.format("M" + rid), opener=opener), "M" + rid)
        except (urllib.error.URLError, OSError, ValueError):
            labels = []
    out["title"] = labels[0] if labels else None
    out["labels"] = labels
    if title and labels and re.search(r"[a-z]", title, re.I):
        # Wylie apostrophes are often dropped ("gsung bum" for "gsung 'bum") and word
        # order varies ("sgam po pa gsung 'bum" for "gsung 'bum/_sgam po pa/").
        words = lambda s: set(re.sub(r"[^a-z0-9 ]", "", re.sub(r"[/_()\-]", " ", s.lower())).split())
        out["title_matches"] = any(words(title) <= words(label) for label in labels)
    elif title:
        out["note"] = "BDRC titles are Tibetan/English; a Chinese title cannot be compared automatically"
    return out


def resolve(citation: str, title: str | None = None, *, opener=None) -> dict:
    parsed = parse(citation)
    out = _base(citation, parsed)
    scheme = parsed.get("scheme")
    if scheme is None:
        out["note"] = "unrecognised citation format"
        return out
    if scheme == "toh":
        out["canonical"] = f"Toh {parsed['number']}"
        out["url"] = TOH_READ.format(parsed["number"])
        out["note"] = "Tohoku numbers are not verified online; the 84000 link may be an untranslated stub"
        return out
    try:
        if scheme == "cbeta":
            return _resolve_cbeta(out, parsed, title, opener)
        if scheme == "suttacentral":
            return _resolve_sc(out, parsed, title, opener)
        return _resolve_bdrc(out, parsed, title, opener)
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as error:
        out["exists"] = None
        out["note"] = f"not checked: {type(error).__name__}: {error}"[:300]
        return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("citations", nargs="*")
    ap.add_argument("--title", help="declared title to check against the id")
    ap.add_argument("--json", action="store_true", help="read {citation, title} or a list of them from stdin")
    args = ap.parse_args(argv)
    if args.json:
        payload = json.load(sys.stdin)
        rows = payload if isinstance(payload, list) else [payload]
        results = [resolve(str(r.get("citation", "")), r.get("title")) for r in rows]
    else:
        if not args.citations:
            ap.error("give at least one citation")
        results = [resolve(c, args.title) for c in args.citations]
    out = results[0] if len(results) == 1 else {"engine": ENGINE, "results": results}
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
