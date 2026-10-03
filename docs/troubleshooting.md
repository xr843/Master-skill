# 常见问题

> 安装、调用、检索相关的常见问题。先跑一次 `npx master-skill doctor`，它会列出本机安装的问题和对应命令。

---

**Q：装完之后，对话里输入 `/master-huineng` 没反应 / 找不到命令？**

1. `npx master-skill doctor` 看 `Installed skills` 是否为 0；为 0 时它会给出安装命令。
2. 已经开着的会话可能没有读到新装的 skill，开一个新会话再试。
3. npx 装到 `~/.claude/skills/`，只有 Claude Code 与 OpenCode 读这里；Codex CLI、Gemini CLI 见下一条。
4. Claude Code **插件**装法下命令带前缀，显示为 `/master-skill:master-huineng`（输入不带前缀的名字会经自动补全解析到它）；Codex 显示为 `master-skill:master-huineng`。
5. 终端里提示 `master-skill: command not found`：CLI 没有全局安装，用 `npx master-skill …`，或 `npm install -g master-skill`。

**Q：Codex CLI / Gemini CLI 看不到任何祖师？**

两者都**不读** `~/.claude/skills/`，`npx master-skill install` 对它们无效。

- **Codex CLI**：按 [`.codex/INSTALL.md`](../.codex/INSTALL.md) 链接到 `~/.agents/skills/`。要先 `mkdir -p ~/.agents/skills`，否则 `ln` 会失败；`create-master` 必须链接整个仓库目录（文件符号链接会被 Codex 忽略）。用 `codex debug prompt-input "hi"` 可以看到模型实际拿到的 skill 列表。
- **Gemini CLI**：`gemini skills install https://github.com/xr843/Master-skill --path prebuilt`，`gemini skills list` 应列出 19 个。需要带 `skills` 子命令的 Gemini CLI：0.60.0 实测可用，0.25.x 没有这个子命令，请先升级。只装扩展（`gemini extensions install`）**不带来任何祖师**。详见 [install.md](install.md) 的 Gemini 小节。

**Q：`create-master` 报 `ModuleNotFoundError: No module named 'pypinyin'`（或 requests / yaml）？**

生成器的工具需要 Python 3.9+ 和几个第三方包。`npx master-skill doctor` 会报告缺哪个；安装：

```bash
python3 -m pip install -r ~/.claude/skills/create-master/requirements.txt
python3 ~/.claude/skills/create-master/tools/check_deps.py   # 复查，只用标准库
```

**Q：`npx master-skill install` 失败、提示本地修改，或报 ENOTEMPTY / 权限错误怎么办？**

**不要手动删除** `~/.claude/skills/master-<name>/`。当前版本（main，CHANGELOG [Unreleased]；0.12.16 及更早没有这项检查）在每个安装目录里写一份安装记录（`.master-skill-install.json`），用它识别你改过的文件：发现本地修改时 install / update 会停下并列出文件，而不是悄悄覆盖。手动删目录会把这些修改和记录一起丢掉。

- 先预览：`npx master-skill update --all --dry-run`
- 备份好自己的改动后，确定要用包内版本替换：`npx master-skill install <name> --force`（或 `update --all --force`）
- 替换失败时旧安装会自动回滚；如果回滚也失败，输出会给出旧安装所在的 `.master-<name>-backup-*` 目录，确认内容前不要删它
- npm 缓存问题：`npm cache clean --force` 后重跑。Windows 用户请在 PowerShell、Git Bash 或 WSL 中执行

**Q：FoJin API 不可达时还能用吗？**

能。每位预置法师的 `prebuilt/<name>/sources/` 收录了该法师声明来源的关键段落（离线摘录），回答先查离线资料，不足时才上 FoJin 实时检索。FoJin 不可达时，法师会标注"FoJin 暂不可达，以下为离线资料"，回落离线作答，不会因网络问题卡住。`/create-master` 管线遇到 API 故障会提示切换手动输入模式，由用户粘贴经文原文继续生成。

**Q：`master-skill recommend` 为什么对英文问题不推荐？**

`recommend` 按中文关键词匹配（外加少数英文模式词，如 compare / debate）。英文问题没有命中时，它会明说无法路由，而不是给一组默认祖师；请在对话里用 `/master-help` 直接描述你的情况。涉及轻生、自伤的表述，`recommend` 不推荐任何祖师，只给出危机求助渠道。

**Q：CBETA 引用格式是什么样的？来源如何验证？**

CBETA 引证使用 `Txxn####` 形式的经号（例如《妙法蓮華經》→ `T09n0262`）；藏传、南传与编纂开示分别使用 persona 在 `meta.json.sources[]` 中声明的 BDRC / Toh、SuttaCentral / PTS 或 teaching ID。`scripts/validate-citation-contract.py` 与 `tools/verify_sources.py --check-links/--final-check` 离线检查来源家族、ID 格式、声明归属和合同一致性；它们不解析正文自由文本，也不保证外部链接 HTTP 可达。旧版 `verify_sources.py --fix` 在线审计只覆盖 CBETA / FoJin 链接。

**Q：生成的法师内容和历史记载不符，怎么纠正？**

直接在对话中告诉法师"他不会这样说话"或"他应该更严厉一些"。`/create-master` 的纠正模式会识别纠正类型（教义纠正 → 追加到 `teaching.md`；风格纠正 → 追加到 `voice.md`），以 `## Correction` 块形式记录并自动递增 patch 版本号。纠正记录的优先级高于分析生成的内容。

**Q：如何贡献一位新的预置法师？**

见 [CONTRIBUTING.md](../CONTRIBUTING.md)。基本流程：遵循 v0.3 目录结构生成 `prebuilt/<name>/`、跑通 `scripts/validate.py --strict` 与 `scripts/validate-fidelity.py`，`tests/fidelity.jsonl` 至少 5 条且至少 1 条 boundary 用例（这是校验器的下限；现有每位祖师都有 10 条以上），然后提 PR。

---
