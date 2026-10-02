#!/usr/bin/env python3
"""离线检索指定 master 的 sources/ 和 references/。"""

import argparse
import json
import os
import re
import sys
import unicodedata

from opencc import OpenCC

from _masterpaths import resolve_master_dir

# master feeds into os.path.join(...); restrict to a slug charset so a value
# like "../../etc" can never read files outside prebuilt/. Mirrors the
# isSafeName guard in bin/cli.mjs.
_SAFE_MASTER = re.compile(r"^[A-Za-z0-9_-]+$")
# Both sides are folded the same way before matching. To simplified, not to
# traditional: s2t turns 执着 into 執着 while the sources write 執著, and 里
# into 裏 against 裡. 著/着 are then treated as one character, which is how
# the canon's own editions disagree. Latin text loses its diacritics — a
# query for ānāpānasati was split at every ā into n, p, nasati, and the lone
# `n` matched nearly every section.
_TO_SIMPLIFIED = OpenCC("t2s")
MAX_RESULTS = 20


def _fold(text: str) -> str:
    text = _TO_SIMPLIFIED.convert(text).replace("著", "着").lower()
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


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


def search(master_dir, query, brief=False):
    normalized_query = _fold(query)
    keywords = set()
    for token in re.findall(r"[\u3400-\u9fff]+|[a-z0-9]+", normalized_query):
        if re.fullmatch(r"[\u3400-\u9fff]+", token):
            if len(token) == 1:
                keywords.add(token)
            for length in range(2, min(4, len(token)) + 1):
                keywords.update(token[i:i + length] for i in range(len(token) - length + 1))
        elif len(token) > 1:
            keywords.add(token)
    if not keywords:
        return []
    results = []

    for subdir in ("sources", "references"):
        dirpath = os.path.join(master_dir, subdir)
        if not os.path.isdir(dirpath):
            continue
        for fname in sorted(os.listdir(dirpath)):
            if fname == "INDEX.md" or not fname.endswith(".md"):
                continue
            fpath = os.path.join(dirpath, fname)
            content = open(fpath, encoding="utf-8").read()
            for title, body in parse_sections(content):
                full = title + "\n" + body
                normalized_full = _fold(full)
                matched = [kw for kw in keywords if kw in normalized_full]
                if not matched:
                    continue
                # 清理 body 前 200 字
                clean = re.sub(r'\n{2,}', '\n', body).strip()
                preview = clean[:200]
                results.append({
                    "section": title,
                    "preview": preview,
                    "file": os.path.join(subdir, fname),
                    "_score": (max(map(len, matched)), len(matched)),
                })
    results.sort(key=lambda row: row["_score"], reverse=True)
    for row in results:
        del row["_score"]
    return results


def main():
    parser = argparse.ArgumentParser(description="离线检索 master 的 sources 和 references")
    parser.add_argument("--master", required=True, help="大师 ID，如 master-zhiyi")
    parser.add_argument("--q", required=True, help="搜索关键词（空格分隔，OR 匹配）")
    parser.add_argument("--json", action="store_true", dest="as_json", help="JSON 格式输出")
    parser.add_argument("--brief", action="store_true", help="仅输出段标题和文件路径")
    args = parser.parse_args()

    if not _SAFE_MASTER.match(args.master):
        print(f"无效的 master ID：{args.master!r}（仅允许字母、数字、'-'、'_'）", file=sys.stderr)
        sys.exit(2)

    master_dir = resolve_master_dir(args.master)
    if master_dir is None:
        print(f"找不到 master：{args.master!r}（试过 {args.master!r} 和 master-{args.master}）",
              file=sys.stderr)
        sys.exit(2)

    results = search(master_dir, args.q, args.brief)
    total = len(results)
    results = results[:MAX_RESULTS]
    if total > MAX_RESULTS:
        # Said on stderr so --json stays a clean array.
        print(f"共 {total} 段命中，按相关度显示前 {MAX_RESULTS} 段。", file=sys.stderr)

    if not results and not args.as_json:
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
