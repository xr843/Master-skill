# RAW / SPE / CUS persona evaluation

All 15 prebuilt personas have a configuration covering instruction/boundary
following (RAW), school-specific knowledge (SPE), voice/style (CUS), and a citation
case. These are configurations, not a claim that a new paid sweep has passed.

Each config calls `scripts/persona_prompt.py:create_prompt`, which uses the same
`load_skill_context` as `test-fidelity.py`: actual SKILL.md, references and source
excerpts become the system message; the fixture question is a separate user
message. No miniature persona prompt is maintained. The original three personas'
curated rubrics are retained. The additional personas' rubrics need calibration
against real answers before promotion to hard gates.

```bash
python3 scripts/validate-promptfoo-configs.py
# Requires Python 3.10+ and a paid provider key for actual model evaluation:
promptfoo eval -c tests/persona/huineng.promptfooconfig.yaml
```

The validator checks all-persona coverage, RAW/SPE/CUS, a marked citation case,
the exact runtime loader, matching persona slug, substantive rubrics and curated
contains-any anchors. A test may not override its persona. Configuration validation
is free; model/judge evaluation is advisory. No paid calls are made by validation.
The Python dynamic prompt mechanism is documented by
[Promptfoo](https://www.promptfoo.dev/docs/integrations/python/).

Automatic keyed CI keeps the original three representative personas; all 15
configs are validated on every run. A paid all-persona sweep requires a manual
workflow dispatch with `full_suite=true`, after reviewing its budget. Expanding
configuration coverage does not automatically expand paid CI scope.
