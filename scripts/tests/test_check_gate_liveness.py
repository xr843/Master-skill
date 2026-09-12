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
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def liveness():
    """Session-scoped on purpose.

    The module holds no mutable state a test would want fresh — the one thing
    tests do mutate, ADVISORY_GATES, they mutate through `monkeypatch.setitem`,
    which restores it. Reloading it per test also reset the `lru_cache` on the
    collection subprocess, so six tests each forked a full
    `pytest --collect-only` of the entire suite: 1.11s apiece, and growing with
    every test added to the project.
    """
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


def test_dry_run_suite_is_exempt(liveness):
    """A dry run grades nothing by design — that is not the failure mode."""
    problems = liveness.check_graded_suites_graded_something(
        [{"master": "master-ouyi", "mode": "dry_run", "results": []}]
    )
    assert problems == []


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


# --------------------------------------------------------------------------
# Advisory gates must be declared, and declarations must not outlive the job.
#
# The repo shipped a *required* branch-protection check — "Fidelity smoke" —
# that exits 0 whenever ANTHROPIC_API_KEY is unset, which it always has been.
# Nothing was wrong with the check; it just never graded anything, and a green
# tick looks identical either way. These assert the skip has to be declared.
# --------------------------------------------------------------------------


def _wf(job_id, *, name=None, run='if [ -z "${SOME_KEY:-}" ]; then exit 0; fi'):
    job = {"steps": [{"run": run}]}
    if name:
        job["name"] = name
    return {".github/workflows/x.yml": {"jobs": {job_id: job}}}


def test_undeclared_silent_skip_is_a_problem(liveness):
    problems = liveness.check_advisory_gates_declared(_wf("g", name="Undeclared Gate"))
    assert len(problems) == 1
    assert "Undeclared Gate" in problems[0]


def test_declared_advisory_gate_is_clean(liveness, monkeypatch):
    monkeypatch.setitem(liveness.ADVISORY_GATES, "Known Gate", "grades nothing without a key")
    assert liveness.check_advisory_gates_declared(_wf("g", name="Known Gate")) == []


def test_job_without_a_name_key_is_reported_by_its_job_id(liveness):
    """GitHub falls back to the job id — so must the roster, or it can't match."""
    problems = liveness.check_advisory_gates_declared(_wf("bare-job-id"))
    assert "bare-job-id" in problems[0]


def test_a_silent_job_cannot_hide_behind_a_declared_sibling(liveness, monkeypatch):
    """Per-job, not per-file: validate-and-test.yml holds six jobs.

    A file-level check passes the whole file once any one job is declared,
    which is exactly how a newly-silent seventh job would slip in.
    """
    monkeypatch.setitem(liveness.ADVISORY_GATES, "Declared", "known advisory")
    docs = {
        ".github/workflows/x.yml": {
            "jobs": {
                "a": {"name": "Declared", "steps": [{"run": 'if [ -z "${K:-}" ]; then exit 0; fi'}]},
                "b": {"name": "Sneaky", "steps": [{"run": 'if [ -z "${K:-}" ]; then exit 0; fi'}]},
            }
        }
    }
    problems = liveness.check_advisory_gates_declared(docs)
    assert len(problems) == 1
    assert "Sneaky" in problems[0]


def test_job_with_no_secret_skip_is_not_flagged(liveness):
    """Don't cry wolf: an ordinary job must stay clean."""
    assert liveness.check_advisory_gates_declared(_wf("g", name="Normal", run="pytest -q")) == []


def test_stale_declaration_is_a_problem(liveness, monkeypatch):
    monkeypatch.setitem(liveness.ADVISORY_GATES, "Renamed Away", "caveat")
    problems = liveness.check_declared_gates_still_exist(
        {".github/workflows/x.yml": {"jobs": {"g": {"name": "Current Name", "steps": []}}}}
    )
    assert any("Renamed Away" in p for p in problems)


def test_this_repos_own_advisory_gates_all_still_exist(liveness):
    """The roster is checked against the real workflows, not a fixture.

    If a job is renamed, this fails here rather than silently un-declaring it.
    """
    root = Path(__file__).resolve().parent.parent.parent
    assert liveness.check_declared_gates_still_exist(liveness.read_workflows(root)) == []


def test_this_repos_own_silent_skips_are_all_declared(liveness):
    root = Path(__file__).resolve().parent.parent.parent
    assert liveness.check_advisory_gates_declared(liveness.read_workflows(root)) == []


# --------------------------------------------------------------------------
# The graded-suite check must actually be reachable from run_all().
#
# It shipped fully written and unit-tested but unreferenced — the anti-fake-
# green script had a check that itself never ran.
# --------------------------------------------------------------------------


def test_load_fidelity_suites_ignores_a_declared_skip(liveness, tmp_path):
    report = tmp_path / "r.json"
    report.write_text(json.dumps({"skipped": True, "reason": "no_api_key"}), encoding="utf-8")
    assert liveness.load_fidelity_suites(report) == []


