#!/usr/bin/env python3
"""
RAG Query — runtime FoJin retrieval for teacher skills.

Usage:
    python3 tools/rag_query.py search "如何念佛" --sources cbeta --top_k 5
    python3 tools/rag_query.py semantic "什么是空性" --top_k 5
    python3 tools/rag_query.py dict "般若"
    python3 tools/rag_query.py kg "印光" --type person
"""

import argparse
import sys
import os

# Ensure tools/ is on the path so we can import fojin_bridge
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fojin_bridge import create_bridge, FojinUnavailableError


def format_search_results(data: dict) -> str:
    """Format keyword search results for LLM consumption."""
    items = data.get("items") or data.get("results") or []
    if not items:
        return "未找到相关结果。"

    lines = []
    for i, item in enumerate(items, 1):
        title = item.get("title", "无标题")
        source = item.get("source", item.get("collection", ""))
        score = item.get("score", item.get("relevance", ""))
        snippet = item.get("highlight", item.get("snippet", item.get("content", "")))
        text_id = item.get("text_id", item.get("id", ""))

        lines.append(f"── 结果 {i} ──")
        lines.append(f"标题: {title}")
        if source:
            lines.append(f"来源: {source}")
        if score:
            lines.append(f"相关度: {score}")
        if text_id:
            lines.append(f"FoJin链接: https://fojin.app/texts/{text_id}")
        if snippet:
            # Truncate long snippets
            snippet_str = str(snippet)
            if len(snippet_str) > 500:
                snippet_str = snippet_str[:500] + "..."
            lines.append(f"摘要: {snippet_str}")
        lines.append("")

    total = data.get("total", len(items))
    lines.insert(0, f"共找到 {total} 条结果，显示前 {len(items)} 条：\n")
    return "\n".join(lines)


def format_semantic_results(data: dict) -> str:
    """Format semantic search results for LLM consumption."""
    items = data.get("items") or data.get("results") or []
    if not items:
        return "语义检索未找到相关经文。"

    lines = [f"语义检索返回 {len(items)} 条相关经文：\n"]
    for i, item in enumerate(items, 1):
        title = item.get("title", "无标题")
        source = item.get("source", item.get("collection", ""))
        score = item.get("score", item.get("similarity", ""))
        content = item.get("content", item.get("snippet", item.get("text", "")))
        text_id = item.get("text_id", item.get("id", ""))
        juan = item.get("juan_num", item.get("juan", ""))

        lines.append(f"── 经文 {i} ──")
        lines.append(f"标题: {title}")
        if source:
            lines.append(f"来源: {source}")
        if score:
            lines.append(f"相似度: {score}")
        if text_id:
            link = f"https://fojin.app/texts/{text_id}"
            if juan:
                link += f"/juan/{juan}"
            lines.append(f"FoJin链接: {link}")
        if content:
            content_str = str(content)
            if len(content_str) > 500:
                content_str = content_str[:500] + "..."
            lines.append(f"经文内容: {content_str}")
        lines.append("")

    return "\n".join(lines)


def format_dict_results(data: dict) -> str:
    """Format dictionary search results for LLM consumption."""
    items = data.get("items") or data.get("results") or []
    if not items:
        return "词典中未找到该术语。"

    lines = [f"词典检索返回 {len(items)} 条释义：\n"]
    for i, item in enumerate(items, 1):
        headword = item.get("headword", item.get("term", item.get("word", "")))
        definition = item.get("definition", item.get("content", item.get("meaning", "")))
        source_dict = item.get("source", item.get("dictionary", item.get("dict_name", "")))

        lines.append(f"── 释义 {i} ──")
        if headword:
            lines.append(f"词条: {headword}")
        if source_dict:
            lines.append(f"出处词典: {source_dict}")
        if definition:
            def_str = str(definition)
            if len(def_str) > 800:
                def_str = def_str[:800] + "..."
            lines.append(f"释义: {def_str}")
        lines.append("")

    return "\n".join(lines)


