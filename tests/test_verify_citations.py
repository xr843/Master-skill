"""Tests for scripts/verify_citations.py — B1 引证核验,纯逻辑无网络。"""

import importlib
from pathlib import Path

verify_citations = importlib.import_module("verify_citations")
audit_answer = verify_citations.audit_answer
load_declared_ids = verify_citations.load_declared_ids
extract_member_aliases = verify_citations.extract_member_aliases
load_member_aliases = verify_citations.load_member_aliases

# 慧能声明的离线源(与 prebuilt/master-huineng/meta.json 一致)
HUINENG = {"T48n2008", "T08n0235", "T14n0475"}
OUYI_JIAXING = {"J36nB348"}


def test_offline_citation_passes():
    """引用声明源 → offline,无幻觉。"""
    ans = "见性成佛者，自性本自清净。【《六祖坛经·般若品》，T48n2008】→ https://fojin.app/texts/58"
    r = audit_answer(HUINENG, ans)
    assert r["fabricated"] == []
    assert "T48n2008" in r["offline"]


def test_fabricated_citation_flagged():
    """引用非声明源且无 live 链接 → fabricated。"""
    ans = "慧能在此经说见性。【《楞严经》，T19n0945】"
    r = audit_answer(HUINENG, ans)
    assert "T19n0945" in r["fabricated"]


def test_live_citation_with_link_passes():
    """非声明源但携带真实 fojin.app/texts 链接 → live,放行。"""
    ans = ("达磨亦云见性即是佛。【《達磨大師血脉論》，X1218】"
           "→ https://fojin.app/texts/13013/read?juan=1")
    r = audit_answer(HUINENG, ans)
    assert r["fabricated"] == []
    assert ("X1218", "13013") in r["live"]


def test_live_link_outside_window_does_not_whitelist():
    """link 离引文太远(超窗口)不算携带 → 仍 fabricated。"""
    ans = "【《達磨大師血脉論》，X1218】" + ("。" * 200) + "https://fojin.app/texts/13013"
    r = audit_answer(HUINENG, ans)
    assert "X1218" in r["fabricated"]


def test_one_link_does_not_whitelist_earlier_blocks():
    """两相邻引文块共用尾部一个 link,只洗白紧挨它的那一个(B1 关键)。"""
    ans = ("【《甲》，X1218】【《乙》，X9999】"
           "→ https://fojin.app/texts/13013/read?juan=1")
    r = audit_answer(HUINENG, ans)
    # 链接紧挨「乙」→ X9999 算 live;「甲」之后到「乙」之间无链接 → X1218 仍 fabricated
    assert ("X9999", "13013") in r["live"]
    assert "X1218" in r["fabricated"]


def test_wikidata_ids_not_parsed_as_cbeta():
    """Q1234 / P5008 是 Wikidata id,不该被当成 CBETA 引文(否则被误判幻觉)。"""
    ans = "某实体见【某条目 Q1234 / P5008】。"
    r = audit_answer(HUINENG, ans)
    assert r["fabricated"] == [] and r["live"] == [] and r["offline"] == []


def test_no_citation_no_false_positive():
    """无引文(如坦诚拒答)→ 不误杀。"""
    ans = "此话题超出本角色离线资料范围，建议在 fojin.app 查阅原典。"
    r = audit_answer(HUINENG, ans)
    assert r["fabricated"] == []
    assert r["offline"] == [] and r["live"] == []


def test_multiple_ids_in_one_block():
    """一个引文块含多个 id,逐个判定。"""
    ans = "【《坛经》T48n2008；《金刚经》T08n0235】"
    r = audit_answer(HUINENG, ans)
    assert set(r["offline"]) == {"T48n2008", "T08n0235"}
    assert r["fabricated"] == []


