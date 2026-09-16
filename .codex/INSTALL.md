# Installing Master-skill for Codex

## Quick Install

```bash
git clone https://github.com/xr843/Master-skill.git ~/.codex/master-skill
mkdir -p ~/.agents/skills
ln -sfn ~/.codex/master-skill/prebuilt ~/.agents/skills/master-skill
ln -sfn ~/.codex/master-skill ~/.agents/skills/create-master
```

Restart Codex. It should list 20 skills: 15 personas, 4 teaching modes, and
`create-master`. Codex names a skill found under a linked directory after that
directory, so they appear as `master-skill:master-huineng`,
`master-skill:compare-masters`, and so on.

Measured with Codex CLI 0.153.4 on Linux, isolated HOME, 2026-09-16
(`codex debug prompt-input` shows the skills the model is given):

- Without the `mkdir -p`, both `ln` commands fail on a machine where
  `~/.agents/skills` does not exist yet.
- `create-master` must be a link to the whole checkout. A link to the root
  `SKILL.md` alone is a file symlink, and Codex skips it; the generator also
  needs the `prompts/` and `references/` beside it.
- `npx master-skill install` installs to `~/.claude/skills/`, which Codex does
  not read.

## Windows (PowerShell)

Not re-verified; mirrors the steps above.

```powershell
git clone https://github.com/xr843/Master-skill.git "$env:USERPROFILE\.codex\master-skill"
New-Item -ItemType Directory -Force "$env:USERPROFILE\.agents\skills" | Out-Null
cmd /c mklink /J "$env:USERPROFILE\.agents\skills\master-skill" "$env:USERPROFILE\.codex\master-skill\prebuilt"
cmd /c mklink /J "$env:USERPROFILE\.agents\skills\create-master" "$env:USERPROFILE\.codex\master-skill"
```

## Available Skills After Install

Run `npx master-skill list` for the current list with descriptions.

## Tool Mapping

| Skill references | Codex equivalent |
|---|---|
| `Read` | `read_file` |
| `Write` | `write_file` |
| `Edit` | `edit_file` |
| `Bash` | `shell` |
| `Grep` | `grep` |
| `Glob` | `glob` |
