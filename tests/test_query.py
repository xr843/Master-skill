"""The offline helper should find a relevant excerpt from an ordinary Chinese question."""

from pathlib import Path

import query


def test_chinese_question_without_spaces_finds_a_traditional_excerpt(tmp_path: Path):
    master = tmp_path / "master-demo"
    sources = master / "sources"
    sources.mkdir(parents=True)
    (sources / "excerpt.md").write_text("## 觀心\n正念觀察心念的生滅。\n", encoding="utf-8")
    result = query.search(str(master), "正念怎么观察心念？")
    assert result and result[0]["section"] == "觀心"


def test_search_prefers_longer_relevant_phrase(tmp_path: Path):
    master = tmp_path / "master-demo"
    sources = master / "sources"
    sources.mkdir(parents=True)
    (sources / "a.md").write_text("## 无常\n一切现象无常。\n", encoding="utf-8")
    (sources / "b.md").write_text("## 正念\n正念观察心念。\n", encoding="utf-8")
    result = query.search(str(master), "如何正念观察心念？")
    assert result and result[0]["section"] == "正念"


def test_single_character_lookup_still_works(tmp_path: Path):
    master = tmp_path / "master-demo"
    sources = master / "sources"
    sources.mkdir(parents=True)
    (sources / "a.md").write_text("## 禪\n坐禪與觀照。\n", encoding="utf-8")
    assert query.search(str(master), "禅")[0]["section"] == "禪"


def test_a_pali_term_with_diacritics_is_one_keyword():
    # Found by review (2026-09-28): ānāpānasati was split at each ā into n, p,
    # nasati, and the lone `n` matched nearly every section.
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    master = str(root / "prebuilt" / "master-ajahn-chah")
    results = query.search(master, "ānāpānasati")
    assert results == query.search(master, "anapanasati")
    assert 0 < len(results) <= 10
    # A lone Latin letter is not a keyword: it used to match nearly everything.
    assert query.search(master, "n") == []


def test_variant_characters_match_across_scripts():
    assert query._fold("执着") == query._fold("執著")
    assert query._fold("里") == query._fold("裡") == query._fold("裏")
