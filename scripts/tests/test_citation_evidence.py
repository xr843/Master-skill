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


# ---- 2026-10-19: claim detection and segment matching ---------------------
# Tuned on the archived claude-sonnet-4-6 sweep; the r2 re-grade went from
# 1838 unverified quotes to 491 without releasing any quotation the CBETA hand
# check (excerpt-pilot) judged near / other_work / spliced / not_found.

ZHONGLUN = {"T30n1564": ["众因缘生法我说即是无亦为是假名亦是中道义"]}
TWO_WORKS = {
    "B10n0048": ["如是若以因缘生因即谓诸法皆无自性说性空义即缘起义"],
    "B10n0067": ["诸具慧者应知性空之空义是缘起义非作用空无事之义"],
}
BOTH = {"B10n0048", "B10n0067"}


def test_inserted_gloss_does_not_hide_a_verbatim_quotation():
    for gloss in ("（空）", "(空)", "（梵文对应 śūnyatā，即空）"):
        text = f"偈云：「众因缘生法，我说即是无{gloss}，亦为是假名，亦是中道义。」【《中论》卷4，T30n1564】"
        assert unsupported_quotes(text, ZHONGLUN, {"T30n1564"}) == []


def test_link_and_source_label_inside_a_blockquote_are_not_quoted_words():
    text = ("龙树说：\n\n> 「众因缘生法，我说即是无，亦为是假名，亦是中道义。」\n"
            "> 出处：【《中论》卷4，T30n1564】→ https://fojin.app/texts/40\n")
    assert unsupported_quotes(text, ZHONGLUN, {"T30n1564"}) == []


def test_each_elided_segment_must_be_verbatim_in_the_same_work():
    cited = "【《辨了不了义善说藏论》卷三，B10n0048】"
    ok = f"论云：「如是若以因缘生因……说性空义即缘起义。」{cited}"
    assert unsupported_quotes(ok, TWO_WORKS, BOTH) == []
    assert unsupported_quotes(ok.replace("……", "（中略）"), TWO_WORKS, BOTH) == []


def test_splice_from_two_works_stays_unverified():
    # Both halves are genuine, from two different books (pilot: 宗喀巴, q-after #8).
    for joined in ("说性空义即缘起义，诸具慧者应知性空之空义，是缘起义",
                   "说性空义即缘起义……诸具慧者应知性空之空义，是缘起义"):
        for cited in ("【《辨了不了义善说藏论》卷三，B10n0048】",
                      "【《辨了不了义善说藏论》B10n0048；《菩提道次第广论》B10n0067】"):
            assert unsupported_quotes(f"论云：「{joined}。」{cited}", TWO_WORKS, BOTH)


def test_one_character_change_stays_unverified():
    # 「无」 written as 「空」: the change a reviewer has to rule on.
    text = "偈云：「众因缘生法，我说即是空，亦为是假名，亦是中道义。」【《中论》卷4，T30n1564】"
    assert unsupported_quotes(text, ZHONGLUN, {"T30n1564"})
    # A gloss cannot launder it either: what is left must still be verbatim.
    text = "偈云：「众因缘生法，我说即是空（无），亦为是假名，亦是中道义。」【《中论》卷4，T30n1564】"
    assert unsupported_quotes(text, ZHONGLUN, {"T30n1564"})


def test_sentence_found_nowhere_stays_unverified_in_every_presentation():
    fake = "菩萨以普贤行愿为本，示现神变，皆为令众生入华严法界"
    cited = "【《大方广佛华严经》，T10n0279】"
    for text in (
        f"经云：「{fake}。」{cited}",
        f"> 「{fake}。」\n\n此义见：{cited}",  # pilot: 法藏, not_found
        f"华严经中说，“{fake}”——{cited}",
        f"如帝释珠网——\n\n> {fake}。\n\n{cited}",
        f"\n\n“{fake}。”\n\n{cited}",
        f"法藏大师“{fake}”，{cited}",
        f"{cited}\n\n闻“{fake}”一句，当下明心。",
    ):
        assert unsupported_quotes(text, ZHONGLUN, {"T10n0279"}), text


