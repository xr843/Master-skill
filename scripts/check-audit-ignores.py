#!/usr/bin/env python3
"""门禁：cargo audit 的每一条 `--ignore` 都必须仍然对应一条真实存在的 advisory。

`security-scan.yml` 里那步「Fail on any actionable advisory」带两个
`--ignore`，它自己的注释写着「一条过期的 `--ignore` 和一条过期的
ADVISORY_GATES 条目是同一种缺陷」—— 而在此之前没有任何东西在检测它过期。
后果不是理论上的：quick-xml 哪天被上游升到 0.41 以上，这两个 `--ignore`
会留在命令行里；若将来某条依赖又把 0.30 拖回来，那条 7.5 高危会被静静吞掉，
而 CI 照常显示绿。抑制清单和它抑制的东西一起消失，是它唯一安全的结局。

本脚本只管这一半。「这次扫描算不算通过」仍由 cargo audit 自己判——
不在这里重写一遍它的退出逻辑（那会漂移），只核对清单本身。

用法：
    cargo audit --file desktop/Cargo.lock --json > audit.json || true
    python3 scripts/check-audit-ignores.py audit.json
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "desktop" / "audit-ignore.json"

# 一条抑制记录至少要说明白这三件事，否则它只是一行静音。
REQUIRED = ("why_not_applicable", "evidence", "reviewed_on")


def load_registry(path: Path = REGISTRY) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["ignore"]


def advisory_ids(report: dict) -> set[str]:
    """扫描结果里出现过的全部 advisory id（漏洞 + 各类警告）。

    warnings 也算：cargo-audit 会把同一条 advisory 按类型分桶，一条今天是
    vulnerability 的记录明天可能降级成 warning，那不等于它消失了。
    """
    ids = {
        v["advisory"]["id"]
        for v in (report.get("vulnerabilities") or {}).get("list", [])
        if v.get("advisory")
    }
    for bucket in (report.get("warnings") or {}).values():
        for item in bucket:
            advisory = item.get("advisory") or {}
            if advisory.get("id"):
                ids.add(advisory["id"])
    return ids


def check(report: dict, registry: list[dict]) -> list[str]:
    problems: list[str] = []
    if not registry:
        # 空清单不是「干净」：它意味着这道检查什么也没核对。
        print("  抑制清单为空 —— 本检查没有核对任何条目")
        return problems

    present = advisory_ids(report)
    for entry in registry:
        aid = entry.get("id", "?")
        for field in REQUIRED:
            value = entry.get(field)
            if not value:
                problems.append(f"{aid}: 缺 `{field}` —— 没有理由的抑制就是静音")
        reviewed = entry.get("reviewed_on")
        if reviewed:
            try:
                datetime.date.fromisoformat(reviewed)
            except ValueError:
                problems.append(f"{aid}: `reviewed_on` 不是可解析的日期：{reviewed!r}")
        if aid not in present:
            problems.append(
                f"{aid}: 已不在扫描结果里 —— 从 desktop/audit-ignore.json 删掉它。"
                " 留着的抑制会在这条 advisory 将来被重新引入时静静吞掉它。"
            )
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {Path(argv[0]).name} <cargo-audit --json 的输出文件>")
        return 2
    report = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    registry = load_registry()
    problems = check(report, registry)

    if problems:
        print(f"✗ 抑制清单有 {len(problems)} 处问题：\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(f"✓ 抑制清单 {len(registry)} 条，逐条仍对应扫描结果里真实存在的 advisory：")
    for entry in registry:
        print(f"    {entry['id']}  {entry.get('crate','?')}  复核于 {entry['reviewed_on']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
