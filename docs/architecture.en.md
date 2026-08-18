# Architecture

> Directory layout and data flow.

---

```
User request
    |
    v
session-start hook ──> auto-injects master list (5 platforms, unified)
    |
    v
SKILL.md (AgentSkills entry: decision tree + quick reference)
    |
    +-- Pre-built masters --> prebuilt/{slug}/
    |                           +-- SKILL.md          (decision tree + <HARD-GATE>)
    |                           +-- meta.json         (version / lineage / provenance)
    |                           +-- references/       (loaded on demand)
    |                           |   +-- teaching.md
    |                           |   +-- voice.md
    |                           +-- sources/          (offline declared-source passages)
    |                           |   +-- *.md
    |                           +-- tests/
    |                               +-- fidelity.jsonl  (CI dry-run samples)
    |
    +-- Offline toolchain
    |   +-- scripts/validate.py         (frontmatter linter)
    |   +-- scripts/cite.py             (CBETA lookup)
    |   +-- scripts/query.py            (offline semantic search)
    |   +-- scripts/test-fidelity.py    (fidelity runner)
    |   +-- scripts/validate-fidelity.py
    |   +-- bin/cli.mjs                 (NPX installer)
    |
    +-- Custom generation (/create-master, HARD-GATE enforced)
          +-- Step 1-2  prompts/intake.md → tools/sutra_collector.py
          |             └─> FoJin API (KG + semantic search + text)
          +-- Step 3    prompts/{sutra,voice}_analyzer.md → two-stage analysis
          +-- Step 3.5  two-stage independent review ──┬─ prompts/doctrine_reviewer.md
          |                                            └─ prompts/voice_reviewer.md
          +-- Step 4-5  tools/master_builder.py → tools/skill_writer.py
                        └─> tools/verify_sources.py (final pre-write check)

Unified multi-platform manifests:
  .claude-plugin/      → Claude Code    (hooks/run-hook.cmd → session-start)
  .cursor-plugin/      → Cursor         (hooks/hooks-cursor.json)
  .codex/              → Codex CLI      (.codex/INSTALL.md)
  .opencode/           → OpenCode       (referenced from opencode.json)
  gemini-extension.json → Gemini CLI    (auto-loaded with GEMINI.md)
```

---
