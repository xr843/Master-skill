# Troubleshooting

> Common install, invocation, and retrieval questions.

---

**Q: Does it still work when the FoJin API is unreachable?**

Yes. Each prebuilt master ships with `prebuilt/<name>/sources/` — key passages from that master's core canon, stored offline. When FoJin is down, the master degrades to offline mode and declares "currently running on offline passages" in the reply. The `/create-master` pipeline asks the user to switch to manual-input mode when the API fails, so you can paste source text and continue.

**Q: What does a valid CBETA citation look like, and how are sources verified?**

CBETA citations use a `Txxn####` identifier (for example, the Lotus Sutra is `T09n0262`); Tibetan, Pali, and compiled-teaching personas use the BDRC / Toh, SuttaCentral / PTS, or teaching IDs declared in `meta.json.sources[]`. `scripts/validate-citation-contract.py` and `tools/verify_sources.py --check-links/--final-check` validate source families, identifier shapes, declared membership, and contract consistency offline. They do not parse free-text citations or guarantee HTTP reachability. The legacy online `verify_sources.py --fix` audit covers CBETA / FoJin links only.

**Q: `npx master-skill install` fails with ENOTEMPTY or a permission error — what now?**

Clean up any leftover `~/.claude/skills/master-<name>/` directories before retrying. For npm-cache weirdness, run `npm cache clean --force` and rerun NPX. Windows users should execute from Git Bash or WSL to avoid cmd.exe path-escaping issues.

**Q: The generated master says things that don't match the historical record — how do I correct it?**

Just tell the master in-chat: "he wouldn't phrase it like that" or "he should sound more stern." The `/create-master` correction mode classifies the fix (doctrinal → appended to `teaching.md`; stylistic → appended to `voice.md`), writes it as a `## Correction` block with timestamp, and bumps the patch version. Correction blocks take priority over analysis-generated content at runtime.

**Q: How do I contribute a new prebuilt master?**

See "Contributing" below. The short version: follow the v0.3 layout under `prebuilt/<name>/`, pass `scripts/validate.py --strict` with zero errors, ship at least 5 fidelity Q&A samples in `tests/fidelity.jsonl`, then open a PR.

---
