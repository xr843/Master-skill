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
        "compare",
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
    master_dir = _write_fixture(tmp_path, "compare", cases)

    errors = validate_fidelity.validate_master(master_dir)

    assert errors == []