def test_fabricated_id_touching_cjk_is_flagged():
    """伪造经号紧贴汉字 → 仍须判 fabricated。

    Python 的 \\w 覆盖 CJK,故「一」与「T」之间不存在 \\b 边界。用 \\b 划界时
    整块引文被 `if not ids: continue` 跳过,而格式跑偏正是模型最可能编造经号
    的时候 —— 反幻觉门恰好在最需要它的场景失效。
    """
    ans = "此义见于彼经。【《伪造经》卷一T99n9999】"
    r = audit_answer(HUINENG, ans)
    assert "T99n9999" in r["fabricated"]


def test_fabricated_id_followed_by_cjk_is_flagged():
    """经号后紧跟汉字(尾侧无 \\b)→ 仍须判 fabricated。"""
    ans = "此义见于彼经。【《伪造经》X9999卷一】"
    r = audit_answer(HUINENG, ans)
    assert "X9999" in r["fabricated"]


def test_declared_id_touching_cjk_is_recognized():
    """真实经号紧贴汉字 → 须认作 offline,而非视若无睹。"""
    ans = "见性成佛。【《坛经》卷一T48n2008】"
    r = audit_answer(HUINENG, ans)
    assert "T48n2008" in r["offline"]
    assert r["fabricated"] == []


def test_id_inside_latin_token_not_parsed_as_cbeta():
    """经号嵌在拉丁词内(如标识符/文件名)不算引文,避免误杀。

    与 CJK 相邻不同:汉字紧邻是真实引文格式,拉丁字母紧邻通常意味着它是更长
    token 的一部分。
    """
    ans = "构建产物见【FakeSutraT99n9999】。"
    r = audit_answer(HUINENG, ans)
    assert r["fabricated"] == [] and r["offline"] == [] and r["live"] == []


def test_canonical_jiaxing_full_id_is_offline():
    result = audit_answer(OUYI_JIAXING, "【《靈峰蕅益大師宗論》，J36nB348】")
    assert result["offline"] == ["J36nB348"]
    assert result["fabricated"] == []


def test_canonical_jiaxing_short_id_resolves_to_declared_full_id():
    result = audit_answer(OUYI_JIAXING, "【《靈峰蕅益大師宗論》，JB348】")
    assert result["offline"] == ["J36nB348"]
    assert result["fabricated"] == []


def test_numeric_jiaxing_typo_does_not_resolve_to_canonical_id():
    result = audit_answer(OUYI_JIAXING, "【《靈峰蕅益大師宗論》，J36n0348】")
    assert result["offline"] == []
    assert result["fabricated"] == ["J36n0348"]


def test_load_declared_ids_real_master():
    """从真实 meta.json 读出慧能声明源。"""
    ids = load_declared_ids("huineng")
    assert {"T48n2008", "T08n0235", "T14n0475"} <= ids


def test_load_declared_ids_rejects_traversal():
    """path-traversal 的 master 名被拒。"""
    import pytest
    with pytest.raises(ValueError):
        load_declared_ids("../../etc")


# ---------------------------------------------------------------------------
# 非 CBETA 契约家族(Toh / BDRC / PTS)
#
# 2026-08-31 之前 _CBETA_ID 只认 CBETA 经号,抽不出 id 的引文块整块 skip ——
# 全部藏传与南传祖师的伪造引用一律漏检(见 eval/reports/BASELINE.md 的撤回段)。
#
# 关键陷阱:meta.json 声明的 id 与回答里实际写法**不是同一个字符串**。
# meta 写 `Toh:4465`,行文写 `Toh 4465`;meta 写 `BDRC:W22272`,夹具 must_cite
# 写裸 `W22272`。只加正则不做归一化,会把**正确**引用判成伪造 —— 比漏检更糟。
# ---------------------------------------------------------------------------

ATISHA = {"Toh:4465", "Toh:3948", "BDRC:Pha-chos-Bu-chos"}
MILAREPA = {"BDRC:W1KG14334", "BDRC:W22272"}
BUDDHAGHOSA = {"PTS:Vism", "PTS:DN-Comm", "SuttaCentral"}


def test_fabricated_toh_id_flagged():
    """编造的德格版编号必须被抓住。"""
    r = audit_answer(ATISHA, "此义见【《菩提道灯论》，Toh 9999】")
    assert "Toh:9999" in r["fabricated"]


