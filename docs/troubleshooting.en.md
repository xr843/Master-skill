# Troubleshooting

> Common install, invocation, and retrieval questions. Run `npx master-skill doctor` first: it lists local install problems and the command for each.

---

**Q: I installed, but typing `/master-huineng` does nothing / the command is not found.**

1. Run `npx master-skill doctor` and check `Installed skills`; at 0 it prints the install command.
2. A session that was already open may not have picked up new skills — start a new session.
3. npx installs to `~/.claude/skills/`, which only Claude Code and OpenCode read; for Codex CLI and Gemini CLI see the next question.
4. With the Claude Code **plugin** install, commands are prefixed: `/master-skill:master-huineng` (typing the bare name resolves to it through autocomplete). Codex shows `master-skill:master-huineng`.
5. `master-skill: command not found` in your shell means the CLI is not installed globally: use `npx master-skill …`, or `npm install -g master-skill`.

**Q: Codex CLI / Gemini CLI shows no masters at all.**

Neither reads `~/.claude/skills/`, so `npx master-skill install` does nothing for them.

- **Codex CLI**: link into `~/.agents/skills/` as in [`.codex/INSTALL.md`](../.codex/INSTALL.md). Run `mkdir -p ~/.agents/skills` first or the `ln` fails; `create-master` must link the whole checkout (Codex ignores file symlinks). `codex debug prompt-input "hi"` shows the skills the model actually receives.
- **Gemini CLI**: `gemini skills install https://github.com/xr843/Master-skill --path prebuilt`; `gemini skills list` should show 19. This needs a Gemini CLI that has the `skills` subcommand: 0.60.0 was verified, 0.25.x has none — upgrade first. Installing only the extension (`gemini extensions install`) brings **no masters**. See the Gemini section of [install.en.md](install.en.md).

**Q: `create-master` fails with `ModuleNotFoundError: No module named 'pypinyin'` (or requests / yaml).**

The generator's tools need Python 3.9+ and a few packages. `npx master-skill doctor` reports which are missing; install them with:

```bash
python3 -m pip install -r ~/.claude/skills/create-master/requirements.txt
python3 ~/.claude/skills/create-master/tools/check_deps.py   # re-check, standard library only
```

**Q: `npx master-skill install` stops on local modifications, or fails with ENOTEMPTY / a permission error.**

**Do not delete** `~/.claude/skills/master-<name>/` by hand. The current version (main, CHANGELOG [Unreleased]; 0.12.16 and earlier have no such check) writes an install record (`.master-skill-install.json`) into each installed skill and uses it to detect files you changed: install / update stop and list them instead of overwriting silently. Deleting the directory throws your edits and the record away together.

- Preview first: `npx master-skill update --all --dry-run`
- After backing up your edits, replace them with the packaged version on purpose: `npx master-skill install <name> --force` (or `update --all --force`)
- A failed replacement rolls back to the previous install; if the rollback also fails, the output names the `.master-<name>-backup-*` directory holding it — do not delete that before checking it
- npm cache trouble: `npm cache clean --force`, then rerun. On Windows, run from PowerShell, Git Bash or WSL

**Q: Does it still work when the FoJin API is unreachable?**

Yes. Each prebuilt master ships `prebuilt/<name>/sources/` — key passages from its declared sources, stored offline — and answers from them first, going to FoJin live retrieval only when they fall short. When FoJin is unreachable the master marks the reply "FoJin 暂不可达，以下为离线资料" (FoJin is unreachable; the following uses offline material) and answers offline rather than blocking. The `/create-master` pipeline asks the user to switch to manual-input mode when the API fails, so you can paste source text and continue.

**Q: Why does `master-skill recommend` not recommend anyone for an English question?**

`recommend` matches Chinese keywords (plus a few English mode words such as compare / debate, and common romanized terms such as nianfo / lamrim / huatou / vipassana). When an English question hits none, it says so plainly instead of offering a default pair; describe your situation to `/master-help` in the chat instead. For statements about suicide or self-harm, `recommend` names no master and prints crisis-help contacts only.

**Q: What does a valid CBETA citation look like, and how are sources verified?**

CBETA citations use a `Txxn####` identifier (for example, the Lotus Sutra is `T09n0262`); Tibetan, Pali, and compiled-teaching personas use the BDRC / Toh, SuttaCentral / PTS, or teaching IDs declared in `meta.json.sources[]`. `scripts/validate-citation-contract.py` and `tools/verify_sources.py --check-links/--final-check` validate source families, identifier shapes, declared membership, and contract consistency offline. They do not parse free-text citations or guarantee HTTP reachability. The legacy online `verify_sources.py --fix` audit covers CBETA / FoJin links only.

**Q: The generated master says things that don't match the historical record — how do I correct it?**

Just tell the master in-chat: "he wouldn't phrase it like that" or "he should sound more stern." The `/create-master` correction mode classifies the fix (doctrinal → appended to `teaching.md`; stylistic → appended to `voice.md`), writes it as a `## Correction` block with timestamp, and bumps the patch version. Correction blocks take priority over analysis-generated content at runtime.

**Q: How do I contribute a new prebuilt master?**

See [CONTRIBUTING.md](../CONTRIBUTING.md). The short version: follow the v0.3 layout under `prebuilt/<name>/`, pass `scripts/validate.py --strict` and `scripts/validate-fidelity.py` with zero errors, ship at least 5 fidelity cases in `tests/fidelity.jsonl` including at least one boundary case (the validator's minimum; every shipped master has 10+), then open a PR.

---
