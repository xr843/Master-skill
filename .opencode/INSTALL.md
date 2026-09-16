# Installing Master-skill for OpenCode

## Quick Install

```bash
npx master-skill install --all
```

OpenCode reads `~/.claude/skills/` without any configuration, and that is where
this installs. `opencode debug skill` should list 20 skills: 15 personas, 4
teaching modes, and `create-master`.

## From a Checkout

Point `skills.paths` in `opencode.json` at the checkout's `prebuilt/`:

```json
{
  "skills": { "paths": ["/absolute/path/to/Master-skill/prebuilt"] }
}
```

That gives the 19 skills under `prebuilt/`. `create-master` lives at the
repository root, outside it.

## Pin a Version

```bash
npx master-skill@<version> install --all
```

## Not a Plugin

Earlier versions of this page said to add

```json
{ "plugin": ["master-skill@git+https://github.com/xr843/Master-skill.git"] }
```

OpenCode plugins are JavaScript modules, and this repository ships none. With
that entry `opencode debug skill` lists none of these skills.

Measured with OpenCode 1.18.13 on Linux, isolated HOME, 2026-09-16.

## Available Skills After Install

Run `npx master-skill list` for the current list with descriptions.

## Tool Mapping

| Skill references | OpenCode equivalent |
|---|---|
| `Read` | `read_file` |
| `Write` | `write_file` |
| `Edit` | `edit_file` |
| `Bash` | `shell` |
| `Grep` | `grep` |
| `Glob` | `glob` |
| `Skill` | `skill` (native) |