def test_declared_toh_id_written_with_a_space_is_offline():
    """meta 写 `Toh:4465`、行文写 `Toh 4465` —— 同一个 id,不得判伪造。"""
    r = audit_answer(ATISHA, "此义见【《菩提道灯论》，Toh 4465】")
    assert r["fabricated"] == []
    assert "Toh:4465" in r["offline"]


def test_fabricated_bdrc_work_id_flagged():
    r = audit_answer(MILAREPA, "见【《道歌集》，BDRC: W99999】")
    assert "BDRC:W99999" in r["fabricated"]


def test_bare_bdrc_work_id_matches_declared_prefixed_form():
    """夹具 must_cite 写裸 `W22272`,meta 写 `BDRC:W22272`。"""
    r = audit_answer(MILAREPA, "见【《密勒日巴尊者传》，W22272】")
    assert r["fabricated"] == []
    assert "BDRC:W22272" in r["offline"]


def test_fabricated_pts_work_flagged():
    r = audit_answer(BUDDHAGHOSA, "见【《伪注释》，PTS:FakeComm】")
    assert "PTS:FakeComm" in r["fabricated"]


def test_declared_pts_work_written_with_a_space_is_offline():
    r = audit_answer(BUDDHAGHOSA, "见【《Visuddhimagga》§I 戒品，PTS Vism】")
    assert r["fabricated"] == []
    assert "PTS:Vism" in r["offline"]


def test_prose_w_word_is_not_read_as_a_bdrc_id():
    """裸 W 形态只在 W 后紧跟数字时成立,普通英文词不得误判。"""
    r = audit_answer(MILAREPA, "见【Wisdom Publications 英译本导论】")
    assert r["fabricated"] == [] and r["offline"] == [] and r["live"] == []


# ---------------------------------------------------------------------------
# 家族标签在引文块**之后**的括号里 —— 这才是非 CBETA 祖师的主格式。
#
#   buddhaghosa  【《{title}》§{section}】（PTS / SuttaCentral）
#   atisha       【《{title}》§{section}】（Toh {toh_id} / 见 BDRC.io 'a ti sha'）
#   milarepa     【《{title}》{section}】（BDRC: {bdrc_id}）
#
# 块内只有书名,可核对的 id 在尾巴上。沿用 _LINK_WINDOW 既有的「块后有界、不跨下一
# 块」区域,与 fojin 链接归属规则同一套。
# ---------------------------------------------------------------------------


def test_trailing_parenthetical_pts_tag_is_audited():
    """觉音的主格式:块内是书名,PTS 标签在尾括号。"""
    r = audit_answer(BUDDHAGHOSA, "见【《Visuddhimagga》§I 戒品】（PTS Vism）")
    assert r["fabricated"] == []
    assert "PTS:Vism" in r["offline"]


def test_fabricated_id_in_trailing_parenthetical_flagged():
    r = audit_answer(BUDDHAGHOSA, "见【《破除戏论》§III】（PTS:FakeComm）")
    assert "PTS:FakeComm" in r["fabricated"]


def test_trailing_id_does_not_attach_to_an_earlier_block():
    """尾部一个 id 只归属紧挨它的那一块 —— 与 fojin 链接同一条不变式。"""
    r = audit_answer(ATISHA, "【《甲》】【《乙》】（Toh 9999）")
    assert r["fabricated"].count("Toh:9999") == 1


def test_bdrc_io_hostname_is_not_read_as_an_id():
    """atisha 出厂格式里就带 `见 BDRC.io 'a ti sha'`,不得被读成 BDRC id。"""
    r = audit_answer(ATISHA, "见【《菩提道灯论》§菩提心章】（Toh 4465 / 见 BDRC.io 'a ti sha'）")
    assert r["fabricated"] == []
    assert "Toh:4465" in r["offline"]


