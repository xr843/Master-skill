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
        assert "npx master-skill install %s</code>" % p["skill"] in page, slug


def test_cards_show_the_declared_sources(sources, page):
    personas, _ = sources
    for slug, p in personas.items():
        first = p["meta"]["sources"][0]
        assert site_build.short_title(first["title"]) in page, slug


def test_web_links_only_for_masters_offered_on_the_web(sources, page):
    _, cards = sources
    for slug, c in cards["masters"].items():
        linked = "/chat?master=%s&amp;" % slug in page
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
    assert "<b>%d</b> 位祖师" % len(personas) in page
    assert site_build.zh_count(16) == "十六"
    assert site_build.zh_count(20) == "二十"
    assert site_build.zh_count(9) == "九"


def test_cards_json_is_valid_utf8_json():
    json.loads((ROOT / "site" / "cards.json").read_text(encoding="utf-8"))
