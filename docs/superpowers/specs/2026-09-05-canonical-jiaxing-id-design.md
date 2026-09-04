# Canonical Jiaxing CBETA Identifier Design

**Date:** 2026-09-05
**Status:** Approved for automatic implementation by the user's standing instruction to continue without repeated confirmation

## Problem

`master-ouyi` declares 《靈峰蕅益大師宗論》 as `J36n0348`. Official CBETA
catalogue and reader records identify the work as `J36nB348` (嘉興藏 volume 36,
No.B348). The missing `B` has three effects:

1. shipped persona metadata and three CBETA Online links name a non-canonical id;
2. `tools/verify_sources.py` turns it into the non-canonical FoJin lookup
   `J0348` instead of `JB348`;
3. the answer auditor cannot recognise the canonical full or short form because
   its CBETA patterns only support numeric work numbers.

FoJin currently resolves neither `J0348` nor canonical `JB348` and returns no
title search result. Correcting the repository therefore fixes local truth but
does not close external issue #158; that issue must continue tracking FoJin's
missing canonical work.

## Source Of Truth

- Official CBETA reader: `https://tripitaka.cbeta.org/J36nB348_010`
- Full catalogue id: `J36nB348`
- Volume-free CBETA/FoJin lookup form: `JB348`

## Design

Support the exact identifier families this repository declares:

- Non-Jiaxing single-letter collections retain the source tool's existing
  numeric work-id support (for example `T08n0235`, `X62n1182`) and optional
  lowercase suffix.
- Jiaxing: `J36nB348`, with the required uppercase `B` before its work number.

`tools/verify_sources.py` will validate those forms and map `J36nB348` to
`JB348`. `scripts/verify_citations.py` will extract both `J36nB348` and `JB348`;
the short-form resolver will map the latter back to a declared full id. It will
continue extracting a malformed full-looking id such as `J36n0348` so that an
answer using it is classified as fabricated rather than silently unparsed, but
metadata validation will reject it.

## Files

- `tests/test_verify_sources.py`: specify canonical Jiaxing validation,
  shortening, and rejection of the numeric typo.
- `tests/test_verify_citations.py`: specify full/short canonical audit behavior
  and ensure the old typo is not accepted as declared.
- `tools/verify_sources.py`: implement collection-aware validation and `JB348`
  shortening.
- `scripts/verify_citations.py`: parse canonical alphanumeric CBETA numbers and
  resolve `JB348` to `J36nB348`.
- `prebuilt/master-ouyi/meta.json` and
  `prebuilt/master-ouyi/references/teaching.md`: ship the canonical id and URLs.
- Current comments/docs/tests that name the source: replace the erroneous id;
  historical reports keep their run data but use the canonical source name in
  later-status prose.
- `CHANGELOG.md`: disclose that the earlier declaration used the wrong id and
  that FoJin still lacks the corrected lookup.

## Non-goals

- Do not claim FoJin contains `JB348`; issue #158 remains open.
- Do not add a fabricated `fojin.app/texts/...` URL.
- Do not change stored evaluation JSON or adjudication verdict JSON.
- Do not broaden the existing non-J metadata syntax beyond its established
  single-letter, numeric-work-number behavior; add only Jiaxing's required
  `B`-prefixed work number as a collection-specific exception.

## Validation

Follow a strict red-green cycle for both parser surfaces, then run targeted
tests, the full `npm test` suite, the citation-reference sweep, and the FoJin
dry run. The final FoJin result should be 34/35 with `J36nB348 -> JB348` as the
only missing external lookup and zero URL replacements.
