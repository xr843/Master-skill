# Framework review hardening

Implement the five improvements authorized after the 2026-10-01 review, in order.
Use the existing Python 3.9 runtime floor, no new runtime dependencies, no paid
evaluation during implementation. Historical reports remain historical; never
rewrite their evidence to make a new gate pass.

1. Citation evidence: unverified live links require review; distinguish source-ID
   resolution from direct-quote support. Check quotations against declared local
   original excerpts; missing excerpt evidence is unknown, not a fabrication verdict.
   Exercise invented links/quotes and genuine local quotations.
2. Release identity: fingerprint skill instructions, references, source declarations,
   sibling skills used by teaching modes, and evaluation code. Record fingerprints
   on measured suites and require current fingerprints at release. Old reports fail
   closed. Exercise edits, missing digests, and documentation-only changes.
3. Persona evaluation: use the same context loader as deterministic fidelity runs,
   cover all 15 personas with RAW/SPE/CUS and citation fixtures, retain curated
   existing rubrics, and validate coverage. Exercise actual prompt rendering and drift.
4. Installation: stage every replacement, roll back failures, persist installation
   file hashes, detect local modifications before replacement, provide --dry-run and
   --force. Old installations without an inventory are conservatively protected.
   Preserve generated masters and existing all-skill update semantics. Exercise
   user edits, upstream updates, copy/swap failures, legacy installs and previews.
5. Query: --json always returns an array, including zero hits. Exercise CLI output.

Each behavioral change gets a failing regression test before implementation.
Run focused checks per task, then npm test and hook checks; report any desktop
verification limitations separately. Implement sequentially in this branch.

## Implementation verification

All five tasks implemented. Independent review reproduced and closed quote-format,
preceding-attribution and declared-ID-link bypasses. Installation tests also cover
rejecting unsupported uninstall previews and preserving generated-persona links.

- `npm test`: all structural gates, 102 CLI tests and 1334 Python tests passed.
- `npm run test:hook`: 36 tests passed.
- `cargo +1.95.0 test --locked` in `desktop/`: 133 tests passed.
- No paid model sweep was launched, no historical measurement was rewritten, and
  no package was published. The new 15-persona rubrics remain advisory until calibrated.
