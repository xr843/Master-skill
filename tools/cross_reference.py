#!/usr/bin/env python3
"""
Cross-Reference — find connections between teachers using FoJin KG.

Usage:
    python3 tools/cross_reference.py lineage "印光" "蕅益"
    python3 tools/cross_reference.py concept "空性" --teachers xuanzang,kumarajiva
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Allow running from project root or tools/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from fojin_bridge import FojinBridge, create_bridge


# ── Teacher registry ────────────────────────────────────────────

PREBUILT_DIR = PROJECT_ROOT / "prebuilt"


def load_teacher_meta(slug: str) -> dict:
    """Load a teacher's meta.json by slug."""
    meta_path = PREBUILT_DIR / slug / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Teacher not found: {slug}")
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_teachers() -> list[str]:
    """Return all available teacher slugs."""
    return sorted(
        d.name for d in PREBUILT_DIR.iterdir()
        if d.is_dir() and (d / "meta.json").exists()
    )


def find_teacher_by_name(name: str) -> Optional[dict]:
    """Find a teacher by Chinese name, English name, or slug."""
    for slug in list_teachers():
        meta = load_teacher_meta(slug)
        if name in (
            meta.get("name"),
            meta.get("name_en"),
            meta.get("name_sa"),
            meta.get("name_bo"),
            meta.get("slug"),
            slug,
        ):
            return meta
    return None


# ── Lineage subcommand ──────────────────────────────────────────

def cmd_lineage(bridge: FojinBridge, person_a: str, person_b: str) -> str:
    """
    Search the KG for relationship paths between two people.

    Returns formatted text describing the lineage connection.
    """
    lines: list[str] = []
    lines.append(f"## 师承关系查询: {person_a} <-> {person_b}")
    lines.append("")

    # Search for both entities in the KG
    result_a = bridge.search_kg_entities(person_a, entity_type="person", limit=5)
    result_b = bridge.search_kg_entities(person_b, entity_type="person", limit=5)

    entities_a = result_a.get("data", result_a.get("results", []))
    entities_b = result_b.get("data", result_b.get("results", []))

    if not entities_a:
        lines.append(f"- 未在知识图谱中找到: {person_a}")
    if not entities_b:
        lines.append(f"- 未在知识图谱中找到: {person_b}")

    if not entities_a or not entities_b:
        lines.append("")
        lines.append("### 建议")
        lines.append("- 尝试使用不同的名称（法号、别名等）")
        lines.append("- 查看 prebuilt/ 目录下已有的法师配置")
        return "\n".join(lines)

    entity_a = entities_a[0]
    entity_b = entities_b[0]
    id_a = entity_a.get("id")
    id_b = entity_b.get("id")

    lines.append(f"### {person_a}")
    lines.append(f"- KG实体: {entity_a.get('name', person_a)} (ID: {id_a})")
    lines.append("")

    lines.append(f"### {person_b}")
    lines.append(f"- KG实体: {entity_b.get('name', person_b)} (ID: {id_b})")
    lines.append("")

    # Fetch relationship graphs for both, looking for teacher-student predicates
    lines.append("### 关系图谱")
    lines.append("")

    graph_a = bridge.get_kg_graph(
        id_a, depth=3, max_nodes=100,
        predicates="teacher_of,student_of,disciple_of,master_of"
    )

    nodes = {n["id"]: n for n in graph_a.get("nodes", [])}
    edges = graph_a.get("edges", graph_a.get("links", []))

    # Check if person_b appears in person_a's graph
    found_connection = False
    for node in nodes.values():
        node_name = node.get("name", "")
        if person_b in node_name or node.get("id") == id_b:
            found_connection = True
            break

    if found_connection:
        lines.append(f"在 {person_a} 的关系图谱中找到 {person_b}:")
        lines.append("")
        for edge in edges:
            src = nodes.get(edge.get("source"), {}).get("name", str(edge.get("source")))
            tgt = nodes.get(edge.get("target"), {}).get("name", str(edge.get("target")))
            pred = edge.get("predicate", edge.get("label", "related_to"))
            lines.append(f"  {src} --[{pred}]--> {tgt}")
    else:
        lines.append(f"在3层关系内未找到 {person_a} 与 {person_b} 的直接师承路径。")
        lines.append("")

        # Show each person's immediate relations for context
        lines.append(f"#### {person_a} 的师承关系:")
        for edge in edges[:10]:
            src = nodes.get(edge.get("source"), {}).get("name", str(edge.get("source")))
            tgt = nodes.get(edge.get("target"), {}).get("name", str(edge.get("target")))
            pred = edge.get("predicate", edge.get("label", "related_to"))
            lines.append(f"  {src} --[{pred}]--> {tgt}")

        graph_b = bridge.get_kg_graph(
            id_b, depth=2, max_nodes=50,
            predicates="teacher_of,student_of,disciple_of,master_of"
        )
        nodes_b = {n["id"]: n for n in graph_b.get("nodes", [])}
        edges_b = graph_b.get("edges", graph_b.get("links", []))

        lines.append("")
        lines.append(f"#### {person_b} 的师承关系:")
        for edge in edges_b[:10]:
            src = nodes_b.get(edge.get("source"), {}).get("name", str(edge.get("source")))
            tgt = nodes_b.get(edge.get("target"), {}).get("name", str(edge.get("target")))
            pred = edge.get("predicate", edge.get("label", "related_to"))
            lines.append(f"  {src} --[{pred}]--> {tgt}")

    # Check if both are prebuilt teachers and note shared traditions
    lines.append("")
    lines.append("### 传承交集分析")
    meta_a = find_teacher_by_name(person_a)
    meta_b = find_teacher_by_name(person_b)
    if meta_a and meta_b:
        scope_a = meta_a.get("search_scope", {})
        scope_b = meta_b.get("search_scope", {})
        shared_traditions = set(scope_a.get("traditions", [])) & set(scope_b.get("traditions", []))
        shared_keywords = set(scope_a.get("keywords", [])) & set(scope_b.get("keywords", []))

        if shared_traditions:
            lines.append(f"- 共同传承: {', '.join(shared_traditions)}")
        if shared_keywords:
            lines.append(f"- 共同关键词: {', '.join(shared_keywords)}")
        if not shared_traditions and not shared_keywords:
            lines.append("- 两位法师属于不同传承，无直接交集")
    else:
        lines.append("- 部分法师不在预置列表中，无法进行本地交集分析")

    return "\n".join(lines)


