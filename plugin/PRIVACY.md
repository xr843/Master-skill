# Privacy policy — Master-skill

Last updated: 2026-10-20

Master-skill is a set of Claude skills (Buddhist teacher personas, teaching
modes and a persona generator). This policy covers the plugin and the
`master-skill` repository it is built from.

## What the plugin collects

Nothing. The plugin has no server, no analytics, no telemetry and no account.
The author receives no data from your use of it. It does not read, store or
send personal data such as names, email addresses or postal addresses, and it
does not read credentials.

## What runs on your machine

- **SessionStart hook.** One `echo` of a fixed sentence. It reads nothing,
  writes nothing and contacts nothing.
- **Personas and teaching modes** answer from the files bundled in the plugin.
  The bundled scripts `scripts/cite.py` and `scripts/query.py` search those
  files locally.
- **`create-master`**, only when you run it, writes the persona it generates to
  `skills/create-master/masters/` on your own machine.

Anything the skills run goes through your host's normal tool-permission prompt.

## What is sent off your machine, and to whom

1. **Optional passage look-up (personas).** When the bundled excerpts do not
   cover a question, a persona may look the passage up in FoJin's public,
   read-only API at `https://fojin.app/api/`. Only the search terms for that
   passage are sent; no conversation content, personal data or credentials.
   FoJin (fojin.app) is run by the same author as this plugin and is served
   through Cloudflare, which handles each request under its own privacy
   policy. FoJin's web server
   keeps standard access logs, which include the request URL and therefore
   the search terms, together with the requesting IP address; these logs are
   used only to operate and protect the service and are deleted on rotation
   within 30 days (currently about 11 days: rotated daily, ten kept). Its
   application logs are capped by size and overwritten within days. FoJin
   does not sell or share them.
2. **`create-master` (only when you run it)** sends the master name and the
   search keywords you give it to these public, read-only services: the FoJin
   REST API (`https://fojin.app`, or the address you set in `FOJIN_URL`), the
   CBETA API (`https://cbdata.dila.edu.tw`), SuttaCentral
   (`https://suttacentral.net`), BDRC (`https://ldspdi.bdrc.io`), and two public
   text mirrors used to verify quotations (`raw.githubusercontent.com/daizhige-org`,
   `bookgb.bfnn.org`). Those services are run by third parties under their own
   policies; the plugin sends them nothing beyond the request itself.
3. **Links in answers** (fojin.app, CBETA, SuttaCentral) are opened only if you
   follow them.

Claude itself, and the host you run it in, process your conversation under
Anthropic's and that host's own terms; this plugin adds nothing to that.

## Children

The plugin is a study aid for adults and is not directed at children under 18.

## Changes and contact

Changes to this policy are made in this file, and its history is public in the
repository. Questions: open an issue at
<https://github.com/xr843/Master-skill/issues>, or email
xianren843@protonmail.com.
