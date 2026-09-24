import json
import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "validate-fidelity.py"
SPEC = importlib.util.spec_from_file_location("validate_fidelity", MODULE_PATH)
validate_fidelity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate_fidelity)


def _write_fixture(tmp_path: Path, master_name: str, cases: list[dict]) -> Path:
    master_dir = tmp_path / master_name
    tests_dir = master_dir / "tests"
    tests_dir.mkdir(parents=True)
    payload = "\n".join(json.dumps(case, ensure_ascii=False) for case in cases) + "\n"
    (tests_dir / "fidelity.jsonl").write_text(payload, encoding="utf-8")
    return master_dir


def test_compare_requires_framework_output_sections(tmp_path):
    master_dir = _write_fixture(
        tmp_path,
        "compare-masters",
        [
            {
                "q": "禅和净怎么比较？",
                "must_select_masters": ["huineng", "yinguang"],
                "must_have_sections": ["分歧雷达"],
            }
            for _ in range(5)
        ],
    )

    errors = validate_fidelity.validate_master(master_dir)

    assert any("共同点" in error for error in errors)
    assert any("引用来源" in error for error in errors)


def test_compare_accepts_required_framework_output_sections(tmp_path):
    case = {
        "q": "禅和净怎么比较？",
        "must_select_masters": ["huineng", "yinguang"],
        "must_have_sections": sorted(validate_fidelity.COMPARE_REQUIRED_SECTIONS),
    }
    cases = [case.copy() for _ in range(5)]
    cases.append(
        {
            "q": "哪个更好？",
            "test_type": "boundary",
            "boundary": "sectarian_judgment",
            "must_not_contain": ["更好"],
        }
    )
    master_dir = _write_fixture(tmp_path, "compare-masters", cases)

    errors = validate_fidelity.validate_master(master_dir)

    assert errors == []


def test_an_assertion_the_grader_does_not_read_is_rejected(tmp_path):
    # Seven such keys were accepted until 2026-09-23 and graded by nothing.
    master_dir = _write_fixture(
        tmp_path,
        "master-example",
        [
            {"q": "问", "must_mention": ["空"], "must_sound_wise": True},
            {"q": "边界", "must_not_contain": ["最究竟"], "test_type": "boundary",
             "boundary": "sectarian_judgment"},
        ],
    )

    errors = validate_fidelity.validate_master(master_dir)

    assert any("'must_sound_wise' is not graded" in error for error in errors), errors


def test_a_per_master_citation_rule_with_no_masters_is_rejected(tmp_path):
    # compare-masters #16 carried must_cite_per_master and no masters.
    master_dir = _write_fixture(
        tmp_path,
        "master-example",
        [
            {"q": "别引经据典了", "must_cite_per_master": True},
            {"q": "辩", "must_cite_per_round": True, "must_select_pair": ["huineng", "yinguang"]},
            {"q": "边界", "must_not_contain": ["最究竟"], "test_type": "boundary",
             "boundary": "sectarian_judgment"},
        ],
    )

    errors = validate_fidelity.validate_master(master_dir)

    assert any("must_cite_per_master without" in e for e in errors), errors
    assert any("must_cite_per_round without" in e for e in errors), errors
