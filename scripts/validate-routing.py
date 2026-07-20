#!/usr/bin/env python3
"""Validate routing.json — the machine-readable master/mode routing table.

`master-skill recommend` and the `/master-help` skill both route off this
file. It exists because the routing knowledge used to live only as prose:
a weighted-match paragraph and a 24-row pairing table inside
prebuilt/compare/SKILL.md, plus a decision tree in
references/teaching-modes.md. Prose cannot be executed and cannot drift-check
itself — the original pairing table shipped three key collisions (`戒律`,
`道次第`, `中观/空性` each matched two or three rows), so which pairing a
query landed on depended on iteration order.

The central invariant this script enforces is therefore **pairwise
disjointness**: within `mode_rules`, and within `topic_pairings`, no keyword
may appear in two rows, and no keyword may be a substring of a keyword in
another row. Substring matters because `recommend` matches by containment —
if row A had `道次第` and row B had `菩提道次第`, a query mentioning the
latter would match both and the winner would be positional. Making that a CI
error forces collisions to be resolved when the data is authored.

Keyword data for personas is deliberately NOT duplicated into routing.json;
it stays in each prebuilt/<slug>/meta.json `search_scope.keywords`, so this
script also checks that every persona still carries usable keywords.

Checks
------
  1. version == 1 and the three top-level sections are well-formed
  2. every mode in `mode_rules` is a `kind: teaching-mode` skill in
     skill-catalog.json
  3. every master slug in `topic_pairings` / `default_pairing` is a
     `kind: persona` skill in skill-catalog.json
  4. `mode_rules` keyword sets are pairwise disjoint (incl. substrings)
  5. `topic_pairings` keyword sets are pairwise disjoint (incl. substrings)
  6. `mode_rules` `order` values are exactly 1..N with no gaps or ties
  7. every catalog persona is reachable from at least one pairing or the
     default pairing (no master can become unrecommendable)
  8. every catalog persona has a non-empty search_scope.keywords

Usage
-----
    python scripts/validate-routing.py            # exit 1 on any problem
    python scripts/validate-routing.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUTING_PATH = ROOT / "routing.json"
CATALOG_PATH = ROOT / "skill-catalog.json"
PREBUILT = ROOT / "prebuilt"


def _read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as err:
        return {"__error__": f"{p.name}: {err}"}


def _disjoint_problems(section: str, rows: list) -> list:
    """Report keyword collisions across rows.

    Two keywords collide when they are equal or one contains the other.
    Collisions inside a single row are fine (`观智` alongside `十六观智`
    is a deliberate broadening); collisions across rows are not, because
    they make the match order-dependent.
    """
    problems = []
    flat = []
    for row in rows:
        label = row.get("id") or row.get("mode") or "<unnamed>"
        for kw in row.get("keywords", []):
            flat.append((label, kw))

    for i, (label_a, kw_a) in enumerate(flat):
        for label_b, kw_b in flat[i + 1:]:
            if label_a == label_b:
                continue
            if kw_a == kw_b:
                problems.append(
                    f"{section}: keyword {kw_a!r} appears in both "
                    f"{label_a!r} and {label_b!r}"
                )
            elif kw_a in kw_b or kw_b in kw_a:
                shorter, longer = sorted((kw_a, kw_b), key=len)
                problems.append(
                    f"{section}: keyword {shorter!r} ({label_a!r}) is a "
                    f"substring of {longer!r} ({label_b!r}) — a query "
                    f"matching the longer one would match both"
                )
    return problems


def validate(root: Path = ROOT) -> list:
    problems = []

    routing = _read_json(root / "routing.json")
    if "__error__" in routing:
        return [f"cannot read routing.json ({routing['__error__']})"]
    catalog = _read_json(root / "skill-catalog.json")
    if "__error__" in catalog:
        return [f"cannot read skill-catalog.json ({catalog['__error__']})"]

    # 1 — shape
    if routing.get("version") != 1:
        problems.append("routing.json: version must be 1")

    mode_rules = routing.get("mode_rules")
    pairings = routing.get("topic_pairings")
    default_pairing = routing.get("default_pairing")
    if not isinstance(mode_rules, list) or not mode_rules:
        problems.append("routing.json: mode_rules must be a non-empty array")
        mode_rules = []
    if not isinstance(pairings, list) or not pairings:
        problems.append("routing.json: topic_pairings must be a non-empty array")
        pairings = []
    if not isinstance(default_pairing, list) or not default_pairing:
        problems.append("routing.json: default_pairing must be a non-empty array")
        default_pairing = []

    skills = catalog.get("skills", [])
    personas = {s["name"] for s in skills if s.get("kind") == "persona"}
    modes = {s["name"] for s in skills if s.get("kind") == "teaching-mode"}

    # 2 — modes resolve
    for rule in mode_rules:
        mode = rule.get("mode")
        if mode not in modes:
            problems.append(
                f"mode_rules: {mode!r} is not a kind:teaching-mode skill in "
                f"skill-catalog.json (known: {sorted(modes)})"
            )
        if not rule.get("keywords"):
            problems.append(f"mode_rules: {mode!r} has no keywords")

    # 3 — masters resolve
    referenced = set()
    for row in pairings:
        rid = row.get("id", "<unnamed>")
        if not row.get("keywords"):
            problems.append(f"topic_pairings: {rid!r} has no keywords")
        row_masters = row.get("masters", [])
        if not row_masters:
            problems.append(f"topic_pairings: {rid!r} has no masters")
        for slug in row_masters:
            referenced.add(slug)
            if slug not in personas:
                problems.append(
                    f"topic_pairings: {rid!r} references {slug!r}, which is "
                    f"not a kind:persona skill in skill-catalog.json"
                )
    for slug in default_pairing:
        referenced.add(slug)
        if slug not in personas:
            problems.append(
                f"default_pairing: {slug!r} is not a kind:persona skill in "
                f"skill-catalog.json"
            )

    # 4 / 5 — disjointness
    problems += _disjoint_problems("mode_rules", mode_rules)
    problems += _disjoint_problems("topic_pairings", pairings)

    # 6 — order is a clean 1..N
    orders = [r.get("order") for r in mode_rules]
    if sorted(o for o in orders if isinstance(o, int)) != list(
        range(1, len(mode_rules) + 1)
    ):
        problems.append(
            f"mode_rules: order values must be exactly 1..{len(mode_rules)} "
            f"with no gaps or ties (got {orders})"
        )

    # 7 — no unreachable persona
    for slug in sorted(personas - referenced):
        problems.append(
            f"coverage: persona {slug!r} appears in no topic_pairing and is "
            f"not in default_pairing — it can never be recommended"
        )

    # 8 — persona keywords still exist (recommend scores off them)
    for slug in sorted(personas):
        meta_path = PREBUILT / slug / "meta.json"
        if not meta_path.exists():
            problems.append(f"keywords: {slug} has no meta.json")
            continue
        meta = _read_json(meta_path)
        if "__error__" in meta:
            problems.append(f"keywords: {slug} meta.json unreadable")
            continue
        kws = (meta.get("search_scope") or {}).get("keywords")
        if not kws:
            problems.append(
                f"keywords: {slug} has empty search_scope.keywords — "
                f"`recommend` cannot score it"
            )

    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    problems = validate()

    if args.json:
        print(json.dumps({"ok": not problems, "problems": problems}, indent=2))
    elif problems:
        print(f"routing.json validation failed ({len(problems)} problem(s)):\n")
        for p in problems:
            print(f"  ✗ {p}")
        print()
    else:
        routing = _read_json(ROUTING_PATH)
        print(
            f"routing.json ok — {len(routing.get('mode_rules', []))} mode rules, "
            f"{len(routing.get('topic_pairings', []))} topic pairings, "
            f"all keyword sets pairwise disjoint."
        )

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
