#!/usr/bin/env python3
"""Build the fojin.ai home page from the skill sources.

    python3 site/build.py            # writes site/dist/
    python3 site/build.py --check    # validate only, write nothing

Where each part of a master card comes from:

- name, dates, tradition, declared sources -> prebuilt/<skill>/meta.json
- skill name and install command           -> skill-catalog.json
- seal text, short school label, one-line
  summary, "适合问", web availability       -> site/cards.json (meta.json has
                                              no field for these)

So adding a persona to skill-catalog.json without a card in site/cards.json
fails the build (and tests/test_site.py), instead of silently leaving the site
one master short. Lives under site/ rather than scripts/ because scripts/ is
shipped in the npm package and this is not part of the skill.
"""

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DIST = SITE / "dist"
CHAT = "https://fojin.app/chat"
SITE_URL = "https://fojin.ai"
ZH_NUM = "零一二三四五六七八九"


class SiteError(Exception):
    pass


def zh_count(n):
    if n < 10:
        return ZH_NUM[n]
    if n < 20:
        return "十" + (ZH_NUM[n - 10] if n > 10 else "")
    if n < 100:
        tens, ones = divmod(n, 10)
        return ZH_NUM[tens] + "十" + (ZH_NUM[ones] if ones else "")
    return str(n)


def short_title(title):
    """'菩提道灯论 (Bodhipathapradīpa, ...)' -> '菩提道灯论'."""
    title = re.split(r"\s*[（(]", title, maxsplit=1)[0].strip()
    # A title that already carries its own book-title marks (《父法》《子法》)
    # would come out double-wrapped.
    return title.strip("《》")


def tradition_of(meta):
    """'藏传 (印藏桥梁)' -> '藏传'; the filter tabs key on this."""
    return re.split(r"[\s(（]", meta.get("tradition", ""), maxsplit=1)[0]


def sources_line(meta, limit=3):
    seen, parts = set(), []
    for src in meta.get("sources", []):
        title = short_title(src.get("title", ""))
        if not title or title in seen:
            continue
        seen.add(title)
        ref = src.get("id", "") if src.get("type") == "cbeta" else ""
        parts.append("《%s》%s" % (title, ref))
        if len(parts) == limit:
            break
    return " · ".join(parts)


def load():
    catalog = json.loads((ROOT / "skill-catalog.json").read_text(encoding="utf-8"))
    cards = json.loads((SITE / "cards.json").read_text(encoding="utf-8"))
    personas = {}
    for skill in catalog["skills"]:
        if skill.get("kind") != "persona":
            continue
        meta = json.loads((ROOT / skill["source"] / "meta.json").read_text(encoding="utf-8"))
        personas[meta["slug"]] = {"skill": skill["name"], "meta": meta}
    return personas, cards


def validate(personas, cards):
    problems = []
    copy = cards.get("masters", {})
    missing = sorted(set(personas) - set(copy))
    extra = sorted(set(copy) - set(personas))
    if missing:
        problems.append("no card in site/cards.json for: " + ", ".join(missing))
    if extra:
        problems.append("site/cards.json has cards for unknown masters: " + ", ".join(extra))
    for slug, c in copy.items():
        for field in ("seal", "school", "line", "ask"):
            if not str(c.get(field, "")).strip():
                problems.append("%s: empty '%s'" % (slug, field))
        if not isinstance(c.get("web"), bool):
            problems.append("%s: 'web' must be true or false" % slug)
    for sc in cards.get("scenarios", []):
        bad = [p for p in sc.get("pick", []) if p not in personas]
        if bad or not sc.get("pick"):
            problems.append("scenario %r picks unknown masters: %s" % (sc.get("label"), bad))
    for slug, p in personas.items():
        if not tradition_of(p["meta"]):
            problems.append("%s: meta.json has no tradition" % slug)
    if problems:
        raise SiteError("\n".join(problems))


