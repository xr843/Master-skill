"""A persona whose host cannot run curl must answer offline, not print the call.

2026-09-26 persona run: master-huineng #9 was two unexecuted `curl` calls to
FoJin and master-yinguang #3 leaked tool-call markup — the whole reply, no
answer. The skills said what to do when curl fails or times out; not what to
do when there is nothing to run it with, which is the case in any host
without a shell or HTTP tool.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUSE = "绝不把 `curl` 命令或工具调用写进回答正文"


def test_every_persona_with_live_retrieval_says_what_to_do_without_tools():
    live = [
        path for path in sorted((ROOT / "prebuilt").glob("master-*/SKILL.md"))
        if "FoJin 实时检索" in path.read_text(encoding="utf-8")
    ]
    assert len(live) == 15, [p.parent.name for p in live]
    missing = [p.parent.name for p in live if CLAUSE not in p.read_text(encoding="utf-8")]
    assert not missing, missing


def test_the_generator_prompt_carries_it_to_new_personas():
    text = (ROOT / "prompts" / "rag_instructions.md").read_text(encoding="utf-8")
    assert "绝不把命令或工具调用写进回答正文" in text