def test_pts_followed_by_a_lowercase_word_is_not_an_id():
    """觉音的行文里有「（PTS edition）」这类说明,不是 id。真 PTS id 首字母大写
    (`PTS:Vism` / `PTS:DN-Comm`),据此把散文排除掉。"""
    r = audit_answer(BUDDHAGHOSA, "依巴利圣典协会刊本【《清净道论》】（PTS edition）")
    assert r["fabricated"] == []


def test_pts_id_with_an_uppercase_work_still_matches():
    r = audit_answer(BUDDHAGHOSA, "见【《长部注释》，PTS:DN-Comm】")
    assert r["fabricated"] == []
    assert "PTS:DN-Comm" in r["offline"]


# 短号形态:CBETA 的通行简写省掉册号(`T1911` = `T46n1911`)。声明集里存的是完整
# 形态,审计一旦无条件运行,模型写简写就会被误判伪造 —— 大正藏经号全藏唯一,
# 按经号对齐即可。
ZHIYI = {"T46n1911", "T33n1718", "T09n0262"}


def test_bare_taisho_number_resolves_to_the_declared_volume_qualified_id():
    r = audit_answer(ZHIYI, "见【《摩訶止觀》，T1911】")
    assert r["fabricated"] == []
    assert "T46n1911" in r["offline"]


def test_zero_padded_declared_number_matches_its_short_form():
    r = audit_answer(ZHIYI, "见【《妙法蓮華經》，T262】")
    assert r["fabricated"] == []
    assert "T09n0262" in r["offline"]


def test_bare_taisho_number_that_is_not_declared_is_still_flagged():
    """1716 不是 1718 —— 对齐不能变成放行。"""
    r = audit_answer(ZHIYI, "见【《法華玄義》，T1716】")
    assert "T1716" in r["fabricated"]


def test_short_form_does_not_cross_canon_prefixes():
    """X(卍續藏)的短号不得对上 T(大正藏)的声明。"""
    r = audit_answer(ZHIYI, "见【《某續藏本》，X1911】")
    assert "X1911" in r["fabricated"]


# 「审计了但一条都没看懂」必须与「已审计、干净」分得开。抽不出 id 的引文块以前被
# 整块 silently skip,于是宗喀巴(声明的多是裸 Wylie 标题)每条回答都报
# `fabricated: []` —— 读起来是干净,实际是没看懂。同一个假绿,更细的粒度。
TSONGKHAPA = {"Lam-gtso-rnam-gsum", "Lam-rim-chen-mo", "BDRC:gsung-bum"}


def test_citation_with_no_extractable_id_is_recorded_as_unparsed():
    r = audit_answer(TSONGKHAPA, "见【《三主要道》(Lam gtso rnam gsum)】")
    assert r["fabricated"] == []
    assert r["unparsed"] == ["《三主要道》(Lam gtso rnam gsum)"]


def test_a_parseable_citation_is_not_recorded_as_unparsed():
    r = audit_answer(ATISHA, "见【《菩提道灯论》，Toh 4465】")
    assert r["unparsed"] == []
    assert "Toh:4465" in r["offline"]


def test_suttacentral_reference_is_unparsed_not_clean():
    """`【SC: AN 3.88】` 按契约就不做 id 级核对(语料库级来源),但那是「没查」,
    不是「查过没问题」。"""
    r = audit_answer(BUDDHAGHOSA, "见【SC: AN 3.88 / Sikkhā Sutta】")
    assert r["fabricated"] == []
    assert r["unparsed"] == ["SC: AN 3.88 / Sikkhā Sutta"]


def test_empty_citation_block_is_not_recorded():
    r = audit_answer(TSONGKHAPA, "格式示例:【】")
    assert r["unparsed"] == []


