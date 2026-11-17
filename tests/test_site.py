"""The fojin.ai home page (site/) must cover exactly the shipped personas.

site/build.py generates the master cards from meta.json + skill-catalog.json
and fails when a persona has no hand-written card copy in site/cards.json.
These tests pin that contract, so adding or renaming a master without
updating the site turns CI red instead of shipping a site one master short.
"""

import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("site_build", ROOT / "site" / "build.py")
site_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(site_build)


@pytest.fixture(scope="module")
def sources():
    return site_build.load()


@pytest.fixture(scope="module")
def page(sources):
    personas, cards = sources
    site_build.validate(personas, cards)
    return site_build.render(personas, cards)


def test_every_persona_has_exactly_one_card(sources, page):
    personas, _ = sources
    ids = re.findall(r'<article class="card" id="m-([^"]+)"', page)
    assert sorted(ids) == sorted(personas)


def test_install_command_names_the_real_skill(sources, page):
    personas, _ = sources
    for slug, p in personas.items():
        assert 'data-copy="npx master-skill install %s"' % p["skill"] in page, slug


def test_cards_show_the_declared_sources(sources, page):
    personas, _ = sources
    for slug, p in personas.items():
        first = p["meta"]["sources"][0]
        assert site_build.short_title(first["title"]) in page, slug


def test_web_links_only_for_masters_offered_on_the_web(sources, page):
    _, cards = sources
    for slug, c in cards["masters"].items():
        linked = "/chat?master=%s&amp;utm_source=fojin.ai\">提问" % slug in page
        assert linked == c["web"], slug


def test_no_template_markers_left(page):
    assert "<!-- @" not in page


def test_persona_without_card_fails(sources):
    personas, cards = sources
    broken = copy.deepcopy(cards)
    broken["masters"].pop(next(iter(broken["masters"])))
    with pytest.raises(site_build.SiteError, match="no card"):
        site_build.validate(personas, broken)


def test_scenario_with_unknown_master_fails(sources):
    personas, cards = sources
    broken = copy.deepcopy(cards)
    broken["scenarios"].append({"label": "x", "pick": ["nobody"]})
    with pytest.raises(site_build.SiteError, match="unknown masters"):
        site_build.validate(personas, broken)


def test_count_follows_the_catalogue(sources, page):
    personas, _ = sources
    assert site_build.zh_count(len(personas)) + "位印度、汉传、藏传、南传祖师" in page
    assert '"description": "Buddhist master persona skills for AI agents: %d masters' % len(personas) in page
    assert site_build.zh_count(16) == "十六"
    assert site_build.zh_count(20) == "二十"
    assert site_build.zh_count(9) == "九"


def test_cards_json_is_valid_utf8_json():
    json.loads((ROOT / "site" / "cards.json").read_text(encoding="utf-8"))


def test_ask_box_offers_only_web_masters(sources, page):
    _, cards = sources
    options = set(re.findall(r'<option value="([^"]+)">', page))
    web = {slug for slug, c in cards["masters"].items() if c["web"]}
    assert options == web


def test_ask_box_submits_to_chat_with_autosend(page):
    form = re.search(r'<form class="ask"(.*?)</form>', page, re.S).group(0)
    assert 'action="https://fojin.app/chat"' in form
    assert 'name="q"' in form and 'name="master"' in form
    assert '<input type="hidden" name="send" value="1" />' in form


def test_example_question_naming_offline_master_fails(sources):
    _, cards = sources
    offline = [s for s, c in cards["masters"].items() if not c["web"]]
    if not offline:
        pytest.skip("every master is on the web")
    with pytest.raises(site_build.SiteError, match="not offered on the web"):
        site_build.check_template_links('<button data-m="%s">' % offline[0], cards)


def test_build_writes_robots_and_sitemap(tmp_path, monkeypatch):
    monkeypatch.setattr(site_build, "DIST", tmp_path / "dist")
    site_build.build()
    robots = (tmp_path / "dist" / "robots.txt").read_text(encoding="utf-8")
    assert "Sitemap: https://fojin.ai/sitemap.xml" in robots
    sitemap = (tmp_path / "dist" / "sitemap.xml").read_text(encoding="utf-8")
    assert "<loc>https://fojin.ai/</loc>" in sitemap
    assert (tmp_path / "dist" / "_site" / "site.js").exists()
