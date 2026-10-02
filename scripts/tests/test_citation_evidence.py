from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _citation_evidence import load_quote_evidence, unsupported_quotes


def test_only_original_blocks_support_quotes_in_the_cited_work(tmp_path: Path):
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "sutra.md").write_text(
        '## 原文\n原典（节选）：\n\n> 菩提自性，本來清淨，但用此心，直了成佛。\n'
        '\n【《坛经》，T48n2008】\n\n教义要点：量子电脑可令人人即刻成佛。\n',
        encoding="utf-8",
    )
    evidence = load_quote_evidence(tmp_path, {"T48n2008", "T08n0235"})
    assert unsupported_quotes('经云：“菩提自性，本来清净。”【《坛经》，T48n2008】', evidence) == []
    assert unsupported_quotes('> 菩提自性，本来清净。\n> 【《坛经》，T48n2008】', evidence) == []
    assert unsupported_quotes('经云：“菩提自性，本来清净。”【《金刚经》，T08n0235】', evidence)
    assert unsupported_quotes('经云：“量子电脑可令人人即刻成佛。”【《坛经》，T48n2008】', evidence)


def test_paraphrases_and_unreferenced_quotes_are_not_original_evidence(tmp_path: Path):
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "paraphrase.md").write_text(
        '## 教义要旨\n> 菩提自性，本來清淨，但用此心，直了成佛。\n【《坛经》，T48n2008】',
        encoding="utf-8",
    )
    assert load_quote_evidence(tmp_path, {"T48n2008"}) == {}
    assert unsupported_quotes('你说“我不知道怎么开始学习”。', {}) == []


def test_each_quote_sharing_one_citation_is_checked():
    text = '经云：“量子电脑可令人人即刻成佛。”又云：“菩提自性，本来清净。”【《坛经》，T48n2008】'
    unknown = unsupported_quotes(text, {"T48n2008": ["菩提自性本来清净"]})
    assert [q["quote"] for q in unknown] == ["量子电脑可令人人即刻成佛。"]


def test_other_direct_quote_formats_cannot_bypass_review():
    for text in (
        '经云：【《坛经》，T48n2008】“量子电脑可令人人即刻成佛。”',
        '经云：\n> 量子电脑可令人人即刻成佛。\n【《坛经》，T48n2008】',
        '经云：“量子电脑\n可令人人即刻成佛。”【《坛经》，T48n2008】',
        '经云：“量子成佛。”【《坛经》，T48n2008】',
        '> 量子电脑可令人人即刻成佛。\n> 【《坛经》，T48n2008】',
        '> 量子电脑可令人人即刻成佛。【《坛经》，T48n2008】',
    ):
        assert unsupported_quotes(text, {}, {"T48n2008"})


def test_explicit_prior_attribution_wins_over_unrelated_following_source():
    text = '【《坛经》，T48n2008】云：“应无所住而生其心。”\n另据【《金刚经》，T08n0235】讨论般若。'
    unknown = unsupported_quotes(text, {"T08n0235": ["应无所住而生其心"]}, {"T48n2008", "T08n0235"})
    assert unknown and unknown[0]["citation"] == '【《坛经》，T48n2008】'
