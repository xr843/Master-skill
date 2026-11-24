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
        assert 'href="/_site/skills/%s.zip" download' % p["skill"] in page, slug


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
    assert "<loc>https://fojin.ai/masters</loc>" in sitemap
    assert (tmp_path / "dist" / "_site" / "site.js").exists()


def test_page_is_canonical_at_masters():
    # fojin.ai/ is the 引文溯源 page now; this catalogue lives at /masters.
    page = site_build.build(check_only=True)
    assert '<link rel="canonical" href="https://fojin.ai/masters" />' in page
    assert '<a href="/" title="贴一段文字，逐句核对是否出自佛经">核对出处</a>' in page


# --- colour contrast (WCAG AA) -------------------------------------------
# axe found 197 contrast failures on the live pages on 2026-11-17, all caused
# by a handful of tokens. These pin the token pairs so a palette tweak that
# drops below 4.5:1 fails here rather than in a visitor's eyes.

def _tokens(block):
    return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;", block))


def _luminance(hex_colour):
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a, b):
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _themes():
    template = (ROOT / "site" / "template.html").read_text(encoding="utf-8")
    light = _tokens(re.search(r":root \{(.*?)\n  \}", template, re.S).group(1))
    dark = dict(light, **_tokens(re.search(r':root\[data-theme="dark"\] \{(.*?)\n  \}', template, re.S).group(1)))
    return {"light": light, "dark": dark}


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_colours_meet_wcag_aa(theme):
    t = _themes()[theme]
    backgrounds = ["bg", "bg-2", "surface", "surface-2"]
    failures = []
    for fg in ("text", "muted", "faint", "accent"):
        for bg in backgrounds:
            ratio = _contrast(t[fg], t[bg])
            if ratio < 4.5:
                failures.append("%s on %s = %.2f" % (fg, bg, ratio))
    for seal in ("t-india", "t-han", "t-tibet", "t-pali", "seal"):
        ratio = _contrast("#ffffff", t[seal])
        if seal != "seal" and ratio < 4.5:  # --seal only colours the large brand mark
            failures.append("white on %s = %.2f" % (seal, ratio))
    ratio = _contrast(t["accent-ink"], t["accent"])
    if ratio < 4.5:
        failures.append("accent-ink on accent = %.2f" % ratio)
    assert failures == []


def test_analytics_only_reports_from_fojin_ai():
    # copies of the page (and *.pages.dev previews) must not write into fojin's stats
    page = site_build.build(check_only=True)
    assert 'data-domains="fojin.ai,www.fojin.ai"' in page


def test_header_nav_matches_the_other_fojin_ai_pages():
    # fojin.ai's three pages share one header: 核对出处 · 祖师 · 开发者 · 读经站, the
    # current page always marked (2026-11-24). Here 祖师 used to be an in-page #masters
    # anchor lit only while that section scrolled by, next to 安装 and GitHub.
    import re
    page = site_build.build(check_only=True)
    nav = re.search(r'<nav class="links"[^>]*>(.*?)</nav>', page, re.S).group(1)
    labels = re.findall(r'<a [^>]*>([^<]+)', nav)
    assert labels == ["核对出处", "祖师", "开发者", "读经站"]
    assert '<a href="/masters" aria-current="page">祖师</a>' in nav
    assert "#install" not in nav and "github.com" not in nav
    # every section shows at every width — nothing hidden on phones (2026-11-24)
    assert 'class="opt"' not in nav



def test_upload_bundles_fit_claude_and_gemini(tmp_path, monkeypatch):
    # claude.ai / Gemini uploads (2026-11-24): top folder named like the skill,
    # description <= 200 bytes (claude.ai's help page says 200; unit not stated),
    # only spec frontmatter keys at the top level, same bytes on every build.
    import io, re, zipfile
    monkeypatch.setattr(site_build, "DIST", tmp_path / "dist")
    site_build.build()
    personas, _ = site_build.load()
    zips = sorted((tmp_path / "dist" / "_site" / "skills").glob("*.zip"))
    assert [z.stem for z in zips] == sorted(p["skill"] for p in personas.values())
    for z in zips:
        names = zipfile.ZipFile(z).namelist()
        assert all(n.startswith(z.stem + "/") for n in names), z.name
        md = zipfile.ZipFile(z).read(z.stem + "/SKILL.md").decode("utf-8")
        fm = re.match(r"---\n(.*?)\n---\n", md, re.S).group(1)
        top = re.findall(r"^([A-Za-z_][\w-]*):", fm, re.M)
        assert set(top) <= {"name", "description", "license", "metadata"}, (z.name, top)
        assert re.search(r"^name: %s$" % z.stem, fm, re.M)
        desc = json.loads(re.search(r"^description: (.*)$", fm, re.M).group(1))
        assert len(desc.encode("utf-8")) <= 200 and "非祖师本人" in desc, z.name
        assert not any(n.endswith(("fidelity.jsonl",)) for n in names), z.name
    first = {z.name: z.read_bytes() for z in zips}
    site_build.build()
    assert first == {z.name: z.read_bytes() for z in sorted((tmp_path / "dist" / "_site" / "skills").glob("*.zip"))}