def format_kg_results(data: dict) -> str:
    """Format knowledge graph entity results for LLM consumption."""
    items = data.get("items") or data.get("results") or data.get("entities") or []
    if not items:
        return "知识图谱中未找到相关实体。"

    lines = [f"知识图谱检索返回 {len(items)} 个实体：\n"]
    for i, item in enumerate(items, 1):
        name = item.get("name", item.get("label", ""))
        etype = item.get("entity_type", item.get("type", ""))
        desc = item.get("description", item.get("summary", ""))
        relations = item.get("relations", item.get("edges", []))
        entity_id = item.get("id", item.get("entity_id", ""))

        lines.append(f"── 实体 {i} ──")
        if name:
            lines.append(f"名称: {name}")
        if etype:
            lines.append(f"类型: {etype}")
        if entity_id:
            lines.append(f"FoJin链接: https://fojin.app/kg/entities/{entity_id}")
        if desc:
            desc_str = str(desc)
            if len(desc_str) > 500:
                desc_str = desc_str[:500] + "..."
            lines.append(f"描述: {desc_str}")
        if relations:
            lines.append("关系:")
            for rel in relations[:10]:
                predicate = rel.get("predicate", rel.get("relation", ""))
                target = rel.get("target", rel.get("object", rel.get("name", "")))
                if predicate and target:
                    lines.append(f"  - {predicate} → {target}")
        lines.append("")

    return "\n".join(lines)


def cmd_search(args):
    bridge = create_bridge()
    result = bridge.search_texts(args.query, sources=args.sources, size=args.top_k)
    print(format_search_results(result))


def cmd_semantic(args):
    bridge = create_bridge()
    result = bridge.semantic_search(args.query, top_k=args.top_k)
    print(format_semantic_results(result))


def cmd_dict(args):
    bridge = create_bridge()
    result = bridge.search_dictionary(args.query)
    print(format_dict_results(result))


def cmd_kg(args):
    bridge = create_bridge()
    result = bridge.search_kg_entities(args.query, entity_type=args.type)
    print(format_kg_results(result))


def main():
    parser = argparse.ArgumentParser(
        description="RAG Query — FoJin 佛教文献实时检索工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = subparsers.add_parser("search", help="关键词搜索经文")
    p_search.add_argument("query", help="搜索关键词")
    p_search.add_argument("--sources", default=None, help="限定来源，如 cbeta")
    p_search.add_argument("--top_k", type=int, default=5, help="返回条数 (默认 5)")
    p_search.set_defaults(func=cmd_search)

    # semantic
    p_sem = subparsers.add_parser("semantic", help="语义向量检索")
    p_sem.add_argument("query", help="语义查询")
    p_sem.add_argument("--top_k", type=int, default=5, help="返回条数 (默认 5)")
    p_sem.set_defaults(func=cmd_semantic)

    # dict
    p_dict = subparsers.add_parser("dict", help="佛学词典查询")
    p_dict.add_argument("query", help="查询术语")
    p_dict.set_defaults(func=cmd_dict)

    # kg
    p_kg = subparsers.add_parser("kg", help="知识图谱实体搜索")
    p_kg.add_argument("query", help="实体名称")
    p_kg.add_argument("--type", default=None, help="实体类型，如 person, text, school")
    p_kg.set_defaults(func=cmd_kg)

    args = parser.parse_args()

    try:
        args.func(args)
    except FojinUnavailableError:
        print("[FoJin API 当前不可用]")
        print("无法检索真实经文。法师将仅基于预置 teaching.md 回答。")
        print("建议：")
        print("- 稍后重试")
        print("- 检查网络连接")
        print("- 或在 fojin.app 直接查阅原典")
        sys.exit(0)
    except ConnectionError as e:
        print(f"[错误] 无法连接 FoJin API: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[错误] 检索失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
