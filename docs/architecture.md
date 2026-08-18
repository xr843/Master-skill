# 架构图

> Master-skill 的目录结构与数据流。

---

```
用户请求
    |
    v
session-start hook ──> 自动注入法师列表（5 端统一）
    |
    v
SKILL.md (AgentSkills 入口：决策树 + Quick Ref)
    |
    +-- 预置法师 --> prebuilt/{slug}/
    |                   +-- SKILL.md          (决策树 + <HARD-GATE> 铁律)
    |                   +-- meta.json         (version / lineage / provenance)
    |                   +-- references/       (按需加载)
    |                   |   +-- teaching.md
    |                   |   +-- voice.md
    |                   +-- sources/          (离线经文片段)
    |                   |   +-- *.md (声明来源的离线段落)
    |                   +-- tests/
    |                       +-- fidelity.jsonl  (保真度样例, CI dry-run)
    |
    +-- 工具链
    |   +-- scripts/validate.py         (frontmatter linter)
    |   +-- scripts/cite.py             (CBETA 引用查询)
    |   +-- scripts/query.py            (离线语义检索)
    |   +-- scripts/test-fidelity.py    (保真度测试)
    |   +-- scripts/validate-fidelity.py
    |   +-- bin/cli.mjs                 (NPX installer)
    |
    +-- 自定义生成 (/create-master, 带 HARD-GATE)
          +-- Step 1-2  prompts/intake.md → tools/sutra_collector.py
          |             └─> FoJin API (KG + 语义检索 + 文本)
          +-- Step 3    prompts/{sutra,voice}_analyzer.md → 两阶段分析
          +-- Step 3.5  二阶段独立审查 ──┬─ prompts/doctrine_reviewer.md
          |                             └─ prompts/voice_reviewer.md
          +-- Step 4-5  tools/master_builder.py → tools/skill_writer.py
                        └─> tools/verify_sources.py (写入前最终验证)

多平台插件统一入口：
  .claude-plugin/    → Claude Code      (hooks/run-hook.cmd → session-start)
  .cursor-plugin/    → Cursor           (hooks/hooks-cursor.json)
  .codex/            → Codex CLI        (.codex/INSTALL.md)
  .opencode/         → OpenCode         (opencode.json 引用)
  gemini-extension.json → Gemini CLI    (GEMINI.md 自动加载)
```

---
