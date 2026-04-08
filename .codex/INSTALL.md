# Installing Master-skill for Codex

## Quick Install

```bash
# Clone the repository
git clone https://github.com/xr843/Master-skill.git ~/.codex/master-skill

# Create skills symlink
ln -sf ~/.codex/master-skill/prebuilt ~/.agents/skills/master-skill
ln -sf ~/.codex/master-skill/SKILL.md ~/.agents/skills/create-master/SKILL.md
```

Restart Codex to discover the new skills.

## Windows (PowerShell)

```powershell
git clone https://github.com/xr843/Master-skill.git "$env:USERPROFILE\.codex\master-skill"
cmd /c mklink /J "$env:USERPROFILE\.agents\skills\master-skill" "$env:USERPROFILE\.codex\master-skill\prebuilt"
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

| Skill references | Codex equivalent |
|---|---|
| `Read` | `read_file` |
| `Write` | `write_file` |
| `Edit` | `edit_file` |
| `Bash` | `shell` |
| `Grep` | `grep` |
| `Glob` | `glob` |