# ---------------------------------------------------------------------------
# 第四个契约家族:编集开示(compiled_teaching)。
#
# roadmap Phase 2 承诺 CBETA / Toh·BDRC / PTS·SuttaCentral / 编集开示四家平等,
# 前三家已实现,这一家一直是空的 —— 2026-08-31 全量跑里阿姜查的审计覆盖率因此是
# 0%(0/48),马哈希 23%(12/52)。「零伪造引用」在那两位身上不是清白,是沉默。
#
# 难点同样在归一化而非正则。声明写 `AjahnChah:StillForestPool`,行文写
# 《A Still Forest Pool》;声明 `Mahasi:ProgressOfInsight`,行文《The Progress of
# Insight (Visuddhiñāṇa-kathā)》;声明 `Mahasi:PracticalVipassana`,行文
# 《Practical Vipassanā Meditation Exercises》。只加正则不归一,会把这三条**正确**
# 引用全判成伪造 —— 比继续瞎着更糟。
# ---------------------------------------------------------------------------

AJAHN_CHAH = {
    "SuttaCentral",
    "AjahnChah:FoodForTheHeart",
    "AjahnChah:StillForestPool",
    "AjahnChah:LivingDhamma",
}
MAHASI = {
    "Mahasi:ManualOfInsight",
    "Mahasi:ProgressOfInsight",
    "Mahasi:PracticalVipassana",
    "Mahasi:DiscoursesOnSuttas",
    "SuttaCentral",
    "PTS:Vism",
}


def test_declared_compiled_teaching_cited_by_title_is_offline():
    ans = "放下不是抛弃。【《Food for the Heart》§Letting Go】（开示要旨）"
    r = audit_answer(AJAHN_CHAH, ans)
    assert r["fabricated"] == []
    assert "AjahnChah:FoodForTheHeart" in r["offline"]


def test_a_leading_article_does_not_make_a_correct_citation_fabricated():
    ans = "停止搅动，水自澄清。【《A Still Forest Pool》§The Forest Path】"
    r = audit_answer(AJAHN_CHAH, ans)
    assert r["fabricated"] == []
    assert "AjahnChah:StillForestPool" in r["offline"]


def test_a_leading_the_does_not_make_a_correct_citation_fabricated():
    ans = "至行舍智。【《The Progress of Insight》§行舍智】"
    r = audit_answer(MAHASI, ans)
    assert r["fabricated"] == []
    assert "Mahasi:ProgressOfInsight" in r["offline"]


def test_a_parenthetical_gloss_after_the_title_is_ignored():
    ans = "见观智次第。【《The Progress of Insight (Visuddhiñāṇa-kathā)》】"
    r = audit_answer(MAHASI, ans)
    assert r["fabricated"] == []
    assert "Mahasi:ProgressOfInsight" in r["offline"]


def test_diacritics_and_a_longer_subtitle_still_resolve_to_the_declared_work():
    ans = "以腹部起伏为主所缘。【《Practical Vipassanā Meditation Exercises》§标记法导引】"
    r = audit_answer(MAHASI, ans)
    assert r["fabricated"] == []
    assert "Mahasi:PracticalVipassana" in r["offline"]


def test_an_undeclared_compiled_teaching_is_flagged():
    """《Stillness Flowing》真有其书,但阿姜查的 meta.json 没声明它。"""
    ans = "巴蓬寺僧众每天诵念巴利。【《Stillness Flowing》——寺院日课】"
    r = audit_answer(AJAHN_CHAH, ans)
    assert any("Stillness Flowing" in f for f in r["fabricated"])


def test_a_shorter_title_does_not_satisfy_a_longer_declared_work():
    """前缀规则是有向的:声明比行文长,不算命中。"""
    ans = "【《Practical》§随便】"
    r = audit_answer(MAHASI, ans)
    assert r["offline"] == []
    assert any("Practical" in f for f in r["fabricated"])


def test_a_cjk_title_beside_a_declared_cbeta_id_adds_no_fabrication():
    """汉文书名不属编集开示家族;绝不能让正确的 CBETA 引用凭空多出一条伪造。"""
    ans = "自性本自清净。【《六祖坛经·般若品》，T48n2008】"
    r = audit_answer(HUINENG, ans)
    assert r["fabricated"] == []
    assert r["offline"] == ["T48n2008"]


