# 常见问题

> 安装、调用、检索相关的常见问题。

---

**Q：FoJin API 不可达时还能用吗？**

能。每位预置法师的 `prebuilt/<name>/sources/` 收录了该法师核心经典的关键段落（离线经文片段）。FoJin 不可用时，法师会降级到离线模式并在回答中声明"当前使用离线片段"。`/create-master` 管线遇到 API 故障会提示用户切换手动输入模式，由用户粘贴经文原文继续生成。

**Q：CBETA 引用格式是什么样的？来源如何验证？**

CBETA 引证使用 `Txxn####` 形式的经号（例如《妙法蓮華經》→ `T09n0262`）；藏传、南传与编纂开示分别使用 persona 在 `meta.json.sources[]` 中声明的 BDRC / Toh、SuttaCentral / PTS 或 teaching ID。`scripts/validate-citation-contract.py` 与 `tools/verify_sources.py --check-links/--final-check` 离线检查来源家族、ID 格式、声明归属和合同一致性；它们不解析正文自由文本，也不保证外部链接 HTTP 可达。旧版 `verify_sources.py --fix` 在线审计只覆盖 CBETA / FoJin 链接。

**Q：`npx master-skill install` 执行失败、报 ENOTEMPTY 或权限错误怎么办？**

先清理 `~/.claude/skills/master-<name>/` 残留目录再重试。如果是 npm 缓存问题，`npm cache clean --force` 后重跑 NPX。Windows 用户请在 Git Bash 或 WSL 中执行，避免 cmd.exe 的路径转义问题。

**Q：生成的法师内容和历史记载不符，怎么纠正？**

直接在对话中告诉法师"他不会这样说话"或"他应该更严厉一些"。`/create-master` 的纠正模式会识别纠正类型（教义纠正 → 追加到 `teaching.md`；风格纠正 → 追加到 `voice.md`），以 `## Correction` 块形式记录并自动递增 patch 版本号。纠正记录的优先级高于分析生成的内容。

**Q：如何贡献一位新的预置法师？**

见下方「贡献指南」。基本流程：遵循 v0.3 目录结构生成 `prebuilt/<name>/`、跑通 `scripts/validate.py --strict`、补齐 `tests/fidelity.jsonl` 的 5 条以上样例，然后提 PR。

---