def test_load_fidelity_suites_wraps_a_single_suite_object(liveness, tmp_path):
    report = tmp_path / "r.json"
    report.write_text(json.dumps({"master": "m", "mode": "graded", "results": []}), encoding="utf-8")
    assert len(liveness.load_fidelity_suites(report)) == 1


def test_run_all_flags_a_report_that_graded_nothing(liveness, tmp_path):
    """End-to-end through run_all — the wiring, not just the function."""
    report = tmp_path / "r.json"
    report.write_text(
        json.dumps([{"master": "master-zhiyi", "mode": "graded",
                     "results": [{"status": "api_error"}] * 3}]),
        encoding="utf-8",
    )
    root = Path(__file__).resolve().parent.parent.parent
    problems = liveness.run_all(root, report)
    assert any("graded nothing" in p for p in problems)


def test_run_all_is_clean_on_a_report_with_real_verdicts(liveness, tmp_path):
    report = tmp_path / "r.json"
    report.write_text(
        json.dumps([{"master": "master-zhiyi", "mode": "graded",
                     "results": [{"status": "PASS"}, {"status": "FAIL"}]}]),
        encoding="utf-8",
    )
    root = Path(__file__).resolve().parent.parent.parent
    assert liveness.run_all(root, report) == []


# --------------------------------------------------------------------------
# The --fidelity-report wiring must itself be non-vacuous.
#
# First version: `if fidelity_report is not None and fidelity_report.exists()`.
# A missing path made run_all return [] and the script print "every gate
# examined a non-empty set" about a report it never opened — the exact
# statement it exists to make impossible.
# --------------------------------------------------------------------------


def test_a_named_report_that_does_not_exist_is_a_problem(liveness, tmp_path):
    root = Path(__file__).resolve().parent.parent.parent
    problems = liveness.run_all(root, tmp_path / "never-written.json")
    assert any("does not exist" in p for p in problems)


def test_an_empty_report_that_declares_no_skip_is_a_problem(liveness, tmp_path):
    report = tmp_path / "r.json"
    report.write_text("[]", encoding="utf-8")
    root = Path(__file__).resolve().parent.parent.parent
    problems = liveness.run_all(root, report)
    assert any("no suites" in p for p in problems)


def test_a_report_that_declares_a_skip_is_clean(liveness, tmp_path):
    """The advisory path is accounted for by ADVISORY_GATES, not by this."""
    report = tmp_path / "r.json"
    report.write_text(json.dumps({"skipped": True, "reason": "no_api_key"}), encoding="utf-8")
    root = Path(__file__).resolve().parent.parent.parent
    assert liveness.run_all(root, report) == []


def test_a_matrix_job_name_is_known_to_be_unmatchable(liveness):
    """Documents a real limit rather than pretending it away.

    GitHub expands `name: CodeQL (${{ matrix.language }})` into one check run
    per leg. Statically only the template is visible, so no ADVISORY_GATES key
    can match a matrix job. If a future change makes these resolvable, this
    test fails and the docstring stating the limit should be revisited.
    """
    root = Path(__file__).resolve().parent.parent.parent
    names = {name for _, name, _ in liveness._iter_jobs(liveness.read_workflows(root))}
    templated = {n for n in names if "${{" in n}
    assert templated, "no matrix jobs left — the documented limit may be stale"
    assert not (templated & set(liveness.ADVISORY_GATES)), (
        "an ADVISORY_GATES key looks like a matrix template; it can never match "
        "a real check-run name"
    )


def test_the_collection_subprocess_runs_once_per_process(liveness, monkeypatch, tmp_path):
    """`collect_counts` forks `pytest --collect-only`, which costs ~1.1s.

    It was called afresh by every test that touched `run_all` — six of them —
    and the cost grew with the suite, so adding tests made this file slower in
    a loop. Counted rather than timed: a wall-clock assertion here would be
    flaky on a loaded machine, and what matters is the number of forks.
    """
    calls = []
    real_run = liveness.subprocess.run

    def counting_run(*args, **kwargs):
        calls.append(args[0])
        return real_run(*args, **kwargs)

    monkeypatch.setattr(liveness.subprocess, "run", counting_run)
    liveness._collect_counts_cached.cache_clear()

    # Pointed at a one-file tree, not this repo: collecting the real suite costs
    # ~1.1s and proves nothing extra here. What is under test is the number of
    # forks, and that is the same whatever is being collected.
    tiny = tmp_path / "tree"
    (tiny / "tests").mkdir(parents=True)
    (tiny / "tests" / "test_one.py").write_text("def test_one():\n    assert True\n")

    first = liveness.collect_counts(tiny)
    second = liveness.collect_counts(tiny)

    assert first == second
    assert len(calls) == 1, f"collected {len(calls)} times, expected 1"
    liveness._collect_counts_cached.cache_clear()
