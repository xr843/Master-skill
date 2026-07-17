"""Tests for scripts/verify_citations.py — B1 引证核验,纯逻辑无网络。"""

import importlib

verify_citations = importlib.import_module("verify_citations")
audit_answer = verify_citations.audit_answer
load_declared_ids = verify_citations.load_declared_ids

# 慧能声明的离线源(与 prebuilt/master-huineng/meta.json 一致)
HUINENG = {"T48n2008", "T08n0235", "T14n0475"}


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


def test_load_declared_ids_real_master():
    """从真实 meta.json 读出慧能声明源。"""
    ids = load_declared_ids("huineng")
    assert {"T48n2008", "T08n0235", "T14n0475"} <= ids


def test_load_declared_ids_rejects_traversal():
    """path-traversal 的 master 名被拒。"""
    import pytest
    with pytest.raises(ValueError):
        load_declared_ids("../../etc")
