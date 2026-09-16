"""Tests for the quote-attribution gate.

3h and 3i ask whether a quoted line *exists* — in CBETA, or in the compiled
teachings CBETA does not hold. Neither asks whether the doc tells the reader
which book it came from, and that is where a misattribution survives both:
master-nagarjuna's 「宁起我见积若须弥」 is real text, findable in CBETA, and not
his — it is in 《大宝积经》.

2026-09-16: measured across the repo, five of master-huineng's quotations named
no source anywhere — the 风幡 exchange, 何期自性, 迷时师度, the 神秀/慧能 verse
pair and 达摩's 付法偈. All five were genuine 《坛经》 lines, so every existing
check passed them; only the reader was left unable to look them up.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate-quote-attribution.py"


@pytest.fixture
def gate():
    scripts_dir = SCRIPT.parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location("validate_quote_attribution", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_source_named_on_the_line_counts(gate):
    lines = ['1. "菩提自性，本来清净，但用此心。"（《六祖大师法宝坛经·行由品》）']
    assert gate.attribution(lines, 1) == "on the line"


def test_a_source_line_below_counts(gate):
    """摘录文件把出处写在引文之后，不是之前。"""
    lines = ['> "菩提自性，本来清净。"', "", "> 出处：【《六祖大师法宝坛经·行由品》】"]
    assert gate.attribution(lines, 1) == "出处 line 2 below"


def test_a_source_line_below_without_a_work_does_not_count(gate):
    """「（开示要旨）」说明了体裁，没说是哪部书 —— 读者仍然查不了。"""
    lines = ['> "菩提自性，本来清净。"', "", "> 出处：（开示要旨）"]
    assert gate.attribution(lines, 1) is None


def test_a_sibling_numbered_item_carries_the_block(gate):
    """master-fazang 与 master-kumarajiva 的示例句：一条出处管整块。"""
    lines = ['1. "金与师子，同时成立，圆满具足。"', '2. "谓金无自性，随工巧匠缘。"（《金师子章》辨色空第二）']
    assert gate.attribution(lines, 1) == "sibling list item 2"


def test_a_heading_above_counts(gate):
    """master-ajahn-chah 的巴利摘录把经名写在 ### 标题里。"""
    lines = ["### 五蕴非我经（Anattalakkhaṇa Sutta）", "", '佛说："比丘们，色非我；受非我。"']
    assert gate.attribution(lines, 3) == "heading 2 above"


def test_a_quotation_named_nowhere_is_reported(gate):
    """门禁必须能红 —— 这正是 2026-09-16 慧能那五条的形状。"""
    lines = ['神秀偈："身是菩提树，心如明镜台，时时勤拂拭，勿使惹尘埃。"神秀从有入手。']
    assert gate.attribution(lines, 1) is None
    missing = gate.unattributed([("master-huineng/references/teaching.md:1", "master-huineng", "身是菩提树")], lambda rel: lines)
    assert [w for w, _ in missing] == ["master-huineng/references/teaching.md:1"]


def test_meta_json_locations_are_skipped(gate):
    """collect_persona_quotes 也收 meta.json 的 lore_triggers，那不是文档行。"""
    quotes = [("master-huineng/meta.json:lore_triggers[0]", "master-huineng", "不是风动")]
    assert gate.unattributed(quotes, lambda rel: []) == []


def test_an_empty_collector_fails_instead_of_passing(gate, monkeypatch, capsys):
    """检查了空集合的门禁不能报绿 —— 这个仓库栽过太多次。"""
    monkeypatch.setattr(gate, "collect_persona_quotes", lambda: [])
    assert gate.main() == 1
    assert "examined an empty set" in capsys.readouterr().out


def test_the_real_repo_passes(gate):
    """每条被 3h/3i 判定的引文，读者都能查到它出自哪部书。"""
    quotes = gate.collect_persona_quotes()
    # 62 → 58 on 2026-09-16 was deliberate: four sutta renderings in files that
    # declare themselves gist summaries stopped being dressed as the Buddha's direct
    # speech, so the collector rightly stopped treating them as quotations.
    assert len(quotes) >= 55, "采集器收的条数骤降，先查采集器"

    def read(rel):
        return Path(gate.PREBUILT_DIR, rel).read_text(encoding="utf-8").splitlines()

    missing = gate.unattributed(quotes, read)
    assert missing == [], f"这些引文没写出处：{[w for w, _ in missing]}"
