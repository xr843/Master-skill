#!/usr/bin/env python3
"""给定关键词，在指定 master 的 sources/*.md 中查找匹配段落，输出标准 CBETA 引用。"""

import argparse
import json
import os
import re
import sys

from _masterpaths import resolve_master_dir

# master feeds into os.path.join(...); restrict to a slug charset so a value
# like "../../etc" can never read files outside prebuilt/. Mirrors the
# isSafeName guard in bin/cli.mjs.
_SAFE_MASTER = re.compile(r"^[A-Za-z0-9_-]+$")


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


def find_citations(master_dir, text):
    sources_dir = os.path.join(master_dir, "sources")
    if not os.path.isdir(sources_dir):
        print(f"错误：找不到目录 {sources_dir}", file=sys.stderr)
        sys.exit(1)

    results = []
    for fname in sorted(os.listdir(sources_dir)):
        if fname == "INDEX.md" or not fname.endswith(".md"):
            continue
        fpath = os.path.join(sources_dir, fname)
        content = open(fpath, encoding="utf-8").read()
        for title, body in parse_sections(content):
            full = title + "\n" + body
            if text not in full:
                continue
            # 提取引用格式行
            for line in body.split('\n'):
                line_s = line.strip()
                if "【《" in line_s:
                    results.append({
                        "section": title,
                        "citation": line_s,
                        "file": fname,
                    })
    return results


def main():
    parser = argparse.ArgumentParser(description="在 master 的 sources 中查找关键词并输出 CBETA 引用")
    parser.add_argument("--master", required=True, help="大师 ID，如 master-zhiyi")
    parser.add_argument("--text", required=True, help="搜索关键词")
    parser.add_argument("--json", action="store_true", dest="as_json", help="JSON 格式输出")
    args = parser.parse_args()

    if not _SAFE_MASTER.match(args.master):
        print(f"无效的 master ID：{args.master!r}（仅允许字母、数字、'-'、'_'）", file=sys.stderr)
        sys.exit(2)

    master_dir = resolve_master_dir(args.master)
    if master_dir is None:
        print(f"找不到 master：{args.master!r}（试过 {args.master!r} 和 master-{args.master}）",
              file=sys.stderr)
        sys.exit(2)

    results = find_citations(master_dir, args.text)

    if not results:
        print(f"未找到包含「{args.text}」的段落。")
        return

    if args.as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"[{r['section']}] {r['citation']}")


if __name__ == "__main__":
    main()