# ── Concept subcommand ──────────────────────────────────────────

def cmd_concept(bridge: FojinBridge, concept: str, teacher_slugs: list[str]) -> str:
    """
    Search the same concept across multiple teachers' primary sources.

    Returns formatted text comparing how different teachers discuss the concept.
    """
    lines: list[str] = []
    lines.append(f"## 跨传承概念对比: {concept}")
    lines.append("")

    # Dictionary lookup first
    lines.append("### 辞典释义")
    try:
        dict_result = bridge.search_dictionary_grouped(concept)
        entries = dict_result.get("data", dict_result.get("results", []))
        if entries:
            for group in entries[:3]:
                source = group.get("source", "unknown")
                items = group.get("entries", group.get("items", []))
                if items:
                    entry = items[0]
                    term = entry.get("term", entry.get("headword", concept))
                    definition = entry.get("definition", entry.get("content", ""))
                    # Truncate long definitions
                    if len(definition) > 200:
                        definition = definition[:200] + "..."
                    lines.append(f"- **{source}** [{term}]: {definition}")
        else:
            lines.append(f"- 未找到「{concept}」的辞典条目")
    except Exception as e:
        lines.append(f"- 辞典查询失败: {e}")

    lines.append("")

    # For each teacher, search their primary sources
    for slug in teacher_slugs:
        try:
            meta = load_teacher_meta(slug)
        except FileNotFoundError:
            lines.append(f"### {slug} (未找到)")
            lines.append(f"- 法师 '{slug}' 不在预置列表中")
            lines.append("")
            continue

        name = meta.get("name", slug)
        scope = meta.get("search_scope", {})
        traditions = scope.get("traditions", [])

        lines.append(f"### {name} ({', '.join(traditions)})")

        # Build source filter from primary CBETA/SuttaCentral IDs
        primary_ids = scope.get("primary_cbeta_ids", []) + scope.get("primary_suttacentral_ids", [])
        source_filter = ",".join(primary_ids) if primary_ids else None

        # Search in teacher's primary texts
        try:
            results = bridge.search_content(concept, sources=source_filter, size=5)
            hits = results.get("data", results.get("results", []))
            if hits:
                for hit in hits[:3]:
                    title = hit.get("title", hit.get("text_title", ""))
                    highlight = hit.get("highlight", hit.get("snippet", ""))
                    if isinstance(highlight, dict):
                        highlight = highlight.get("content", [""])[0]
                    if isinstance(highlight, list):
                        highlight = highlight[0] if highlight else ""
                    # Truncate
                    if len(highlight) > 150:
                        highlight = highlight[:150] + "..."
                    lines.append(f"- 《{title}》: {highlight}")
            else:
                lines.append(f"- 在主要典籍中未搜到「{concept}」的直接引用")
        except Exception as e:
            lines.append(f"- 搜索失败: {e}")

        # Also search dictionary with teacher-specific sources
        dict_sources = scope.get("dictionary_sources", [])
        if dict_sources:
            try:
                for ds in dict_sources[:2]:
                    dict_res = bridge.search_dictionary(concept, source=ds, size=1)
                    entries = dict_res.get("data", dict_res.get("results", []))
                    if entries:
                        entry = entries[0]
                        definition = entry.get("definition", entry.get("content", ""))
                        if len(definition) > 100:
                            definition = definition[:100] + "..."
                        lines.append(f"- [{ds}辞典]: {definition}")
            except Exception:
                pass  # Dictionary lookup is best-effort

        lines.append("")

    # Cross-tradition comparison summary
    lines.append("### 传承视角对比")
    tradition_map: dict[str, list[str]] = {}
    for slug in teacher_slugs:
        try:
            meta = load_teacher_meta(slug)
            scope = meta.get("search_scope", {})
            for t in scope.get("traditions", []):
                tradition_map.setdefault(t, []).append(meta.get("name", slug))
        except FileNotFoundError:
            pass

    for tradition, teachers in tradition_map.items():
        lines.append(f"- **{tradition}**: {', '.join(teachers)}")

    if len(tradition_map) > 1:
        lines.append("")
        lines.append(
            f"共涉及 {len(tradition_map)} 个传承，"
            f"建议对比各传承对「{concept}」的不同诠释角度。"
        )

    return "\n".join(lines)


