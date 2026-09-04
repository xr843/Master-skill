"""Behaviour tests for the gate-liveness meta-check.

Three of this repo's shipped defects were the same shape: a gate examined an
empty set and reported success.

  - `pytest.ini` listed `testpaths = tests` while CI passed `scripts/tests/`,
    so neither suite ever ran the other's cases (v0.10.1).
  - `tests/test_voice_rules.py` globbed `prebuilt/<slug>/voice.md` when
    voice.md lives under `references/`. The empty glob left every case
    parametrized over an empty set: nothing asserted, green (v0.10.1).
  - The fidelity smoke — a branch-protection-required check — writes
    `{"skipped": true, "reason": "no_api_key"}` and exits 0 when the secret is
    absent, which it always has been.

None of those is a wrong assertion. Each is an assertion that never ran. This
check exists to make "I examined nothing" fail loudly instead of passing
quietly.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def liveness():
    scripts_dir = Path(__file__).resolve().parents[1]
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location(
        "check_gate_liveness", scripts_dir / "check-gate-liveness.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_gate_liveness"] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# Every test file must contribute at least one collected test.
# This is the voice_rules bug: the file exists, pytest imports it fine, and it
# yields nothing because the set it parametrizes over came back empty.
# --------------------------------------------------------------------------


def test_file_collecting_zero_tests_is_a_problem(liveness):
    problems = liveness.check_every_test_file_collects(
        test_files=["tests/test_voice_rules.py", "tests/test_cli.py"],
        collected_counts={"tests/test_voice_rules.py": 0, "tests/test_cli.py": 7},
    )
    assert len(problems) == 1
    assert "test_voice_rules.py" in problems[0]


def test_all_files_collecting_is_clean(liveness):
    problems = liveness.check_every_test_file_collects(
        test_files=["tests/a.py", "tests/b.py"],
        collected_counts={"tests/a.py": 3, "tests/b.py": 1},
    )
    assert problems == []


def test_file_absent_from_collection_entirely_is_a_problem(liveness):
    """Never collected at all is the same failure as collected-zero."""
    problems = liveness.check_every_test_file_collects(
        test_files=["scripts/tests/a.py"], collected_counts={}
    )
    assert len(problems) == 1
    assert "scripts/tests/a.py" in problems[0]


# --------------------------------------------------------------------------
# testpaths must cover every directory that holds tests.
# This is the pytest.ini bug verbatim.
# --------------------------------------------------------------------------


def test_uncovered_test_directory_is_a_problem(liveness):
    problems = liveness.check_testpaths_cover_suites(
        testpaths=["tests"], test_dirs=["tests", "scripts/tests"]
    )
    assert len(problems) == 1
    assert "scripts/tests" in problems[0]


def test_testpaths_covering_everything_is_clean(liveness):
    problems = liveness.check_testpaths_cover_suites(
        testpaths=["tests", "scripts/tests"], test_dirs=["tests", "scripts/tests"]
    )
    assert problems == []


# --------------------------------------------------------------------------
# A graded fidelity suite that graded nothing must not read as a pass.
# --------------------------------------------------------------------------


def test_graded_suite_with_no_graded_cases_is_a_problem(liveness):
    problems = liveness.check_graded_suites_graded_something(
        [{"master": "master-zhiyi", "mode": "graded", "results": []}]
    )
    assert len(problems) == 1
    assert "master-zhiyi" in problems[0]


def test_graded_suite_of_only_api_errors_is_a_problem(liveness):
    """The credit-exhaustion shape: 10 results, none of them a verdict."""
    problems = liveness.check_graded_suites_graded_something(
        [
            {
                "master": "master-xuyun",
                "mode": "graded",
                "results": [{"status": "api_error"}] * 10,
            }
        ]
    )
    assert len(problems) == 1
    assert "master-xuyun" in problems[0]


def test_graded_suite_with_real_verdicts_is_clean(liveness):
    problems = liveness.check_graded_suites_graded_something(
        [
            {
                "master": "master-xuyun",
                "mode": "graded",
                "results": [{"status": "PASS"}, {"status": "FAIL"}],
            }
        ]
    )
    assert problems == []


def test_dry_run_suite_is_not_evidence_for_a_graded_gate(liveness):
    """A dry run is valid elsewhere, but cannot satisfy a graded gate."""
    problems = liveness.check_graded_suites_graded_something(
        [{"master": "master-ouyi", "mode": "dry_run", "results": []}]
    )
    assert len(problems) == 1
    assert "graded nothing" in problems[0]


def _minimal_live_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    tests = root / "tests"
    tests.mkdir(parents=True)
    (tests / "test_live.py").write_text(
        "def test_live():\n    assert True\n", encoding="utf-8"
    )
    (root / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")
    fixtures = root / "prebuilt" / "master-live" / "tests"
    fixtures.mkdir(parents=True)
    (fixtures / "fidelity.jsonl").write_text(
        json.dumps({"q": "live"}) + "\n", encoding="utf-8"
    )
    return root


def _run_liveness_cli(root: Path, result_path: Path) -> subprocess.CompletedProcess[str]:
    script = Path(__file__).resolve().parents[1] / "check-gate-liveness.py"
    return subprocess.run(
        [
            sys.executable,
            str(script),
            "--root",
            str(root),
            "--fidelity-results",
            str(result_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_rejects_fidelity_result_that_graded_nothing(tmp_path: Path):
    root = _minimal_live_repo(tmp_path)
    result_path = tmp_path / "fidelity.json"
    result_path.write_text(
        json.dumps([{"master": "master-live", "mode": "graded", "results": []}]),
        encoding="utf-8",
    )

    result = _run_liveness_cli(root, result_path)

    assert result.returncode == 1
    assert "graded suite produced 0 verdicts" in result.stdout


def test_cli_rejects_empty_fidelity_result_set(tmp_path: Path):
    root = _minimal_live_repo(tmp_path)
    result_path = tmp_path / "fidelity.json"
    result_path.write_text("[]", encoding="utf-8")

    result = _run_liveness_cli(root, result_path)

    assert result.returncode == 1
    assert "contains 0 suites" in result.stdout


def test_cli_accepts_fidelity_result_with_a_real_verdict(tmp_path: Path):
    root = _minimal_live_repo(tmp_path)
    result_path = tmp_path / "fidelity.json"
    result_path.write_text(
        json.dumps(
            [
                {
                    "master": "master-live",
                    "mode": "graded",
                    "results": [{"status": "PASS"}],
                }
            ]
        ),
        encoding="utf-8",
    )

    result = _run_liveness_cli(root, result_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "fidelity result set produced a real verdict" in result.stdout


def test_load_fidelity_suites_accepts_committed_report_wrapper(liveness, tmp_path: Path):
    suites = [{"master": "master-live", "results": [{"status": "PASS"}]}]
    result_path = tmp_path / "report.json"
    result_path.write_text(json.dumps({"meta": {}, "suites": suites}), encoding="utf-8")

    assert liveness.load_fidelity_suites(result_path) == suites


# --------------------------------------------------------------------------
# Discovery drift: the catalog and the filesystem must agree.
# --------------------------------------------------------------------------


def test_catalog_entry_without_a_directory_is_a_problem(liveness, tmp_path):
    prebuilt = tmp_path / "prebuilt"
    (prebuilt / "master-huineng").mkdir(parents=True)
    catalog = {
        "skills": [
            {"name": "master-huineng", "source": "prebuilt/master-huineng"},
            {"name": "master-ghost", "source": "prebuilt/master-ghost"},
        ]
    }
    problems = liveness.check_catalog_matches_filesystem(catalog, prebuilt, tmp_path)
    assert any("master-ghost" in p for p in problems)


def test_directory_missing_from_catalog_is_a_problem(liveness, tmp_path):
    prebuilt = tmp_path / "prebuilt"
    (prebuilt / "master-huineng").mkdir(parents=True)
    (prebuilt / "master-orphan").mkdir(parents=True)
    catalog = {"skills": [{"name": "master-huineng", "source": "prebuilt/master-huineng"}]}
    problems = liveness.check_catalog_matches_filesystem(catalog, prebuilt, tmp_path)
    assert any("master-orphan" in p for p in problems)


def test_catalog_agreeing_with_filesystem_is_clean(liveness, tmp_path):
    prebuilt = tmp_path / "prebuilt"
    for slug in ("master-huineng", "compare-masters"):
        (prebuilt / slug).mkdir(parents=True)
    catalog = {
        "skills": [
            {"name": "master-huineng", "source": "prebuilt/master-huineng"},
            {"name": "compare-masters", "source": "prebuilt/compare-masters"},
        ]
    }
    problems = liveness.check_catalog_matches_filesystem(catalog, prebuilt, tmp_path)
    assert problems == []


def test_empty_catalog_is_a_problem_not_a_vacuous_pass(liveness, tmp_path):
    """The whole point: examining nothing must never read as success."""
    prebuilt = tmp_path / "prebuilt"
    prebuilt.mkdir(parents=True)
    problems = liveness.check_catalog_matches_filesystem({"skills": []}, prebuilt, tmp_path)
    assert len(problems) >= 1
    assert any("empty" in p.lower() or "no skills" in p.lower() for p in problems)


# --------------------------------------------------------------------------
# Fixtures must exist and be non-empty, per skill.
# --------------------------------------------------------------------------


def test_empty_fixture_file_is_a_problem(liveness, tmp_path):
    prebuilt = tmp_path / "prebuilt"
    good = prebuilt / "master-a" / "tests"
    good.mkdir(parents=True)
    (good / "fidelity.jsonl").write_text(json.dumps({"q": "x"}) + "\n", encoding="utf-8")
    empty = prebuilt / "master-b" / "tests"
    empty.mkdir(parents=True)
    (empty / "fidelity.jsonl").write_text("", encoding="utf-8")

    problems = liveness.check_every_skill_has_fixtures(prebuilt)
    assert len(problems) == 1
    assert "master-b" in problems[0]


def test_missing_fixture_file_is_a_problem(liveness, tmp_path):
    prebuilt = tmp_path / "prebuilt"
    (prebuilt / "master-c").mkdir(parents=True)
    problems = liveness.check_every_skill_has_fixtures(prebuilt)
    assert len(problems) == 1
    assert "master-c" in problems[0]


# --------------------------------------------------------------------------
# The real repo must pass its own check.
# --------------------------------------------------------------------------


def test_this_repo_passes_the_liveness_check(liveness):
    root = Path(__file__).resolve().parents[2]
    problems = liveness.run_all(root)
    assert problems == [], "gate liveness problems: " + "; ".join(problems)
