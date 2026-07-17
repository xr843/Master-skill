#!/usr/bin/env python3
"""B1 引证核验器 — 抓出 master 回答里的幻觉引文(dev/CI 镜像)。

这是每个 master SKILL.md 里「出答前引证自审」那条运行时规则的**确定性镜像**。
运行时命门在 SKILL.md(指令驱动,随技能装机);本脚本只在 repo 内(有 Python)做 CI lint。

规则:抽取答案中每个 `【…，<cbeta_id>】` 引文,判定——
  - `cbeta_id` ∈ 本 master 声明的离线源(meta.json sources[].id) → offline,放行;
  - 否则其后近邻出现 `fojin.app/texts/{N}` 数字链接 → live,放行(`--online` 再验 N 可解析);
  - 两者都不满足 → fabricated(幻觉引文),exit 1。

离线判定纯确定性、零网络、零 LLM,可作 CI 硬门。`--online` 为可选增强,网络不可达时仅告警。

用法:
    python scripts/verify_citations.py --master huineng --answer-file ans.md
    echo "…答案…" | python scripts/verify_citations.py --master huineng
    python scripts/verify_citations.py --master huineng --answer-file ans.md --online
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

from _masterpaths import resolve_master_dir

# master feeds into path resolution; restrict to a slug charset so a value like
# "../../etc" can never read files outside prebuilt/. Mirrors the isSafeName
# guard in bin/cli.mjs and scripts/query.py.
_SAFE_MASTER = re.compile(r"^[A-Za-z0-9_-]+$")

# CBETA id 形态:T48n2008 / T08n0235(藏经卷+n+编号),及 API 返回的 X1218 / X0303
# (无卷号)。无 `n` 的形态只认 T/X 两个集合,避免误吞 Wikidata 的 Q1234 / P5008。
#
# 边界不能用 \b:Python 的 \w 覆盖 CJK,故「卷一T99n9999」的「一」与「T」之间
# 没有 \b,整块引文会被 audit_answer 当作无 id 跳过 —— 而格式跑偏正是模型最可能
# 编造经号的时候。改判「前后不是拉丁字母或数字」:汉字紧邻属真实引文形态,须命中;
# 拉丁字母紧邻(FakeSutraT99n9999)通常意味着它只是更长 token 的一部分,不算引文。
_CBETA_ID = re.compile(
    r"(?<![0-9A-Za-z])(?:[A-Z]{1,2}\d+n\d+|[TX]\d{3,})(?![0-9A-Za-z])"
)
# 引文块 【…】
_CITATION_BLOCK = re.compile(r"【([^】]*)】")
# live 链接 fojin.app/texts/<数字>
_FOJIN_TEXT_LINK = re.compile(r"fojin\.app/texts/(\d+)")
# 引文块「之后」多远内出现 live 链接仍算本块携带(且不跨过下一引文块)。link 须在引文之后。
_LINK_WINDOW = 120


def load_declared_ids(master: str) -> set[str]:
    """读 prebuilt/<master>/meta.json,返回声明的离线 cbeta_id 集合。"""
    if not _SAFE_MASTER.match(master):
        raise ValueError(f"无效的 master ID：{master!r}（仅允许字母、数字、'-'、'_'）")
    master_dir = resolve_master_dir(master)  # 兼容 "huineng" / "master-huineng"
    if master_dir is None:
        raise FileNotFoundError(f"找不到 master：{master!r}（试过 {master!r} 和 master-{master}）")
    with open(os.path.join(master_dir, "meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    ids: set[str] = set()
    for src in meta.get("sources", []):
        sid = src.get("id")
        if sid:
            ids.add(sid)
    ids.update(meta.get("search_scope", {}).get("primary_cbeta_ids", []))
    return ids


def audit_answer(declared_ids: set[str], answer: str) -> dict:
    """把答案里每条引文分类为 offline / live / fabricated。

    返回 {'offline': [...], 'live': [(cbeta_id, text_id), ...], 'fabricated': [...]}。
    """
    offline: list[str] = []
    live: list[tuple[str, str]] = []
    fabricated: list[str] = []

    blocks = list(_CITATION_BLOCK.finditer(answer))
    for idx, m in enumerate(blocks):
        ids = _CBETA_ID.findall(m.group(1))
        if not ids:
            continue
        # 链接归属:本引文块结束 → 下一引文块开始(且不超过 _LINK_WINDOW)。这样一个 link
        # 只能洗白紧挨它之前的那一个引文块,不会连带洗白更前面的伪造引文(B1 的关键)。
        next_start = blocks[idx + 1].start() if idx + 1 < len(blocks) else len(answer)
        region_end = min(next_start, m.end() + _LINK_WINDOW)
        link = _FOJIN_TEXT_LINK.search(answer, m.end(), region_end)
        for cid in ids:
            if cid in declared_ids:
                offline.append(cid)
            elif link:
                live.append((cid, link.group(1)))
            else:
                fabricated.append(cid)
    return {"offline": offline, "live": live, "fabricated": fabricated}


def verify_online(text_ids: list[str], base_url: str = "https://fojin.app", timeout: int = 15) -> dict:
    """best-effort:GET /api/texts/{id} 看 live 引文的 text_id 是否真解析。

    网络不可达时返回 {'_unreachable': True},调用方按告警处理(不硬失败)。
    """
    try:
        import requests
    except ImportError:
        return {"_unreachable": True, "_reason": "requests 未安装"}
    out: dict = {}
    sess = requests.Session()
    for tid in text_ids:
        try:
            r = sess.get(f"{base_url}/api/texts/{tid}", timeout=timeout)
            out[tid] = r.status_code == 200 and bool(r.json())
        except Exception as e:  # noqa: BLE001 — 网络层一律降级为不可达
            return {"_unreachable": True, "_reason": str(e)}
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="B1 引证核验器")
    p.add_argument("--master", required=True, help="master slug,如 huineng")
    p.add_argument("--answer-file", help="答案文件;省略则从 stdin 读")
    p.add_argument("--online", action="store_true", help="额外验证 live 引文 text_id 可解析")
    args = p.parse_args()

    try:
        declared = load_declared_ids(args.master)
    except (ValueError, FileNotFoundError) as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2

    answer = open(args.answer_file, encoding="utf-8").read() if args.answer_file else sys.stdin.read()
    report = audit_answer(declared, answer)

    print(f"offline 引文: {len(report['offline'])}  live 引文: {len(report['live'])}  "
          f"fabricated: {len(report['fabricated'])}")

    exit_code = 0
    if report["fabricated"]:
        print(f"✗ 幻觉引文(既非声明源,又无 live 链接): {sorted(set(report['fabricated']))}", file=sys.stderr)
        exit_code = 1

    if args.online and report["live"]:
        res = verify_online([tid for _, tid in report["live"]])
        if res.get("_unreachable"):
            print(f"⚠ --online 跳过:FoJin 不可达({res.get('_reason')})", file=sys.stderr)
        else:
            bad = [tid for tid, ok in res.items() if not ok]
            if bad:
                print(f"✗ live 引文 text_id 无法解析: {bad}", file=sys.stderr)
                exit_code = 1

    if exit_code == 0:
        print("✓ 全部引文可核验")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
