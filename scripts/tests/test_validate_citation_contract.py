"""Tests for the cross-tradition citation contract validator."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def validator():
    script_path = Path(__file__).resolve().parents[1] / "validate-citation-contract.py"
    spec = importlib.util.spec_from_file_location("validate_citation_contract", script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_citation_contract"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fake_tree(tmp_path: Path) -> Path:
    return tmp_path / "prebuilt"


def contract(*types: str) -> dict:
    return {
        "version": 1,
        "claim_policy": "declared_sources_only",
        "required_for": [
            "doctrinal_claim",
            "practice_guidance",
            "text_interpretation",
        ],
        "allowed_source_types": sorted(types),
        "minimum_claim_coverage": 0.9,
        "live_retrieval_allowed": True,
    }


def write_meta(
    prebuilt: Path,
    slug: str,
    source_types: list[str],
    value: dict | None,
    *,
    kind: str | None = None,
) -> None:
    directory = prebuilt / f"master-{slug}"
    directory.mkdir(parents=True, exist_ok=True)
    data = {
        "slug": slug,
        "sources": [
            {"type": source_type, "id": f"id-{index}", "title": f"source-{index}"}
            for index, source_type in enumerate(source_types)
        ],
    }
    if kind is not None:
        data["kind"] = kind
    if value is not None:
        data["citation_contract"] = value
    (directory / "meta.json").write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.parametrize(
    "source_types",
    [
        ["cbeta"],
        ["tibetan_canon", "tibetan_treatise"],
        ["compiled_teaching", "pali_canon", "pali_treatise"],
    ],
)
def test_valid_source_family_contracts_pass(validator, fake_tree, source_types):
    write_meta(fake_tree, "demo", source_types, contract(*source_types))
    assert validator.validate(fake_tree) == []


def test_missing_contract_fails(validator, fake_tree):
    write_meta(fake_tree, "demo", ["cbeta"], None)
    errors = validator.validate(fake_tree)
    assert any(
        "master-demo/meta.json" in error and "citation_contract" in error
        for error in errors
    )


@pytest.mark.parametrize("allowed", [[], ["cbeta", "pali_canon"]])
def test_source_type_drift_fails(validator, fake_tree, allowed):
    value = contract("cbeta")
    value["allowed_source_types"] = allowed
    write_meta(fake_tree, "demo", ["cbeta"], value)
    errors = validator.validate(fake_tree)
    assert any(
        "master-demo/meta.json" in error and "allowed_source_types" in error
        for error in errors
    )


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("version", 2),
        ("claim_policy", "any_source"),
        ("required_for", ["doctrinal_claim"]),
        ("minimum_claim_coverage", True),
        ("minimum_claim_coverage", 0.8),
        ("live_retrieval_allowed", "yes"),
    ],
)
def test_fixed_contract_values_are_enforced(
    validator,
    fake_tree,
    field,
    invalid,
):
    value = contract("cbeta")
    value[field] = invalid
    write_meta(fake_tree, "demo", ["cbeta"], value)
    errors = validator.validate(fake_tree)
    assert any(
        "master-demo/meta.json" in error and field in error for error in errors
    )


def test_meta_skill_without_sources_is_ignored(validator, fake_tree):
    write_meta(fake_tree, "debate", [], None, kind="meta-skill")
    assert validator.validate(fake_tree) == []


def test_meta_skill_must_not_declare_persona_contract(validator, fake_tree):
    write_meta(
        fake_tree,
        "debate",
        ["cbeta"],
        contract("cbeta"),
        kind="meta-skill",
    )
    errors = validator.validate(fake_tree)
    assert any(
        "master-debate/meta.json" in error and "meta-skill" in error
        for error in errors
    )


def test_persona_without_sources_is_not_treated_as_meta_skill(validator, fake_tree):
    write_meta(fake_tree, "demo", [], None)
    errors = validator.validate(fake_tree)
    assert any(
        "master-demo/meta.json" in error and "sources" in error for error in errors
    )


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_contract_keys_are_exact(validator, fake_tree, mutation):
    value = contract("cbeta")
    if mutation == "missing":
        del value["claim_policy"]
    else:
        value["unexpected"] = "value"
    write_meta(fake_tree, "demo", ["cbeta"], value)
    errors = validator.validate(fake_tree)
    assert any(
        "master-demo/meta.json" in error and "citation_contract" in error
        for error in errors
    )


@pytest.mark.parametrize("source_type", ["", "   ", None, True])
def test_source_types_must_be_non_empty_strings(
    validator,
    fake_tree,
    source_type,
):
    write_meta(fake_tree, "demo", [source_type], contract("cbeta"))
    errors = validator.validate(fake_tree)
    assert any(
        "master-demo/meta.json" in error and "sources[].type" in error
        for error in errors
    )


def test_cli_exit_codes_and_persona_count(
    validator,
    fake_tree,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(validator, "PREBUILT_DIR", fake_tree)
    monkeypatch.setattr(validator, "EXPECTED_PERSONA_SLUGS", ("demo",))
    write_meta(fake_tree, "demo", ["cbeta"], None)

    assert validator.main() == 1
    assert "master-demo/meta.json" in capsys.readouterr().err

    write_meta(fake_tree, "demo", ["cbeta"], contract("cbeta"))
    assert validator.main() == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.strip() == "citation contracts OK (1 personas)"


def test_repository_mode_fails_when_prebuilt_directory_is_missing(
    validator,
    tmp_path,
):
    errors = validator.validate_repository(tmp_path / "missing")
    assert any("prebuilt directory" in error for error in errors)


def test_repository_mode_fails_with_zero_personas(validator, fake_tree):
    write_meta(fake_tree, "debate", [], None, kind="meta-skill")
    errors = validator.validate_repository(fake_tree)
    assert any("persona roster" in error and "missing" in error for error in errors)


def test_repository_mode_fails_with_fourteen_personas(validator, fake_tree):
    for slug in validator.EXPECTED_PERSONA_SLUGS[:-1]:
        write_meta(fake_tree, slug, ["cbeta"], contract("cbeta"))

    errors = validator.validate_repository(fake_tree)
    missing = validator.EXPECTED_PERSONA_SLUGS[-1]
    assert any(
        "persona roster" in error and f"master-{missing}" in error
        for error in errors
    )


def test_repository_mode_accepts_the_real_fifteen_persona_roster(validator):
    repository = Path(__file__).resolve().parents[2]
    assert validator.validate_repository(repository / "prebuilt") == []


def test_repository_wording_uses_declared_source_contract():
    repository = Path(__file__).resolve().parents[2]
    runtime_paths = [
        repository / "SKILL.md",
        repository / "prebuilt" / "compare" / "SKILL.md",
        repository / "prompts" / "doctrine_reviewer.md",
        repository / "references" / "ethics-runtime.md",
        repository / "references" / "source-conventions.md",
        repository / "docs" / "PRD.md",
        repository / "docs" / "v1-framework-roadmap.md",
        repository / "ETHICS.md",
        repository / "README.md",
        repository / "README_EN.md",
        repository / "CONTRIBUTING.md",
    ]
    forbidden = [
        "NO DOCTRINAL CLAIM WITHOUT CBETA CITATION",
        "每位祖师的回答必须附 CBETA 引用",
        "CBETA 经证覆盖率 ≥ 90%",
        "primary_cbeta_ids 过滤结果",
        "当前版本仅汉传",
        "无 CBETA 经号的教义断言不得写入",
        "每一条教义断言必须附一个**真实**的 CBETA 经号",
    ]
    for path in runtime_paths:
        content = path.read_text(encoding="utf-8")
        for phrase in forbidden:
            assert phrase not in content, (
                f"{path}: stale source-family rule: {phrase}"
            )

    root_text = runtime_paths[0].read_text(encoding="utf-8")
    compare_text = runtime_paths[1].read_text(encoding="utf-8")
    reviewer_text = runtime_paths[2].read_text(encoding="utf-8")
    conventions_text = runtime_paths[4].read_text(encoding="utf-8")

    for text in (root_text, compare_text):
        assert "NO DOCTRINAL CLAIM WITHOUT A DECLARED SOURCE CITATION" in text
        assert "citation_contract.allowed_source_types" in text
        assert "meta.json.sources[]" in text
        assert "live_retrieval_allowed" in text

    assert "primary_cbeta_ids" not in compare_text
    assert "minimum_claim_coverage" in reviewer_text
    assert "同等适用 citation contract" in conventions_text
    contributing_text = runtime_paths[-1].read_text(encoding="utf-8")
    assert "validate-citation-contract.py" in contributing_text
    assert '"citation_contract"' in contributing_text
    assert "meta.json.sources[]" in contributing_text
    for source_family in (
        "CBETA",
        "BDRC / Toh",
        "PTS / SuttaCentral",
        "compiled teachings",
    ):
        assert source_family in conventions_text


def test_non_cbeta_runtime_instructions_are_source_family_aware():
    repository = Path(__file__).resolve().parents[2]
    slugs = (
        "atisha",
        "tsongkhapa",
        "milarepa",
        "buddhaghosa",
        "mahasi-sayadaw",
        "ajahn-chah",
    )
    for slug in slugs:
        persona = repository / "prebuilt" / f"master-{slug}"
        meta = json.loads((persona / "meta.json").read_text(encoding="utf-8"))
        assert "cbeta" not in meta["citation_contract"]["allowed_source_types"]
        instructions = (persona / "SKILL.md").read_text(encoding="utf-8")
        for stale in ("cbeta_id", "--sources cbeta", "以 CBETA 汉文为主"):
            assert stale not in instructions, f"master-{slug}: stale {stale}"
        for required in (
            "source_type",
            "source_id",
            "meta.json.sources[]",
            "citation_contract.allowed_source_types",
        ):
            assert required in instructions, f"master-{slug}: missing {required}"

    rag = (repository / "prompts" / "rag_instructions.md").read_text(
        encoding="utf-8"
    )
    assert "--sources cbeta" not in rag
    for required in (
        "source_type",
        "source_id",
        "meta.json.sources[]",
        "citation_contract.allowed_source_types",
    ):
        assert required in rag


def test_live_retrieval_never_uses_sources_outside_the_declared_contract():
    repository = Path(__file__).resolve().parents[2]
    persona_skills = []
    for path in sorted((repository / "prebuilt").glob("master-*/SKILL.md")):
        meta_path = path.parent / "meta.json"
        if not meta_path.is_file():
            continue
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        if isinstance(metadata.get("sources"), list) and metadata["sources"]:
            persona_skills.append(path)
    assert len(persona_skills) == 15
    for path in persona_skills:
        content = path.read_text(encoding="utf-8")
        for stale in (
            "声明经典之外",
            "所列经典之外",
            "三部经之外",
            "上述三部经之外",
        ):
            assert stale not in content, f"{path}: contradictory live trigger {stale}"
        assert "先人工扩充 `sources[]` / citation contract" in content
        assert "已声明来源" in content


def test_create_master_docs_match_the_real_generator_cli():
    repository = Path(__file__).resolve().parents[2]
    root = (repository / "SKILL.md").read_text(encoding="utf-8")
    workflow = (repository / "references" / "workflow-details.md").read_text(
        encoding="utf-8"
    )
    combined = root + workflow
    assert "sutra_collector.py --name" in combined
    assert "--output collected_data.json" in combined
    assert "verify_sources.py --check-links collected_data.json" in combined
    assert "master_builder.py --spec generated-master.json" in combined
    assert "verify_sources.py --final-check" in combined
    assert "生成器内存" in root
    assert "master_builder.py --name" not in combined


def test_create_master_prompts_and_contribution_paths_are_source_neutral():
    repository = Path(__file__).resolve().parents[2]
    source_prompts = [
        repository / "prompts" / "sutra_analyzer.md",
        repository / "prompts" / "teaching_builder.md",
        repository / "prompts" / "voice_builder.md",
    ]
    for path in source_prompts:
        content = path.read_text(encoding="utf-8")
        for stale in (
            "`cbeta_id`",
            "`fojin_url`",
            "所有经文引用必须附 FoJin 链接",
            "https://fojin.app/texts/{text_id}",
        ):
            assert stale not in content, f"{path}: stale {stale}"
        assert "source_id" in content, f"{path}: missing source_id"

    intake = (repository / "prompts" / "intake.md").read_text(encoding="utf-8")
    for tradition in ("印度", "汉传", "藏传", "南传"):
        assert tradition in intake
    assert "当前版本仅汉传" not in intake

    pull_request = (
        repository / ".github" / "PULL_REQUEST_TEMPLATE.md"
    ).read_text(encoding="utf-8")
    issue = (
        repository / ".github" / "ISSUE_TEMPLATE" / "new_master.yml"
    ).read_text(encoding="utf-8")
    for content in (pull_request, issue):
        assert "声明来源" in content
    assert "validate-citation-contract.py" in pull_request
