import importlib
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def test_persona_prompt_loads_actual_skill_and_changes_with_it(tmp_path, monkeypatch):
    module = importlib.import_module("persona_prompt")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    master = tmp_path / "prebuilt" / "master-demo"
    master.mkdir(parents=True)
    (master / "SKILL.md").write_text("Actual persona instruction.\n")
    (master / "references").mkdir()
    (master / "references" / "voice.md").write_text("Actual voice rules.")
    prompt = module.create_prompt({"vars": {"master": "master-demo", "question": "How?"}})
    assert prompt[0]["content"].startswith("Actual persona instruction.")
    assert "Actual voice rules." in prompt[0]["content"]
    assert prompt[1] == {"role": "user", "content": "How?"}
    (master / "SKILL.md").write_text("Changed instruction.\n")
    assert module.create_prompt({"vars": {"master": "master-demo", "question": "How?"}}) != prompt
    with pytest.raises(ValueError):
        module.create_prompt({"vars": {"master": "../../etc", "question": "How?"}})


def test_all_fifteen_configs_use_runtime_prompt_and_citation_cases():
    personas = {p.name for p in (ROOT / "prebuilt").glob("master-*")
                if (p / "meta.json").is_file() and json.loads((p / "meta.json").read_text()).get("signature_phrases")}
    configs = list((ROOT / "tests" / "persona").glob("*.promptfooconfig.yaml"))
    assert {"master-" + p.name.removesuffix(".promptfooconfig.yaml") for p in configs} == personas
    for path in configs:
        cfg = yaml.safe_load(path.read_text())
        assert cfg["prompts"] == ["file://../../scripts/persona_prompt.py:create_prompt"]
        assert cfg["defaultTest"]["vars"]["master"] in personas
        assert any(t.get("metadata", {}).get("citation_case") is True for t in cfg["tests"])
