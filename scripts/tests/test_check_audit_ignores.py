"""`cargo audit` 的抑制清单必须和它抑制的东西一起消失。

security-scan.yml 那道门禁自己的注释写着「一条过期的 `--ignore` 和一条过期的
ADVISORY_GATES 条目是同一种缺陷」—— 在 2026-09-13 之前没有任何东西在检测它。
下面这些用例钉的就是检测本身：每一条都对着一种具体的失效方式。
"""

from __future__ import annotations

import datetime
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
_spec = importlib.util.spec_from_file_location(
    "check_audit_ignores", ROOT / "scripts" / "check-audit-ignores.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _report(vuln_ids=(), warn_ids=()):
    return {
        "vulnerabilities": {
            "count": len(vuln_ids),
            "list": [{"advisory": {"id": i}, "package": {"name": "x"}} for i in vuln_ids],
        },
        "warnings": {
            "unmaintained": [{"advisory": {"id": i}, "package": {"name": "y"}} for i in warn_ids]
        },
    }


def _entry(aid, **over):
    base = {
        "id": aid,
        "crate": "quick-xml",
        "why_not_applicable": "漏洞代码进不了发布二进制",
        "evidence": ["nm 在二进制里找不到该 crate 的任何符号"],
        "reviewed_on": "2026-09-13",
    }
    base.update(over)
    return base


def test_a_live_advisory_keeps_its_suppression():
    assert mod.check(_report(vuln_ids=["RUSTSEC-1"]), [_entry("RUSTSEC-1")]) == []


def test_a_suppression_whose_advisory_is_gone_is_reported():
    """上游升级后 advisory 消失，`--ignore` 还留着 —— 将来它被重新引入时会被静静吞掉。"""
    problems = mod.check(_report(vuln_ids=[]), [_entry("RUSTSEC-1")])
    assert len(problems) == 1
    assert "已不在扫描结果里" in problems[0]


def test_an_advisory_demoted_to_a_warning_is_not_treated_as_gone():
    """cargo-audit 会把同一条 advisory 按类型分桶；降级不等于消失。

    只看 vulnerabilities 的话，一条降级成 warning 的 advisory 会被误判成
    「已修复，删掉抑制」，下一次它再升回 vulnerability 就直接把 CI 打红，
    理由还是错的。
    """
    assert mod.check(_report(warn_ids=["RUSTSEC-1"]), [_entry("RUSTSEC-1")]) == []


def test_a_suppression_without_a_reason_is_rejected():
    entry = _entry("RUSTSEC-1")
    del entry["why_not_applicable"]
    problems = mod.check(_report(vuln_ids=["RUSTSEC-1"]), [entry])
    assert any("why_not_applicable" in p for p in problems)


def test_a_suppression_without_evidence_is_rejected():
    """「为什么不适用」可以随口写，「怎么确认的」不行。"""
    problems = mod.check(
        _report(vuln_ids=["RUSTSEC-1"]), [_entry("RUSTSEC-1", evidence=[])]
    )
    assert any("evidence" in p for p in problems)


@pytest.mark.parametrize("bad", ["待定", "TODO", "2026-13-45", ""])
def test_an_unparseable_review_date_is_rejected(bad):
    problems = mod.check(
        _report(vuln_ids=["RUSTSEC-1"]), [_entry("RUSTSEC-1", reviewed_on=bad)]
    )
    assert problems


def test_the_registry_on_disk_is_complete():
    """仓库里那份清单每条都要过同一套要求。"""
    registry = mod.load_registry()
    assert registry, "清单为空时这道检查什么也没核对"
    for entry in registry:
        assert entry["id"].startswith("RUSTSEC-"), entry["id"]
        assert len(entry["why_not_applicable"]) >= 10, entry["id"]
        assert entry["evidence"], entry["id"]
        datetime.date.fromisoformat(entry["reviewed_on"])
        assert entry.get("cannot_upgrade_because"), entry["id"]


def test_the_workflow_takes_its_ignore_ids_from_the_registry():
    """两处各写一份清单，迟早会对不上 —— 而对不上的那一天没人会发现。"""
    workflow = (ROOT / ".github/workflows/security-scan.yml").read_text(encoding="utf-8")
    assert "desktop/audit-ignore.json" in workflow
    for entry in mod.load_registry():
        assert f"--ignore {entry['id']}" not in workflow, (
            f"{entry['id']} 被硬写进了 workflow；ignore 参数必须由清单生成"
        )
