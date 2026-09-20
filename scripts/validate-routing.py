#!/usr/bin/env python3
"""Validate routing.json — the machine-readable master/mode routing table.

`master-skill recommend` and the `/master-help` skill both route off this
file. It exists because the routing knowledge used to live only as prose:
a weighted-match paragraph and a 24-row pairing table inside
prebuilt/compare-masters/SKILL.md, plus a decision tree in
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
    situations = routing.get("situations") or []
    if not isinstance(situations, list):
        problems.append("routing.json: situations must be an array")
        situations = []

    referenced = set()
    for section, rows in (("topic_pairings", pairings), ("situations", situations)):
        for row in rows:
            rid = row.get("id", "<unnamed>")
            if not row.get("keywords"):
                problems.append(f"{section}: {rid!r} has no keywords")
            row_masters = row.get("masters", [])
            if not row_masters:
                problems.append(f"{section}: {rid!r} has no masters")
            for slug in row_masters:
                referenced.add(slug)
                if slug not in personas:
                    problems.append(
                        f"{section}: {rid!r} references {slug!r}, which is "
                        f"not a kind:persona skill in skill-catalog.json"
                    )
    for slug in default_pairing:
        referenced.add(slug)
        if slug not in personas:
            problems.append(
                f"default_pairing: {slug!r} is not a kind:persona skill in "
                f"skill-catalog.json"
            )

    # 4 / 5 — disjointness within each section
    problems += _disjoint_problems("mode_rules", mode_rules)
    problems += _disjoint_problems("topic_pairings", pairings)
    problems += _disjoint_problems("situations", situations)

    # 5b — a situation keyword that also triggers a mode is dead code: the
    # mode layer short-circuits first, so the situation row can never fire.
    mode_kws = {kw for r in mode_rules for kw in r.get("keywords", [])}
    for row in situations:
        rid = row.get("id", "<unnamed>")
        for kw in row.get("keywords", []):
            for mkw in mode_kws:
                if kw == mkw or kw in mkw or mkw in kw:
                    problems.append(
                        f"situations: {rid!r} keyword {kw!r} collides with "
                        f"mode_rules keyword {mkw!r} — mode_rules is evaluated "
                        f"first, so this situation row is unreachable"
                    )

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
            f"coverage: persona {slug!r} appears in no topic_pairing or "
            f"situation and is not in default_pairing — it can never be "
            f"recommended"
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

    problems.extend(_prose_table_problems(root, routing))
    problems.extend(_master_help_problems(root, routing))

    return problems


def _prose_pairings(skill_md: Path) -> list[tuple[set, list]]:
    """compare-masters/SKILL.md 里那张「主题映射兜底」表，解析成 (关键词集合, 祖师)。"""
    rows: list[tuple[set, list]] = []
    for line in skill_md.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or "master-" not in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or cells[0].startswith("master-"):
            continue
        masters = [m.strip() for m in cells[1].split("+") if m.strip().startswith("master-")]
        keywords = {k.strip() for k in cells[0].split("/") if k.strip()}
        if masters and keywords:
            rows.append((keywords, masters))
    return rows


def _prose_table_problems(root: Path, routing: dict) -> list:
    """散文表必须与 routing.json 逐行一致。

    `compare-masters` 装到 `~/.claude/skills/` 时只带 SKILL.md 和 tests/ —— 仓库根的
    routing.json 不在里面。所以这张表不能删：运行时模型能读到的只有它。既然要留一份
    副本，就得有东西保证两份不分叉。

    2026-09-20 实测它们已经分叉了：routing.json 当初是靠**合并**消除碰撞的
    （`戒律/行持` 并入 `戒律/持戒/律仪/行持`、`中观` 从「唯识」行移到「般若/空性」行、
    `道次第` 从「七清净」行移走），而散文表原封不动保留着合并前的旧行。本文件开头那段
    「原始配对表有三处碰撞」说的正是这张表 —— 可执行的那份修好了，被模型读的那份没有。
    结果是同一个「戒律」既命中 xuyun+yinguang+ajahn-chah，又命中 xuyun+atisha+buddhaghosa。
    """
    problems: list = []
    skill_md = root / "prebuilt" / "compare-masters" / "SKILL.md"
    if not skill_md.exists():
        return ["prose table: prebuilt/compare-masters/SKILL.md is missing"]
    rows = _prose_pairings(skill_md)
    pairings = routing.get("topic_pairings") or []
    default = routing.get("default_pairing")
    if isinstance(default, dict):
        default = default.get("masters")
    expected = [(set(p.get("keywords") or []), list(p.get("masters") or [])) for p in pairings]
    expected.append(({"其他"}, list(default or [])))
    if len(rows) != len(expected):
        problems.append(
            f"prose table: compare-masters/SKILL.md has {len(rows)} pairing row(s), "
            f"routing.json has {len(expected)} (topic_pairings + default) — they must mirror each other"
        )
        return problems
    for index, ((got_kw, got_ms), (want_kw, want_ms)) in enumerate(zip(rows, expected), 1):
        if got_kw != want_kw:
            problems.append(
                f"prose table row {index}: keywords {sorted(got_kw)} != routing.json {sorted(want_kw)}"
            )
        if got_ms != want_ms:
            problems.append(
                f"prose table row {index}: masters {got_ms} != routing.json {want_ms}"
            )
    return problems


def _md_rows(text: str, header: str) -> list[tuple[list, list]]:
    """取 `header` 之后那张 markdown 表，每行切成 (第一列的 / 分词, master- 开头的项)。"""
    if header not in text:
        return []
    body = text[text.index(header) :]
    rows: list[tuple[list, list]] = []
    for line in body.splitlines()[1:]:
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-: "):
            continue
        masters = [m.strip() for m in cells[1].split("+") if m.strip().startswith("master-")]
        if masters:
            rows.append(([k.strip() for k in cells[0].split("/") if k.strip()], masters))
    return rows


def _master_help_problems(root: Path, routing: dict) -> list:
    """master-help 自带的三张路由表必须与 routing.json 一致。

    这个 skill 装到 `~/.claude/skills/` 时只带 SKILL.md 和 tests/ —— 仓库根的
    routing.json 不随行（插件装法才读得到，两种装法能力不同）。2026-09-20 实测：
    它的第 5–7 步（状况层 / 主题配对 / 兜底）在 npm 装法下**连数据都没有**，而
    SKILL 里却写着「读文件」。现在表随 skill 走，这道检查保证它们不分叉。
    """
    problems: list = []
    skill_md = root / "prebuilt" / "master-help" / "SKILL.md"
    if not skill_md.exists():
        return ["master-help: prebuilt/master-help/SKILL.md is missing"]
    text = skill_md.read_text(encoding="utf-8")

    for rule in routing.get("mode_rules") or []:
        listed = f"命中「{' / '.join(rule['keywords'])}」"
        if listed not in text:
            problems.append(
                f"master-help: the route order does not list {rule['mode']}'s keywords "
                f"exactly as routing.json has them"
            )

    got = _md_rows(text, "| 状况（用户原话） | 目标 | 说明 |")
    want = [(list(s.get("keywords") or []), list(s.get("masters") or [])) for s in routing.get("situations") or []]
    if got != want:
        problems.append(f"master-help: situations table {got} != routing.json {want}")

    got = _md_rows(text, "| 问题主题 | 配对祖师 |")
    default = routing.get("default_pairing")
    if isinstance(default, dict):
        default = default.get("masters")
    want = [(list(x.get("keywords") or []), list(x.get("masters") or [])) for x in routing.get("topic_pairings") or []]
    want.append((["其他"], list(default or [])))
    if got != want:
        problems.append("master-help: the topic pairing table does not mirror routing.json")
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
            f"{len(routing.get('situations', []))} situations, "
            f"{len(routing.get('topic_pairings', []))} topic pairings, "
            f"all keyword sets pairwise disjoint."
        )

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