# ── CLI ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Cross-reference Buddhist masters and concepts via FoJin KG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s lineage "印光" "蕅益"
  %(prog)s concept "空性" --teachers xuanzang,kumarajiva
  %(prog)s concept "止观" --teachers zhiyi,ouyi,xuyun
  %(prog)s list
""",
    )
    sub = parser.add_subparsers(dest="command")

    # lineage
    p_lineage = sub.add_parser("lineage", help="查询两人师承关系")
    p_lineage.add_argument("person_a", help="第一位人物名称")
    p_lineage.add_argument("person_b", help="第二位人物名称")

    # concept
    p_concept = sub.add_parser("concept", help="跨传承概念对比")
    p_concept.add_argument("concept", help="要比较的概念")
    p_concept.add_argument(
        "--teachers", "-t", required=True,
        help="法师slug列表，逗号分隔 (如: xuanzang,kumarajiva)"
    )

    # list
    sub.add_parser("list", help="列出所有可用法师")

    args = parser.parse_args()

    if args.command == "list":
        print("Available teachers:")
        for slug in list_teachers():
            meta = load_teacher_meta(slug)
            scope = meta.get("search_scope", {})
            traditions = ", ".join(scope.get("traditions", []))
            print(f"  {slug:16s}  {meta['name']}  ({traditions})")
        return

    if args.command is None:
        parser.print_help()
        return

    bridge = create_bridge()

    if args.command == "lineage":
        output = cmd_lineage(bridge, args.person_a, args.person_b)
    elif args.command == "concept":
        teacher_slugs = [s.strip() for s in args.teachers.split(",")]
        output = cmd_concept(bridge, args.concept, teacher_slugs)
    else:
        parser.print_help()
        return

    print(output)


if __name__ == "__main__":
    main()
