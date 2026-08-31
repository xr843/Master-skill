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
# 非 CBETA 契约家族。roadmap Phase 2 承诺把 CBETA / BDRC·Toh / PTS·SuttaCentral /
# 编集开示当作平等的 contract family,但审计器长期只实现了第一个 —— 于是全部藏传与
# 南传祖师的伪造引用一律漏检(见 eval/reports/BASELINE.md 的撤回段)。
#
# 关键在归一化,不在正则:meta.json 声明 `Toh:4465`,行文写 `Toh 4465`;声明
# `BDRC:W22272`,夹具 must_cite 写裸 `W22272`。只加正则不归一,会把**正确**引用
# 判成伪造 —— 那比漏检更糟。统一收敛到 `Family:Work` 再与声明集比对。
_FAMILY_ID = re.compile(
    r"(?<![0-9A-Za-z])(?:"
    r"(?P<toh>Toh)[:\s]\s*(?P<toh_n>\d+)"
    r"|(?P<bdrc>BDRC)[:\s]\s*(?P<bdrc_w>W[0-9A-Za-z-]+)"
    # 真 PTS id 的作品名首字母大写(`PTS:Vism` / `PTS:DN-Comm`)。要求大写,
    # 「（PTS edition）」这类散文说明才不会被读成 id。
    r"|(?P<pts>PTS)[:\s]\s*(?P<pts_w>[A-Z][0-9A-Za-z-]*)"
    # 裸 W 号:BDRC 的 work id 常单独出现(W22272 / W1KG14334)。要求 W 后紧跟数字,
    # 否则 "Wisdom Publications" 这类普通词会被误读成 id。
    r"|(?P<bare_w>W\d[0-9A-Z-]{3,})"
    r")(?![0-9A-Za-z])"
)


def _normalize_family_id(m: "re.Match[str]") -> str:
    """把一处家族引文归一成 meta.json 里声明的 `Family:Work` 形态。"""
    if m.group("toh"):
        return f"Toh:{m.group('toh_n')}"
    if m.group("bdrc"):
        return f"BDRC:{m.group('bdrc_w')}"
    if m.group("pts"):
        return f"PTS:{m.group('pts_w')}"
    return f"BDRC:{m.group('bare_w')}"


def extract_citation_ids(text: str) -> list[str]:
    """抽出一段文本里所有可核对的来源 id,四个家族一视同仁。

    CBETA 号按原样返回(声明形态与行文形态本来就一致);其余家族归一到
    `Family:Work`。SuttaCentral 是**语料库级** id(runtime contract §4 规则 3),
    `MN 118` 这类经号无法在没有经目索引的情况下判真伪,故不在此抽取 —— 那是
    已知边界,不是遗漏。
    """
    ids = list(_CBETA_ID.findall(text))
    ids.extend(_normalize_family_id(m) for m in _FAMILY_ID.finditer(text))
    return ids


# 短号 ↔ 完整号。CBETA 通行简写省掉册号(`T1911` = `T46n1911`),而 meta.json 存的
# 是完整形态。审计无条件运行之后,模型写简写就会被误判伪造 —— 大正藏/卍續藏的经号
# 在各自藏内唯一,按「藏别字母 + 经号数值」对齐即可,跨藏不对齐。
_SHORT_FORM = re.compile(r"^([TX])(\d+)$")
_FULL_FORM = re.compile(r"^([TX])\d+n(\d+)$")


def _resolve_short_form(cid: str, declared_ids: set[str]) -> str | None:
    """把短号对回声明里的完整号;对不上返回 None(仍按伪造处理)。"""
    m = _SHORT_FORM.match(cid)
    if not m:
        return None
    prefix, number = m.group(1), int(m.group(2))
    for declared in declared_ids:
        d = _FULL_FORM.match(declared)
        if d and d.group(1) == prefix and int(d.group(2)) == number:
            return declared
    return None


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
        # 归属区:本引文块结束 → 下一引文块开始(且不超过 _LINK_WINDOW)。这样一个 link
        # 只能洗白紧挨它之前的那一个引文块,不会连带洗白更前面的伪造引文(B1 的关键)。
        next_start = blocks[idx + 1].start() if idx + 1 < len(blocks) else len(answer)
        region_end = min(next_start, m.end() + _LINK_WINDOW)
        # 非 CBETA 祖师的主格式把家族标签放在块**后**的括号里
        # (`【《Visuddhimagga》§I】（PTS Vism）`),所以 id 与 link 共用这同一个归属区。
        ids = extract_citation_ids(m.group(1)) + extract_citation_ids(
            answer[m.end():region_end]
        )
        if not ids:
            continue
        link = _FOJIN_TEXT_LINK.search(answer, m.end(), region_end)
        for cid in ids:
            resolved = cid if cid in declared_ids else _resolve_short_form(
                cid, declared_ids
            )
            if resolved:
                offline.append(resolved)
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
