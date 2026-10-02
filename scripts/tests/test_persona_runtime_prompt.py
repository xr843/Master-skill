import importlib
import json
import sys
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.mark.parametrize("broken_prompt", [False, True])
def test_real_promptfoo_loads_all_personas_without_paid_models(tmp_path, broken_prompt):
    cli = shutil.which("promptfoo")
    if not cli:
        if os.environ.get("MASTER_SKILL_REQUIRE_PROMPTFOO") == "1":
            pytest.fail("required Promptfoo CLI is missing")
        pytest.skip("Promptfoo CLI integration runs in persona CI")
    provider = tmp_path / "provider.py"
    provider.write_text('''import json
import sys
from pathlib import Path
sys.path.insert(0, %r)
from _skill_context import load_skill_context
ROOT = Path(%r)
def call_api(prompt, options, context):
    messages = json.loads(prompt)
    variables = context["vars"]
    expected = [{"role": "system", "content": load_skill_context(ROOT / "prebuilt" / variables["master"])},
                {"role": "user", "content": variables["question"]}]
    return {"output": "RUNTIME_OK" if messages == expected else "RUNTIME_MISMATCH"}
''' % (str(ROOT / "scripts"), str(ROOT)), encoding="utf-8")
    tests = []
    for path in sorted((ROOT / "tests" / "persona").glob("*.promptfooconfig.yaml")):
        original = yaml.safe_load(path.read_text())
        for case in original["tests"]:
            tests.append({"vars": {**original["defaultTest"]["vars"], **case["vars"]},
                          "assert": [{"type": "equals", "value": "RUNTIME_OK"}]})
    config = tmp_path / "config.yaml"
    prompt = f"file://{ROOT / 'scripts/persona_prompt.py'}:create_prompt"
    if broken_prompt:
        broken = tmp_path / "broken_prompt.py"
        broken.write_text('def create_prompt(context):\n    return [{"role": "user", "content": context["vars"]["question"]}]\n')
        prompt = f"file://{broken}:create_prompt"
        tests = tests[:1]
    config.write_text(yaml.safe_dump({
        "prompts": [prompt],
        "providers": [f"file://{provider}"], "tests": tests,
    }), encoding="utf-8")
    env = {**os.environ, "PROMPTFOO_DISABLE_TELEMETRY": "1",
           "PROMPTFOO_CONFIG_DIR": str(tmp_path / "state"),
           "PROMPTFOO_PYTHON": sys.executable}
    completed = subprocess.run([cli, "eval", "-c", str(config), "--no-cache", "--no-progress-bar"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
    output = completed.stdout + completed.stderr
    if broken_prompt:
        assert completed.returncode != 0 and "RUNTIME_MISMATCH" in output, output[-6000:]
    else:
        assert completed.returncode == 0, output[-6000:]


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
