# fojin.ai home page

The page at **https://fojin.ai/** is built from this directory.

```bash
python3 site/build.py           # -> site/dist/  (index.html + _site/*.js)
python3 site/build.py --check   # validate only
```

## Where the content comes from

| Part of a master card | Source |
| --- | --- |
| name, dates, tradition, declared sources | `prebuilt/<skill>/meta.json` |
| skill name, install command | `skill-catalog.json` |
| seal text, short school label, one-line summary, 「适合问」, whether the web chat offers this master | `site/cards.json` |
| situation chips (「不知道该问谁」) | `site/cards.json` → `scenarios` |
| everything else on the page | `site/template.html`, `site/assets/` |

Adding a persona to `skill-catalog.json` without a card in `site/cards.json`
fails the build and `tests/test_site.py`. When a master goes live on
fojin.app/chat, set its `"web": true` — the card then links straight into that
lineage (`fojin.app/chat?master=<slug>`).

## How it is served

1. **Cloudflare Pages** builds this repository on every push to `main`
   (preview builds for other branches):
   build command `python3 site/build.py`, output directory `site/dist`.
2. **fojin.ai** is answered by the edge worker in the FoJin repository
   (`workers/fojin-ai-edge/`). It forwards `/` and `/_site/*` to the Pages
   site and keeps the domain's other jobs: the legacy service-worker
   kill-switch, `/developers` (the MCP / API portal) and the 301s that send old
   fojin.ai deep links to fojin.app. That worker also sets the page's security
   headers (CSP: no inline script — keep scripts in `site/assets/`).

The page's `<link rel="canonical">` is `https://fojin.ai/`, so the
`*.pages.dev` address is not indexed as a second copy.
