# Installing Master-skill for OpenCode

## Quick Install

Add to your `opencode.json`:

```json
{
  "plugin": ["master-skill@git+https://github.com/xr843/Master-skill.git"]
}
```

OpenCode will automatically install and register all skills.

## Pin a Version

```json
{
  "plugin": ["master-skill@git+https://github.com/xr843/Master-skill.git#v0.3.0"]
}
```

## Available Skills After Install

- `/xuanzang` — Xuanzang (Yogacara)
- `/kumarajiva` — Kumarajiva (Madhyamaka)
- `/huineng` — Huineng (Chan/Zen)
- `/zhiyi` — Zhiyi (Tiantai)
- `/fazang` — Fazang (Huayan)
- `/yinguang` — Yinguang (Pure Land)
- `/ouyi` — Ouyi (Tiantai-Pure Land)
- `/xuyun` — Xuyun (Chan, Five Schools)
- `/compare-masters` — Multi-tradition comparison
- `/create-master` — Generate new master

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
