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
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DIST = SITE / "dist"
CHAT = "https://fojin.app/chat"
SITE_URL = "https://fojin.ai"
ZH_NUM = "零一二三四五六七八九"


class SiteError(Exception):
    pass


# ---- upload bundles (Claude.ai / Gemini app) --------------------------------
# Since autumn 2026 ordinary chat apps take Agent Skills as an uploaded .zip:
# claude.ai (all plans, Customize > Skills > Upload) and the Gemini app
# (personal accounts, Customize > Skills > Upload). Our readers are there, not
# in a terminal, so every master gets a download at /_site/skills/<skill>.zip.
# Their rules differ from the terminal hosts':
#   - claude.ai's help page caps `description` at 200 characters (the spec says
#     1024; ours run 278-483). It doesn't say characters or bytes, so the upload
#     copy gets its own short description of at most 200 UTF-8 bytes.
#   - the zip's top folder must be named exactly like the skill.
#   - only the spec's frontmatter keys are kept; the rest move into `metadata`
#     (string values). meta.json, which carries the full source list, ships too.
#   - neither app lets a skill reach the network (Gemini says so outright), so
#     the persona falls back to its bundled excerpts — it already does that when
#     FoJin is unreachable.
# Teaching modes (compare / debate / curriculum) read the other masters'
# folders and stay terminal-only.
UPLOAD_DESC_MAX_BYTES = 200
UPLOAD_KEEP_KEYS = ("name", "description", "license")
UPLOAD_METADATA_KEYS = ("version", "lineage", "dates", "verified_by", "verified_at")
ZIP_DATE = (2026, 1, 1, 0, 0, 0)  # fixed, so the same sources give the same bytes


def upload_description(persona, copy):
    meta = persona["meta"]
    school = re.split(r"[（(]", copy["school"], maxsplit=1)[0]  # 律宗（南山律） -> 律宗
    first = next((short_title(x.get("title", "")) for x in meta.get("sources", [])
                  if short_title(x.get("title", ""))), "")
    desc = "%s（%s）AI 学修伴读：问%s，依《%s》等原典作答并附出处。AI 依文献生成，非祖师本人。" % (
        meta["name"], school, copy["ask"], first)
    if len(desc.encode("utf-8")) > UPLOAD_DESC_MAX_BYTES:
        # drop the source title before giving up
        desc = "%s（%s）AI 学修伴读：问%s，作答附原典出处。AI 依文献生成，非祖师本人。" % (
            meta["name"], school, copy["ask"])
    return desc


def upload_skill_md(text, description):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise SiteError("SKILL.md has no frontmatter")
    fm, body = m.group(1), text[m.end():]
    top = {}
    for key, val in re.findall(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$", fm, re.M):
        top[key] = val.strip()
    lines = ["---", "name: " + top["name"], "description: " + json.dumps(description, ensure_ascii=False)]
    if top.get("license"):
        lines.append("license: " + top["license"])
    meta = [(k, top[k].strip('"').strip("'")) for k in UPLOAD_METADATA_KEYS if top.get(k)]
    if meta:
        lines.append("metadata:")
        lines += ["  %s: %s" % (k, json.dumps(v, ensure_ascii=False)) for k, v in meta]
    lines.append("---")
    return "\n".join(lines) + "\n" + body


def upload_bundle(skill, description):
    """Bytes of <skill>.zip: <skill>/SKILL.md (rewritten frontmatter) and the
    rest of plugin/skills/<skill>/ as installed by the terminal hosts."""
    src = ROOT / "plugin" / "skills" / skill
    if not (src / "SKILL.md").is_file():
        raise SiteError("plugin/skills/%s/SKILL.md missing (run scripts/build-plugin-bundle.py)" % skill)
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(x for x in src.rglob("*") if x.is_file()):
            rel = f.relative_to(src).as_posix()
            data = f.read_bytes()
            if rel == "SKILL.md":
                data = upload_skill_md(data.decode("utf-8"), description).encode("utf-8")
            info = zipfile.ZipInfo("%s/%s" % (skill, rel), date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)
    return buf.getvalue()


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
        if slug in copy and len(upload_description(p, copy[slug]).encode("utf-8")) > UPLOAD_DESC_MAX_BYTES:
            problems.append("%s: upload description over %d bytes" % (slug, UPLOAD_DESC_MAX_BYTES))
        if not tradition_of(p["meta"]):
            problems.append("%s: meta.json has no tradition" % slug)
    if problems:
        raise SiteError("\n".join(problems))


def card_html(slug, persona, copy):
    """Compact card: name, dates, one line, the first declared source, two
    actions. The situation chips above the grid do the "who should I ask"
    job, so 适合问 is only the card's hover hint; the full source list lives
    in meta.json / docs/masters.md."""
    meta = persona["meta"]
    e = html.escape
    era = meta.get("era", "").replace("约", "约 ").replace("-", "–")
    trad = tradition_of(meta)
    first = sources_line(meta, limit=1)
    more = len({short_title(x.get("title", "")) for x in meta.get("sources", [])}) > 1
    if copy["web"]:
        ask = ('<a class="card-ask" data-master="%s" href="%s?master=%s&amp;utm_source=fojin.ai">提问 →</a>'
               % (e(slug), CHAT, e(slug)))
    else:
        ask = '<span class="off">网页版暂未上线</span>'
    return (
        '      <article class="card" id="m-{slug}" data-id="{slug}" data-t="{trad}" title="适合问：{hint}">\n'
        '        <div class="head"><div class="seal">{seal}</div><div><div class="name">{name}</div>'
        '<div class="meta">{era} · {trad} · {school}</div></div></div>\n'
        '        <p class="line">{line}</p>\n'
        '        <p class="src">依据：{src}{more}</p>\n'
        '        <div class="actions">{ask}<a class="card-dl" href="/_site/skills/{skill}.zip" download '
        'data-master="{slug}" title="装进 Claude 或 Gemini 网页版：见下方「安装」">下载技能包</a></div>\n'
        "      </article>"
    ).format(
        slug=e(slug), trad=e(trad), hint=e(copy["ask"]), seal=e(copy["seal"]), name=e(meta["name"]),
        era=e(era), school=e(copy["school"]), line=e(copy["line"]), src=e(first),
        more=" 等" if more else "", ask=ask, skill=e(persona["skill"]),
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
    # every other path there redirects to fojin.app). This page is served at
    # fojin.ai/masters; fojin.ai/ is the 引文溯源 page from the FoJin repo.
    (DIST / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE_URL, encoding="utf-8")
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url><loc>%s/</loc></url>\n"
        "  <url><loc>%s/masters</loc></url>\n"
        "  <url><loc>%s/developers</loc></url>\n"
        "</urlset>\n" % (SITE_URL, SITE_URL, SITE_URL), encoding="utf-8")
    for asset in (SITE / "assets").iterdir():
        shutil.copy2(asset, DIST / "_site" / asset.name)
    (DIST / "_site" / "skills").mkdir()
    for slug, p in personas.items():
        (DIST / "_site" / "skills" / (p["skill"] + ".zip")).write_bytes(
            upload_bundle(p["skill"], upload_description(p, cards["masters"][slug])))
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
