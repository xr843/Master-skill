#!/usr/bin/env python3
"""离线检索指定 master 的 sources/ 和 references/。"""

import argparse
import json
import os
import re
import sys

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prebuilt")


def parse_sections(text):
    """按 ## 标题分段，返回 [(title, body), ...]"""
    sections = []
    parts = re.split(r'^## ', text, flags=re.MULTILINE)
    for part in parts[1:]:
        lines = part.split('\n', 1)
        title = lines[0].strip()
        body = lines[1] if len(lines) > 1 else ''
        sections.append((title, body))
    return sections


def search(master, query, brief=False):
    keywords = query.split()
    results = []

    for subdir in ("sources", "references"):
        dirpath = os.path.join(BASE, master, subdir)
        if not os.path.isdir(dirpath):
            continue
        for fname in sorted(os.listdir(dirpath)):
            if fname == "INDEX.md" or not fname.endswith(".md"):
                continue
            fpath = os.path.join(dirpath, fname)
            content = open(fpath, encoding="utf-8").read()
            for title, body in parse_sections(content):
                full = title + "\n" + body
                # OR 匹配：任一关键词命中即可
                if not any(kw in full for kw in keywords):
                    continue
                # 清理 body 前 200 字
                clean = re.sub(r'\n{2,}', '\n', body).strip()
                preview = clean[:200]
                results.append({
                    "section": title,
                    "preview": preview,
                    "file": os.path.join(subdir, fname),
                })

    return results


def main():
    parser = argparse.ArgumentParser(description="离线检索 master 的 sources 和 references")
    parser.add_argument("--master", required=True, help="大师 ID，如 master-zhiyi")
    parser.add_argument("--q", required=True, help="搜索关键词（空格分隔，OR 匹配）")
    parser.add_argument("--json", action="store_true", dest="as_json", help="JSON 格式输出")
    parser.add_argument("--brief", action="store_true", help="仅输出段标题和文件路径")
    args = parser.parse_args()

    results = search(args.master, args.q, args.brief)

    if not results:
        print(f"未找到包含「{args.q}」的段落。")
        return

    if args.as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.brief:
        for r in results:
            print(f"[{r['section']}] → {r['file']}")
    else:
        for i, r in enumerate(results):
            if i > 0:
                print("---")
            print(f"## {r['section']}")
            print(r['preview'])
            print(f"📂 {r['file']}")


if __name__ == "__main__":
    main()