def test_a_cjk_only_block_stays_unparsed_rather_than_fabricated():
    ans = "依《清净道论》所说。【《清净道论》§VII】"
    r = audit_answer(AJAHN_CHAH, ans)
    assert r["fabricated"] == []
    assert r["unparsed"] == ["《清净道论》§VII"]


def test_a_master_declaring_no_compiled_teaching_is_unaffected():
    """慧能没有编集开示来源,英文书名对他仍是「读不懂」,不是「伪造」。"""
    ans = "【《Food for the Heart》§Letting Go】"
    r = audit_answer(HUINENG, ans)
    assert r["fabricated"] == []
    assert r["unparsed"] == ["《Food for the Heart》§Letting Go"]


def test_a_live_link_still_whitewashes_an_unmatched_title():
    ans = "【《Stillness Flowing》】→ https://fojin.app/texts/58"
    r = audit_answer(AJAHN_CHAH, ans)
    assert r["fabricated"] == []
    assert len(r["live"]) == 1


def test_a_sutta_reference_in_book_brackets_is_not_a_compiled_teaching():
    """《MN 10 / Satipaṭṭhāna Sutta》是语料库级的 SuttaCentral 引用。

    它是拉丁书名、不匹配任何编集开示,一不小心就会被新家族判成伪造 —— 而
    prebuilt/master-ajahn-chah/references/teaching.md 里就有四条这种写法。
    把正确引用判成伪造比继续瞎着更糟,所以经号形态必须先被挡掉。
    """
    for title in (
        "《MN 10 / Satipaṭṭhāna Sutta》",
        "《SN 56.11 / Dhammacakkappavattana Sutta》",
        "《AN 3.65 / Kesamutti Sutta》",
        "《DN 16 / Mahāparinibbāna Sutta》",
        "《Dhp 276》",
        "《SC: MN 118 / Ānāpānasati Sutta》",
    ):
        r = audit_answer(AJAHN_CHAH, f"如经所说。【{title}】")
        assert r["fabricated"] == [], f"{title} 被误判为伪造"
        assert len(r["unparsed"]) == 1, f"{title} 应记为不可解析,而非放行"


def test_a_sutta_shaped_title_does_not_shadow_a_real_compiled_teaching():
    """挡经号不能顺手挡掉真书名 —— 书名里出现数字仍要能匹配。"""
    ans = "【《Food for the Heart》§Right Practice】"
    r = audit_answer(AJAHN_CHAH, ans)
    assert "AjahnChah:FoodForTheHeart" in r["offline"]


# ---------------------------------------------------------------------------
# 合集覆盖成员。Mahasi:DiscoursesOnSuttas 的 note 自己点了名
# ("Mālukyaputta Sutta / Dhammacakka Sutta / Sallekha Sutta 等开示集"),但人格
# 引某一篇具体开示时用的是篇目名 (《A Discourse on Dhammacakka Sutta》),不是合集
# CamelCase 名。2026-09-03 用户裁定:成员应可解析到它所属的合集。
#
# 设计成可选参数(member_aliases),不碰 declared_ids 的既有语义 —— 不给这个参数时
# 行为与之前完全一致,这条新能力不会悄悄改变别的祖师的判定。
# ---------------------------------------------------------------------------


def test_note_with_slash_delimited_members_yields_aliases():
    aliases = extract_member_aliases(
        "Mahasi:DiscoursesOnSuttas",
        "Mālukyaputta Sutta / Dhammacakka Sutta / Sallekha Sutta 等开示集，BPS Sri Lanka",
    )
    assert aliases == {
        "Mālukyaputta Sutta": "Mahasi:DiscoursesOnSuttas",
        "Dhammacakka Sutta": "Mahasi:DiscoursesOnSuttas",
        "Sallekha Sutta": "Mahasi:DiscoursesOnSuttas",
    }


