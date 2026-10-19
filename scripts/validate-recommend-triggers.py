#!/usr/bin/env python3
"""Check that every persona's advertised Chinese triggers route back to it.

A persona is reachable two ways. Inside a host, the model reads the SKILL.md
frontmatter `description` ("Use when user asks about 南传佛教, 上座部 …
Triggers include "南传"、"巴利" …") and decides. From the terminal,
`master-skill recommend` scores the persona's meta.json
`search_scope.keywords` plus routing.json. Nothing tied the two together, so
they drifted: on 2026-10-19 `recommend "南传佛教怎么修"` and
`recommend "噶举派"` fell through to the default pairing (Kumārajīva and
Yinguang, both 汉传) although Ajahn Chah, Buddhaghosa and Milarepa list those
words in their own descriptions.

This script runs the real router — `node bin/cli.mjs recommend <term> --json`
— on every Chinese trigger a persona's description names, and fails when the
persona is not among the masters returned. Re-implementing the scoring here
would test a copy of the router, not the router.

A trigger may legitimately route elsewhere (a word that is really a request
for a teaching mode, or one shared so widely that three other masters win the
tie). Those go in EXEMPT with the reason. The list is checked both ways: an
exemption whose trigger now routes correctly, or no longer appears in the
description, is itself an error — a stale excuse reads like a live one.

Usage
-----
    python scripts/validate-recommend-triggers.py          # exit 1 on any problem
    python scripts/validate-recommend-triggers.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from _skill_io import PREBUILT_DIR, ROOT, load_frontmatter

CLI = ROOT / "bin" / "cli.mjs"
HAN = re.compile(r"[㐀-鿿]+")

# slug -> {trigger: why it does not route back to this persona}
_THERAVADA = (
    "README's 你的状况 table sends 上座部 to Buddhaghosa alone; the router fills "
    "up to three masters on any hit, so giving all three Theravāda personas the "
    "word would answer every 上座部 question with all three. 南传 does reach them"
)

EXEMPT: dict[str, dict[str, str]] = {
    "master-ajahn-chah": {"上座部": _THERAVADA},
    "master-mahasi-sayadaw": {"上座部": _THERAVADA},
    "master-huineng": {
        "禅": "single character: below routing.json min_keyword_length",
    },
    "master-nagarjuna": {
        "空": "single character: below routing.json min_keyword_length",
    },
    "master-fazang": {
        "法藏": "also 法藏比丘, Amitābha's name before awakening — a Pure Land "
                "question would land on Fazang; 法藏大师 and 贤首 are keywords",
    },
    "master-milarepa": {
        "觉受": "fires inside ordinary 感觉受…; 禅定觉受 is the keyword",
        "明空": "fires inside 说明空性; 明空双运 is the keyword",
    },
    "master-tsongkhapa": {
        "缘起性空": "four personas hold it, one per tradition; the three-master cap "
                    "and slug order keep Buddhaghosa, Kumārajīva, Nāgārjuna",
        "达赖喇嘛传承根基": "a description of lineage, not a query anyone types",
        "戒律": "four personas hold it; the three-master cap keeps one per tradition "
                "and slug order — Ajahn Chah, Atiśa, Daoxuan",
    },
}


def description_triggers(description: str) -> list[str]:
    """Chinese terms from the "asks about …" list and the "Triggers include" quotes."""
    terms: list[str] = []
    about = re.search(r"asks about (.*?)(?:, or wants|$)", description)
    if about:
        for item in about.group(1).split(","):
            terms.extend(HAN.findall(item))
    quoted = description.split("Triggers include", 1)
    if len(quoted) == 2:
        for item in re.findall(r'"([^"]+)"', quoted[1]):
            if "{" in item or "【" in item:
                continue
            terms.extend(HAN.findall(item))
    seen: set[str] = set()
    return [t for t in terms if not (t in seen or seen.add(t))]


def persona_triggers(prebuilt: Path = PREBUILT_DIR) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for skill in sorted(prebuilt.glob("master-*/SKILL.md")):
        meta_path = skill.parent / "meta.json"
        if not meta_path.is_file():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if not meta.get("search_scope", {}).get("keywords"):
            continue  # teaching modes carry no persona keywords
        front = load_frontmatter(skill.read_text(encoding="utf-8")) or {}
        out[skill.parent.name] = description_triggers(str(front.get("description", "")))
    return out


def route(term: str) -> dict:
    proc = subprocess.run(
        ["node", str(CLI), "recommend", term, "--json"],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"recommend {term!r} exited {proc.returncode}: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def check(prebuilt: Path = PREBUILT_DIR, exempt: dict | None = None) -> tuple[list[str], int]:
    exempt = EXEMPT if exempt is None else exempt
    triggers = persona_triggers(prebuilt)
    pairs = [(slug, t) for slug, terms in triggers.items() for t in terms]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda p: route(p[1]), pairs))
    problems: list[str] = []
    for (slug, term), data in zip(pairs, results):
        names = [m["name"] for m in data.get("masters", [])]
        reached = slug in names
        excused = term in exempt.get(slug, {})
        if not reached and not excused:
            got = ", ".join(names) or data.get("command") or data.get("kind")
            problems.append(f"{slug}: trigger 「{term}」 routes to {got} ({data['resolvedBy']})")
        elif reached and excused:
            problems.append(f"{slug}: exemption for 「{term}」 is stale — it now routes here")
    for slug, terms in exempt.items():
        for term in terms:
            if term not in triggers.get(slug, []):
                problems.append(f"{slug}: exemption for 「{term}」 is stale — not in the description")
    return problems, len(pairs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows runners default to cp1252
    problems, checked = check()
    if not checked:
        problems.append("no description triggers found — the parser read nothing")
    if args.json:
        print(json.dumps({"checked": checked, "problems": problems}, ensure_ascii=False, indent=2))
    else:
        for p in problems:
            print(f"  FAIL {p}")
        status = "FAIL" if problems else "PASS"
        print(f"{status}: {checked} description triggers checked, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