def test_short_quotation_beside_a_citation_is_still_checked():
    assert unsupported_quotes("《坛经》明判：“量子即成佛”【《坛经》，T48n2008】", {}, {"T48n2008"})
    assert unsupported_quotes("> 诸法量子。【《坛经》，T48n2008】", {}, {"T48n2008"})


def test_terms_misconceptions_and_callouts_are_not_quotations():
    cited = "【《中论》卷4，T30n1564】"
    for text in (
        f"{cited}\n\n此处“无我”，并非否定一切。",
        f"{cited}\n\n若闻空而转起「证空得神通」之执，此执更难对治。",
        f"{cited}\n\n有人误以为“空就是什么都没有的意思”，这是断见。\n\n下一节再谈。",
        f"{cited}\n\n## 小结\n\n> 缘起即性空，性空即缘起，此二不相违。\n",
        f"{cited}\n\n> ⚠️ **重要提示**：本回答依据历史文献生成，仅供学习参考。\n",
        f"> 出处：{cited}→ https://fojin.app/texts/40\n",
        f"{cited}\n\n可以追问“中观与唯识的空有之争，历史上如何展开？”",
    ):
        assert unsupported_quotes(text, {}, {"T30n1564"}) == [], text


def test_blockquote_that_is_one_quotation_is_reported_once():
    text = "老和尚说：\n\n> “万缘放下，一念不生，这两句话如果不做到，入门都不可能。”\n> 【《坛经》，T48n2008】\n"
    assert len(unsupported_quotes(text, {}, {"T48n2008"})) == 1


def test_quotations_inside_a_quoted_blockquote_are_each_checked():
    text = ("《坛经》中大师明言：\n\n> 「菩提自性，本来清净。」\n> 「量子电脑可令人人即刻成佛。」\n"
            "> 【《坛经》，T48n2008】\n")
    unknown = unsupported_quotes(text, {"T48n2008": ["菩提自性本来清净"]}, {"T48n2008"})
    assert "量子电脑可令人人即刻成佛。" in [q["quote"] for q in unknown]


def test_a_compiled_teaching_cited_by_its_chinese_title_is_matched(tmp_path: Path):
    # 【《虚云和尚法汇》·开示·篇名】 carries no id; only the declared-title alias
    # resolves it. Without the aliases every xuyun quotation of the 《法汇》 was
    # unverified, verbatim or not (2026-10-19 sweep: 37 of 49).
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "fahui-excerpts.md").write_text(
        "## 话头\n\n原典（节选）：\n\n> 所谓话头。即是一念未生之际。一念才生。已成话尾。\n\n"
        "**引用格式：**【《虚云和尚法汇》·开示·禅堂开示】\n",
        encoding="utf-8",
    )
    declared = {"Xuyun:Fahui", "Xuyun:Nianpu"}
    aliases = {"虚云和尚法汇": "Xuyun:Fahui", "虚云老和尚年谱": "Xuyun:Nianpu"}
    evidence = load_quote_evidence(tmp_path, declared, aliases)
    assert set(evidence) == {"Xuyun:Fahui"}
    cited = "【《虚云和尚法汇》·开示·禅堂开示】"
    genuine = f"老和尚说：“所谓话头，即是一念未生之际。”{cited}"
    assert unsupported_quotes(genuine, evidence, declared, aliases) == []
    # Still exact: one changed character, or the right words under the other work, miss.
    assert unsupported_quotes(genuine.replace("未生", "不生"), evidence, declared, aliases)
    assert unsupported_quotes(genuine.replace(cited, "【《虚云老和尚年谱》】"), evidence, declared, aliases)
    # Without the aliases nothing resolves — the behaviour this guards against.
    assert load_quote_evidence(tmp_path, declared) == {}