def test_a_plain_bibliographic_note_yields_no_aliases():
    """没有 `/` 分隔就不是成员列表,不该被误读。"""
    aliases = extract_member_aliases(
        "Mahasi:ManualOfInsight",
        "1944 缅文巨著，2016 Wisdom Publications 英译（Vipassana Metta Foundation Translation Committee）",
    )
    assert aliases == {}


def test_a_single_word_segment_is_not_promiscuous_enough_to_alias():
    """单字词(如裸的 'Sutta')几乎每条引用都会命中,不能当别名。"""
    aliases = extract_member_aliases("X:Y", "Sutta / Vinaya 汇编")
    assert aliases == {}


def test_a_member_cited_with_extra_words_resolves_to_its_collection():
    aliases = {"Dhammacakka Sutta": "Mahasi:DiscoursesOnSuttas"}
    ans = "【《A Discourse on Dhammacakka Sutta》】"
    r = audit_answer(MAHASI, ans, member_aliases=aliases)
    assert r["fabricated"] == []
    assert "Mahasi:DiscoursesOnSuttas" in r["offline"]


def test_without_the_alias_the_same_citation_is_still_fabricated():
    """不传 member_aliases 时行为与之前完全一致 —— 向后兼容,默认不变。"""
    ans = "【《A Discourse on Dhammacakka Sutta》】"
    r = audit_answer(MAHASI, ans)
    assert any("Dhammacakka" in f for f in r["fabricated"])


def test_an_alias_for_a_different_master_does_not_leak_in():
    aliases = {"Dhammacakka Sutta": "Mahasi:DiscoursesOnSuttas"}
    ans = "【《Some Dhammacakka Sutta Commentary》】"
    r = audit_answer(HUINENG, ans, member_aliases=aliases)
    # 慧能没有 compiled_teaching 声明,不该因为传入了别人的别名表就多出一条判定。
    assert r["fabricated"] == []
    assert len(r["unparsed"]) == 1


def test_load_member_aliases_reads_the_real_mahasi_meta_json():
    aliases = load_member_aliases("mahasi-sayadaw")
    assert aliases.get("Dhammacakka Sutta") == "Mahasi:DiscoursesOnSuttas"


def test_the_real_mahasi_fixture_now_resolves_via_the_declared_collection():
    """回归 2026-08-31 那次跑的真实案例:马哈希 #12 引《A Discourse on
    Dhammacakka Sutta》曾被判 fabricated,而合集 note 里早就点了这篇的名。"""
    aliases = load_member_aliases("mahasi-sayadaw")
    ans = "【《A Discourse on Dhammacakka Sutta》】"
    r = audit_answer(MAHASI, ans, member_aliases=aliases)
    assert r["fabricated"] == []
    assert "Mahasi:DiscoursesOnSuttas" in r["offline"]


# ---------------------------------------------------------------------------
# The CLI entrypoint. Found by an independent code-review pass (2026-09-03):
# main() called audit_answer(declared, answer) without ever loading or
# passing member_aliases, so the CLI/CI-lint tool disagreed with the live
# grader (test-fidelity.py) on identical input — a citation that resolves
# cleanly through check_response() still reported as fabricated here, exit 1.
# ---------------------------------------------------------------------------