def card_html(slug, persona, copy):
    meta = persona["meta"]
    e = html.escape
    era = meta.get("era", "").replace("约", "约 ").replace("-", "–")
    trad = tradition_of(meta)
    if copy["web"]:
        action = '<a href="%s?master=%s&amp;utm_source=fojin.ai">依此宗风提问 →</a>' % (CHAT, e(slug))
    else:
        action = '<span class="off">网页版暂未上线，可在终端安装使用</span>'
    cmd = "npx master-skill install " + persona["skill"]
    return (
        '      <article class="card" id="m-{slug}" data-id="{slug}" data-t="{trad}">\n'
        '        <div class="head"><div class="seal">{seal}</div><div><div class="name">{name}</div>'
        '<div class="meta">{era} · {trad} · {school}</div></div></div>\n'
        '        <p class="line">{line}</p>\n'
        '        <p class="ask"><b>适合问</b>　{ask}</p>\n'
        '        <p class="src">依据：{src}</p>\n'
        '        <div class="actions">{action}</div>\n'
        '        <div class="cmd"><code>{cmd}</code><button class="copy" type="button">复制</button></div>\n'
        "      </article>"
    ).format(
        slug=e(slug), trad=e(trad), seal=e(copy["seal"]), name=e(meta["name"]), era=e(era),
        school=e(copy["school"]), line=e(copy["line"]), ask=e(copy["ask"]),
        src=e(sources_line(meta)), action=action, cmd=e(cmd),
    )


def master_options(personas, cards):
    """<option>s for the hero ask box: only masters fojin.app/chat offers."""
    rows = []
    for slug, c in cards["masters"].items():
        if not c["web"]:
            continue
        rows.append('            <option value="%s">%s · %s</option>'
                    % (html.escape(slug), html.escape(personas[slug]["meta"]["name"]), html.escape(c["school"])))
    return "\n".join(rows)


def check_template_links(template, cards):
    """Example questions (data-m) must name a master the web chat offers."""
    web = {slug for slug, c in cards["masters"].items() if c["web"]}
    bad = sorted(set(re.findall(r'data-m="([^"]+)"', template)) - web)
    if bad:
        raise SiteError("template example questions name masters not offered on the web: " + ", ".join(bad))


def render(personas, cards):
    template = (SITE / "template.html").read_text(encoding="utf-8")
    check_template_links(template, cards)
    copy = cards["masters"]
    cards_html = "\n\n".join(card_html(slug, personas[slug], copy[slug]) for slug in copy)
    chips_html = "\n".join(
        '      <button class="chip" data-pick="%s">%s</button>'
        % (html.escape(" ".join(sc["pick"])), html.escape(sc["label"]))
        for sc in cards["scenarios"]
    )
    out = (
        template.replace("<!-- @CARDS -->", cards_html)
        .replace("<!-- @CHIPS -->", chips_html)
        .replace("<!-- @MASTER_OPTIONS -->", master_options(personas, cards))
        .replace("<!-- @COUNT_ZH -->", zh_count(len(copy)))
        .replace("<!-- @COUNT -->", str(len(copy)))
    )
    leftover = re.findall(r"<!-- @[A-Z_]+ -->", out)
    if leftover:
        raise SiteError("unreplaced markers in template: " + ", ".join(sorted(set(leftover))))
    return out


def build(check_only=False):
    personas, cards = load()
    validate(personas, cards)
    page = render(personas, cards)
    if check_only:
        return page
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "_site").mkdir(parents=True)
    (DIST / "index.html").write_text(page, encoding="utf-8")
    # fojin.ai's own crawler files (the edge worker forwards these two paths;
    # every other path there redirects to fojin.app).
    (DIST / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE_URL, encoding="utf-8")
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url><loc>%s/</loc></url>\n"
        "  <url><loc>%s/developers</loc></url>\n"
        "</urlset>\n" % (SITE_URL, SITE_URL), encoding="utf-8")
    for asset in (SITE / "assets").iterdir():
        shutil.copy2(asset, DIST / "_site" / asset.name)
    return page


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="validate only, write nothing")
    args = parser.parse_args()
    try:
        build(check_only=args.check)
    except SiteError as exc:
        print("site build failed:\n" + str(exc), file=sys.stderr)
        return 1
    print("site OK" if args.check else "site built -> %s" % DIST.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