def test_cli_resolves_a_collection_member_the_same_way_the_live_judge_does():
    import subprocess

    result = subprocess.run(
        [
            "python3",
            "scripts/verify_citations.py",
            "--master",
            "mahasi-sayadaw",
        ],
        input="【《A Discourse on Dhammacakka Sutta》】",
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode == 0, result.stderr
    assert "fabricated: 1" not in result.stdout


# ---------------------------------------------------------------------------
# Found by an independent code-review pass (2026-09-03):
#
# 1. Member-alias matching accepted a real alias anywhere as a contiguous
#    token run inside the cited title, with no bound on surrounding text — so
#    a wholly invented title that happens to CONTAIN a real member name is
#    fully whitewashed. The real citation shape this feature exists for
#    ("A Discourse on Dhammacakka Sutta") always puts the alias as the
#    trailing part of the phrase, never buried with trailing padding after
#    it — matching on trailing position (bounded prefix, no suffix padding)
#    covers the real shape and closes the laundering path.
#
# 2. The primary declared-work prefix match picked the alphabetically-first
#    declared id whose tokens prefix the cited title, not the longest/most
#    specific one — so a shorter declared work whose tokens happen to prefix
#    a longer declared work's tokens can steal the citation.
# ---------------------------------------------------------------------------


def test_an_invented_title_padded_after_a_real_alias_is_not_whitewashed():
    aliases = {"Dhammacakka Sutta": "Mahasi:DiscoursesOnSuttas"}
    ans = "【《A Totally Invented Commentary on the Dhammacakka Sutta That Does Not Exist》】"
    r = audit_answer(MAHASI, ans, member_aliases=aliases)
    assert "Mahasi:DiscoursesOnSuttas" not in r["offline"]
    assert any("Dhammacakka" in f for f in r["fabricated"])


def test_a_real_member_alias_with_only_a_descriptive_prefix_still_resolves():
    """The actual shape this feature exists for keeps working."""
    aliases = {"Dhammacakka Sutta": "Mahasi:DiscoursesOnSuttas"}
    ans = "【《A Discourse on Dhammacakka Sutta》】"
    r = audit_answer(MAHASI, ans, member_aliases=aliases)
    assert r["fabricated"] == []
    assert "Mahasi:DiscoursesOnSuttas" in r["offline"]


def test_the_longest_matching_declared_work_wins_not_the_alphabetically_first():
    declared = {"AjahnChah:Food", "AjahnChah:FoodForTheHeart"}
    r = audit_answer(declared, "【《Food For The Heart》】")
    assert r["offline"] == ["AjahnChah:FoodForTheHeart"]
    assert "AjahnChah:Food" not in r["offline"]


# ---------------------------------------------------------------------------
# `base` lets load_declared_ids/load_member_aliases target a directory other
# than the real prebuilt/ — needed so validate-citation-references.py can
# import them instead of reimplementing the same meta.json parsing (found by
# an independent code-review pass, 2026-09-03) while still being testable
# against a tmp_path fixture rather than the real repo.
# ---------------------------------------------------------------------------


def test_load_declared_ids_accepts_a_base_directory(tmp_path):
    persona = tmp_path / "master-example"
    persona.mkdir()
    (persona / "meta.json").write_text(
        '{"sources": [{"type": "cbeta", "id": "T99n9999"}]}', encoding="utf-8"
    )
    ids = load_declared_ids("master-example", base=tmp_path)
    assert ids == {"T99n9999"}


def test_load_member_aliases_accepts_a_base_directory(tmp_path):
    persona = tmp_path / "master-example"
    persona.mkdir()
    (persona / "meta.json").write_text(
        '{"sources": [{"type": "compiled_teaching", "id": "X:Y", '
        '"note": "Foo Sutta / Bar Sutta 等开示集"}]}',
        encoding="utf-8",
    )
    aliases = load_member_aliases("master-example", base=tmp_path)
    assert aliases == {"Foo Sutta": "X:Y", "Bar Sutta": "X:Y"}


def test_load_declared_ids_without_base_still_reads_the_real_repo():
    assert load_declared_ids("huineng") == load_declared_ids("huineng", base=None)


def test_cjk_preceding_the_title_within_a_segment_does_not_drop_it():
    """Found by an independent code-review pass (2026-09-03): the original
    implementation took everything before the FIRST CJK character as the
    candidate title, assuming English always precedes CJK within a segment.
    If CJK comes first, the title was silently dropped — a safe failure
    (the term just stays unauditable rather than being wrongly cleared), but
    still a real gap: it fails on any note phrased "开示集包括 X" rather than
    "X 等开示集".
    """
    aliases = extract_member_aliases("X:Y", "开示集包括 Mālukyaputta Sutta / Dhammacakka Sutta")
    assert aliases == {
        "Mālukyaputta Sutta": "X:Y",
        "Dhammacakka Sutta": "X:Y",
    }
