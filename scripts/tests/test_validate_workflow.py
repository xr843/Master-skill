"""Structural and behavior checks for the repository validation workflow."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "validate-and-test.yml"
WORKFLOW_TEXT = WORKFLOW_PATH.read_text(encoding="utf-8")
VERIFY_LINKS_PATH = ROOT / ".github" / "workflows" / "verify-links.yml"


def _load_workflow_text(text: str) -> dict:
    workflow = yaml.safe_load(text)
    assert isinstance(workflow, dict)
    assert isinstance(workflow.get("jobs"), dict)
    return workflow


def _job(workflow: dict, job_name: str) -> dict:
    job = workflow["jobs"].get(job_name)
    assert isinstance(job, dict), f"missing workflow job: {job_name}"
    assert isinstance(job.get("steps"), list), f"job has no steps: {job_name}"
    return job


def _step(workflow: dict, job_name: str, step_name: str) -> dict:
    matches = [
        step
        for step in _job(workflow, job_name)["steps"]
        if step.get("name") == step_name
    ]
    assert len(matches) == 1, f"expected one {job_name}/{step_name} step, got {len(matches)}"
    return matches[0]


def _assert_hard(step: dict) -> None:
    assert step.get("continue-on-error") not in (True, "true")


WORKFLOW = _load_workflow_text(WORKFLOW_TEXT)
VERIFY_LINKS_WORKFLOW = _load_workflow_text(
    VERIFY_LINKS_PATH.read_text(encoding="utf-8")
)


def test_free_text_tokens_cannot_substitute_for_workflow_structure():
    fake = _load_workflow_text(
        """\
name: fake
jobs:
  validate:
    steps:
      - name: comments only
        run: echo 'python -m pytest tests/ scripts/tests/ -v'
"""
    )

    with pytest.raises(AssertionError, match="Run Python tests"):
        _step(fake, "validate", "Run Python tests")


def test_workflow_has_no_softened_steps():
    for job_name, job in WORKFLOW["jobs"].items():
        for step in job.get("steps", []):
            assert step.get("continue-on-error") not in (True, "true"), (
                f"softened workflow step in {job_name}: {step.get('name', step.get('uses'))}"
            )


def _gate_registry():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_run_gates_for_workflow_test", ROOT / "scripts" / "run-gates.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("step_name", "gate_name", "argv"),
    [
        ("Run Python tests", "pytest", ("-m", "pytest", "tests/", "scripts/tests/")),
        (
            "Content gates (validators + gate liveness)",
            "validate-citation-contract",
            ("scripts/validate-citation-contract.py",),
        ),
        (
            "Content gates (validators + gate liveness)",
            "validate-lore-triggers-content",
            ("scripts/validate-lore-triggers-content.py", "--strict"),
        ),
        (
            "Content gates (validators + gate liveness)",
            "validate-promptfoo-configs",
            ("scripts/validate-promptfoo-configs.py",),
        ),
        (
            "Hook tests (session-start sanitization, run-hook via bash + POSIX sh)",
            "test-run-hook",
            ("hooks/tests/test_run_hook.sh",),
        ),
    ],
)
def test_validate_job_contains_hard_gate_commands(step_name: str, gate_name: str, argv):
    """The command lives in scripts/run-gates.py; the step must select its group."""
    registry = _gate_registry()
    gate = next(g for g in registry.GATES if g.name == gate_name)
    assert all(token in gate.argv for token in argv), gate.argv
    assert not gate.expect_failure
    step = _step(WORKFLOW, "validate", step_name)
    assert step.get("run") == f"python scripts/run-gates.py --only {gate.group}"
    _assert_hard(step)


def test_every_validate_step_that_runs_gates_names_a_real_group():
    registry = _gate_registry()
    groups = set(registry.groups())
    runs = [
        step["run"] for step in _job(WORKFLOW, "validate")["steps"]
        if "run-gates.py" in str(step.get("run", ""))
    ]
    assert runs, "the validate job runs no gates from the registry"
    for run in runs:
        selected = run.split("--only", 1)[1].split()
        assert set(selected) <= groups, run


def test_paid_eval_workflows_have_no_schedule():
    """A cron with no key configured is a weekly green tick that graded nothing.

    Both workflows ran on a Monday cron, both skipped grading for want of
    ANTHROPIC_API_KEY, and both concluded success. Paid runs are dispatched by a
    person now; this keeps a schedule from quietly coming back.
    """
    for name in ("validate-and-test.yml", "persona-fidelity.yml"):
        doc = yaml.safe_load(
            (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        )
        triggers = doc.get("on") or doc.get(True)
        assert "schedule" not in triggers, f"{name} has a schedule trigger again"
        assert "workflow_dispatch" in triggers, f"{name} lost its manual trigger"


def test_the_manual_full_sweep_fails_without_a_key():
    job = _job(WORKFLOW, "fidelity-full")
    assert job.get("if") == "github.event_name == 'workflow_dispatch'"
    assert job.get("needs") == "validate"
    script = _step(WORKFLOW, "fidelity-full", "Run fidelity tests")["run"]
    import re

    missing = re.split(r"\n\s*fi\b", script.split('if [ -z "${ANTHROPIC_API_KEY:-}" ]; then', 1)[1])[0]
    assert "exit 1" in missing
    assert "exit 0" not in script, "a dispatched paid sweep must not have a pass-without-grading path"
    assert "skipped" not in script


def test_persona_eval_fails_on_dispatch_without_key_and_never_swallows_failures():
    import re

    persona = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "persona-fidelity.yml").read_text(encoding="utf-8")
    )
    steps = {s.get("name"): s for s in persona["jobs"]["fidelity"]["steps"]}
    detect = steps["Detect ANTHROPIC_API_KEY"]["run"]
    missing = detect.split('if [ -z "${ANTHROPIC_API_KEY:-}" ]; then', 1)[1]
    dispatch = missing.split('= "workflow_dispatch"', 1)
    assert len(dispatch) == 2, "a dispatched run must be distinguished from a PR"
    assert "exit 1" in re.split(r"\n\s*fi\b", dispatch[1])[0]
    evaluate = steps["Run llm-rubric eval"]["run"]
    assert "|| true" not in evaluate
    assert "exit 1" in evaluate
    assert steps["Run llm-rubric eval"].get("shell") == "bash"


def test_promptfoo_version_comes_from_a_manifest_dependabot_watches():
    import json
    import re

    text = (ROOT / ".github" / "workflows" / "persona-fidelity.yml").read_text(encoding="utf-8")
    assert not re.search(r"promptfoo@\d", text), (
        "a version written inside a workflow run line is invisible to Dependabot"
    )
    manifest = json.loads(
        (ROOT / ".github" / "promptfoo" / "package.json").read_text(encoding="utf-8")
    )
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["devDependencies"]["promptfoo"])
    assert ".github/promptfoo/package.json" in text
    dependabot = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    assert any(
        u["package-ecosystem"] == "npm" and u["directory"] == "/.github/promptfoo"
        for u in dependabot["updates"]
    )


def test_validate_job_lints_workflows_with_verified_pinned_actionlint():
    step = _step(WORKFLOW, "validate", "Lint GitHub Actions workflows")
    assert step.get("env") == {
        "ACTIONLINT_VERSION": "1.7.12",
        "ACTIONLINT_SHA256": (
            "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8"
        ),
    }
    script = step.get("run", "")
    assert "rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/" in script
    assert "sha256sum --check -" in script
    assert '"$ACTIONLINT_DIR/actionlint" -color' in script
    _assert_hard(step)


def test_verify_links_quotes_github_output_path():
    """每一处写 `$GITHUB_OUTPUT` 都要加引号 —— 断言的是性质，不是条数。

    原来写的是 `count(...) == 2`。加第三个 output 时它就红了，而它本来想守的
    那件事（引号）一点没被破坏 —— 一个数着行数的测试，第一次真正扩展就得改，
    改的人只会把 2 换成 3，于是它连自己守什么都说不清了。
    """
    import re

    step = _step(VERIFY_LINKS_WORKFLOW, "verify", "Run verify_sources.py (dry run)")
    script = step.get("run", "")
    assert 'cd "${{ github.workspace }}"' in script

    writes = re.findall(r">>\s*\S*GITHUB_OUTPUT\S*", script)
    assert writes, "这一步没有写任何 output —— 那下面的 if: 条件永远为假"
    for write in writes:
        assert write.replace(">>", "").strip() == '"$GITHUB_OUTPUT"', write


def test_every_output_the_issue_condition_reads_is_actually_written():
    """`if:` 里引用的每个 output 都必须真的被写过。

    拼错一个名字，GitHub 把它求值成空字符串，`!= '0'` 恒真或恒假 —— 要么每周
    开一个空 issue，要么永远不开。两种都不会报错，也不会有人发现：这道周检的
    全部产出就是「开没开 issue」这一件事。
    """
    import re

    verify = _step(VERIFY_LINKS_WORKFLOW, "verify", "Run verify_sources.py (dry run)")
    written = set(re.findall(r'echo\s+"(\w+)=', verify.get("run", "")))

    read = set()
    for job in VERIFY_LINKS_WORKFLOW["jobs"].values():
        for step in job.get("steps", []):
            blob = str(step.get("if", "")) + str(step.get("with", "")) + str(step.get("run", ""))
            read |= set(re.findall(r"steps\.verify\.outputs\.(\w+)", blob))

    assert read, "没有任何地方读取 outputs —— 这两个断言都会空转"
    missing = read - written
    assert not missing, f"读取了但从未写入的 output: {sorted(missing)}"


def test_every_defect_counter_the_weekly_check_prints_reaches_the_issue():
    """脚本数出来的每一类问题，都必须能让周检开出 issue。

    一个计数要真的有用，得出现在五个地方：脚本打印、workflow 抽取、写进
    outputs、issue 的 `if:` 条件、issue 标题。2026-09-20 加 3j（巴利经号）时只
    做了第一件 —— 检查跑了、问题会打印，然后躺在日志里没人看，与没有这道门禁
    等价。姊妹测试
    `test_every_output_the_issue_condition_reads_is_actually_written` 管的是
    反方向（读了却没写），漏的正是这一向。
    """
    import re
    import sys

    sys.path.insert(0, str(ROOT / "tools"))
    import verify_sources

    verify = _step(VERIFY_LINKS_WORKFLOW, "verify", "Run verify_sources.py (dry run)")
    run = verify.get("run", "")
    issue = [
        step
        for job in VERIFY_LINKS_WORKFLOW["jobs"].values()
        for step in job.get("steps", [])
        if "outputs.failed" in str(step.get("if", ""))
    ]
    assert len(issue) == 1, "找不到那个开 issue 的步骤"
    condition = str(issue[0].get("if", ""))
    script = str(issue[0].get("with", {}).get("script", ""))

    counters = verify_sources.SUMMARY_DEFECT_COUNTERS
    assert len(counters) >= 14, counters
    for name, label in counters:
        assert re.search(rf'grep -oP "{re.escape(label)}:', run), f"workflow 没有抽取 {label!r}"
        assert f'echo "{name}=' in run, f"抽了却没写进 outputs: {name}"
        assert f"steps.verify.outputs.{name} != '0'" in condition, f"不在 issue 条件里: {name}"
        assert f"steps.verify.outputs.{name}" in script, f"issue 标题/正文里没有: {name}"


@pytest.mark.parametrize(
    ("step_name", "command"),
    [
        ("Check desktop formatting", "cargo fmt --manifest-path desktop/Cargo.toml -- --check"),
        (
            "Lint desktop app",
            "cargo clippy --locked --manifest-path desktop/Cargo.toml "
            "--all-targets -- -D warnings",
        ),
        ("Test desktop app", "cargo test --locked --manifest-path desktop/Cargo.toml"),
        ("Build desktop app", "cargo build --locked --manifest-path desktop/Cargo.toml"),
    ],
)
def test_desktop_job_contains_hard_gate_commands(step_name: str, command: str):
    step = _step(WORKFLOW, "desktop-rust", step_name)
    assert step.get("run") == command
    _assert_hard(step)


def test_desktop_quality_gates_run_before_tests_and_build():
    step_names = [step.get("name") for step in _job(WORKFLOW, "desktop-rust")["steps"]]
    assert step_names.index("Check desktop formatting") < step_names.index("Lint desktop app")
    assert step_names.index("Lint desktop app") < step_names.index("Test desktop app")
    assert step_names.index("Test desktop app") < step_names.index("Build desktop app")


def test_desktop_job_type_checks_every_other_release_target():
    """The release matrix builds Windows and macOS; nothing else compiled them.

    v0.12.0 failed to build for Windows while every PR and main check was
    green, and its release attached no desktop binaries. Each target the release
    workflow builds on a non-Linux runner must be type-checked here.
    """
    steps = _job(WORKFLOW, "desktop-rust")["steps"]
    names = [step.get("name") for step in steps]
    assert "Type-check the other release targets" in names
    assert names.index("Type-check the other release targets") > names.index("Build desktop app")
    step = _step(WORKFLOW, "desktop-rust", "Type-check the other release targets")
    run = step.get("run", "")
    for target in ("x86_64-pc-windows-msvc", "aarch64-apple-darwin"):
        assert f"--target {target}" in run, target
        assert target in run.split("\n")[0], f"{target} is checked but never installed"
    _assert_hard(step)


def test_windows_cli_job_installs_the_generator_python_runtime():
    job = _job(WORKFLOW, "cli-windows")
    uses = [step.get("uses", "") for step in job["steps"]]
    assert any(use.startswith("actions/setup-python@") for use in uses)
    install = _step(WORKFLOW, "cli-windows", "Install generator dependencies")
    assert install.get("run") == "python -m pip install -r requirements.txt"
    _assert_hard(install)


def test_python39_job_compiles_and_runs_the_four_generator_cli_steps():
    job = _job(WORKFLOW, "python-compat")
    setup = next(
        step
        for step in job["steps"]
        if str(step.get("uses", "")).startswith("actions/setup-python@")
    )
    assert setup.get("with", {}).get("python-version") == "3.9"
    smoke = _step(WORKFLOW, "python-compat", "Run Python 3.9 generator smoke")
    command = smoke["run"]
    assert "python -m compileall -q tools scripts" in command
    assert "sutra_collector.py" in command
    assert "verify_sources.py --check-links" in command
    assert "master_builder.py" in command
    assert "verify_sources.py --final-check" in command
    _assert_hard(smoke)


def _covered(target: str, patterns: set[str]) -> bool:
    """Whether a push-paths pattern set actually triggers on `target`.

    The contract is "editing this file runs CI", not "this literal string
    appears in the list" — so a broader glob that consolidates several entries
    (docs/PRD.md + docs/v1-framework-roadmap.md -> docs/**) still satisfies it,
    while dropping the coverage entirely still fails.
    """
    if target in patterns:
        return True
    return any(
        target.startswith(pattern[: -len("**")])
        for pattern in patterns
        if pattern.endswith("**")
    )


def test_push_paths_include_distribution_and_generator_runtime():
    triggers = WORKFLOW.get("on", WORKFLOW.get(True))
    assert isinstance(triggers, dict)
    paths = set(triggers["push"]["paths"])
    required = {
        "skill-catalog.json",
        "SKILL.md",
        "references/**",
        "ETHICS.md",
        "requirements.txt",
        "README.md",
        "README_EN.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "docs/PRD.md",
        "docs/v1-framework-roadmap.md",
        "masters/**",
        ".claude-plugin/**",
        ".cursor-plugin/**",
        "gemini-extension.json",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/**",
    }
    uncovered = sorted(t for t in required if not _covered(t, paths))
    assert not uncovered, f"push trigger does not cover: {uncovered}"


def test_pick_step_uses_checked_selector_without_fixed_roster():
    checkout = next(
        step
        for step in _job(WORKFLOW, "fidelity-smoke")["steps"]
        if str(step.get("uses", "")).startswith("actions/checkout@")
    )
    assert checkout.get("with", {}).get("fetch-depth") == 0
    step = _step(WORKFLOW, "fidelity-smoke", "Pick smoke target")
    script = step["run"]
    assert "if ! CHANGED=$(python scripts/select-fidelity-smoke.py" in script
    assert "if ! DIFF_OUTPUT=$(git diff --name-only" in script
    assert "CHANGED_CANDIDATES" in script
    assert "--prebuilt prebuilt" in script
    assert '--day-of-year "$(date +%j)"' in script
    assert "MASTERS=(" not in script
    _assert_hard(step)


def test_smoke_selector_producer_failure_is_not_masked(tmp_path: Path):
    pick_step = _step(WORKFLOW, "fidelity-smoke", "Pick smoke target")
    script = pick_step["run"].replace("${{ github.base_ref || 'main' }}", "main")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_python = bin_dir / "python"
    fake_python.write_text(
        "#!/bin/sh\nprintf 'master-partial\\n'\nexit 7\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    output_path = tmp_path / "github-output"
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["GITHUB_OUTPUT"] = str(output_path)

    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", script],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert not output_path.exists()


def test_smoke_git_diff_failure_is_not_masked(tmp_path: Path):
    pick_step = _step(WORKFLOW, "fidelity-smoke", "Pick smoke target")
    script = pick_step["run"].replace("${{ github.base_ref || 'main' }}", "main")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_git = bin_dir / "git"
    fake_git.write_text("#!/bin/sh\nexit 7\n", encoding="utf-8")
    fake_git.chmod(0o755)
    fake_python = bin_dir / "python"
    fake_python.write_text(
        "#!/bin/sh\nprintf 'master-alpha\\n'\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    output_path = tmp_path / "github-output"
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["GITHUB_OUTPUT"] = str(output_path)

    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", script],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "git diff failed" in result.stdout
    assert not output_path.exists()


@pytest.mark.parametrize(
    ("job_name", "step_name"),
    [
        # fidelity-full has no advisory branch any more: it runs only when
        # dispatched and fails without a key (test_the_manual_full_sweep_fails_without_a_key).
        ("fidelity-smoke", "Run fidelity smoke"),
    ],
)
def test_each_fidelity_no_key_branch_records_step_summary(job_name: str, step_name: str):
    job = _job(WORKFLOW, job_name)
    assert job.get("needs") == "validate"
    step = _step(WORKFLOW, job_name, step_name)
    script = step["run"]
    assert 'if [ -z "${ANTHROPIC_API_KEY:-}" ]; then' in script
    assert script.count('echo "### Fidelity grading skipped') == 1
    assert '} >> "$GITHUB_STEP_SUMMARY"' in script
    # The summary must say the tick graded nothing, not merely that a step was
    # "skipped" — a required check reading green while having graded zero
    # responses is the defect this branch exists to disclose.
    assert "graded nothing" in script
    _assert_hard(step)


@pytest.mark.parametrize(
    ("job_name", "step_name"),
    [
        ("fidelity-smoke", "Run fidelity smoke"),
    ],
)
def test_each_fidelity_no_key_branch_can_be_promoted_to_a_hard_gate(
    job_name: str, step_name: str
):
    """The advisory skip must be one repo variable away from failing.

    Project policy is that CI does not pay for LLM-judge grading, so the key is
    deliberately unset. That is a decision — but it has to be a *revocable* one
    held in a single obvious place, not an emergent property of an `exit 0`.
    """
    step = _step(WORKFLOW, job_name, step_name)
    assert step["env"].get("FIDELITY_GRADING_REQUIRED") == (
        "${{ vars.FIDELITY_GRADING_REQUIRED }}"
    )
    script = step["run"]
    assert '[ "${FIDELITY_GRADING_REQUIRED:-}" = "true" ]' in script
    # …and the promoted branch must actually fail, not warn.
    promoted = script.split('FIDELITY_GRADING_REQUIRED:-}" = "true" ]; then', 1)[1]
    assert "exit 1" in promoted.split("fi", 1)[0]


@pytest.mark.parametrize(
    ("job_name", "step_name", "report"),
    [
        ("fidelity-smoke", "Run fidelity smoke", "fidelity-smoke.json"),
        ("fidelity-full", "Run fidelity tests", "fidelity-results.json"),
    ],
)
def test_each_graded_fidelity_run_is_checked_for_real_verdicts(
    job_name: str, step_name: str, report: str
):
    """A run that reached the API must prove it produced verdicts.

    `eval/reports/0.10.1-c697d5d.json` is the shape this guards: 127 of 211
    calls returned HTTP 400 for an exhausted credit balance, so the suite
    "completed" having graded 84. Without this line a suite where *every* call
    errored exits 0 and reads as a clean pass.
    """
    script = _step(WORKFLOW, job_name, step_name)["run"]
    assert f"check-gate-liveness.py --fidelity-report {report}" in script
    # …and it has to be REACHABLE. `results_failed()` exits 1 on any FAIL /
    # api_error / truncated and this `run:` is `bash -e`, so a plain sequence
    # put the liveness check after a line that had already killed the step.
    # The exit code must be captured and re-raised afterwards.
    assert "set +e" in script, "the grading call must not abort the step"
    liveness_at = script.index("check-gate-liveness.py --fidelity-report")
    assert script.index("FIDELITY_EXIT=$?") < liveness_at
    assert 'exit "$FIDELITY_EXIT"' in script[liveness_at:]
    # `exit` must come LAST. Inserting it before the summary heredoc made that
    # whole block unreachable — the smoke silently stopped reporting
    # "N/M passed" — which shellcheck caught (SC2317) and local runs did not,
    # because actionlint skips its shellcheck integration when shellcheck is
    # not installed.
    assert script.rstrip().endswith('exit "$FIDELITY_EXIT"'), (
        "anything after the exit is dead code"
    )


def test_concurrency_never_lets_one_merge_cancel_another():
    """`cancel-in-progress: false` does not make main runs independent.

    It makes them QUEUE, and GitHub cancels a *pending* run when a newer one
    queues behind it — so a merge landing while a 60-minute sweep (the Monday
    cron then, a manual dispatch now) holds the group could be dropped outright, which is the opposite of what
    the first version of this comment asserted. main gets a per-run group.
    """
    group = WORKFLOW["concurrency"]["group"]
    assert "github.run_id" in group, (
        "main needs a per-run group; a shared non-cancelling group queues "
        "merges behind a long-running sweep and drops the pending one"
    )
    assert "github.head_ref" in group, (
        "keyed on github.ref alone, a PR's push and pull_request events land in "
        "different groups and both run"
    )
    assert WORKFLOW["concurrency"]["cancel-in-progress"] == (
        "${{ github.ref != 'refs/heads/main' }}"
    )


def test_push_validation_is_restricted_to_main():
    """同仓 PR 不得再由分支 push 事件产生检查结果。

    2026-09-07 实测过一次:PR 有冲突,GitHub 构建不出 `refs/pull/N/merge`,
    整类 pull_request workflow 一次都没触发 —— 而分支 push 跑出的绿灯把这
    件事盖住了,`gh pr checks` 照常显示通过,security-scan.yml 从头到尾没跑。

    push 限定 main 之后,那种情况下 PR 的检查是**空的**而不是绿的,分支保护
    会因为 required check 缺席而拦住:缺席看得见,假绿看不见。
    """
    triggers = WORKFLOW.get("on") or WORKFLOW.get(True)
    assert triggers["push"]["branches"] == ["main"]
    # pull_request 必须无过滤器 —— push 的 paths 过滤不该在 PR 上留下盲区。
    assert triggers["pull_request"] is None, (
        "pull_request 带上过滤器就会有既不触发 push 也不触发 pull_request "
        "的改动,那类改动将完全无人检查"
    )


def test_the_eval_sdk_smoke_runs_both_ways_after_the_sdks_are_installed():
    """The keyless SDK smoke must run, must run against the pinned SDKs, and its
    `--break` self-test must be able to fail the job.

    Each clause guards a way it could quietly stop meaning anything: removed
    outright; moved above `pip install`, where it would import whatever the
    runner image happens to carry; or the `--break` case losing its must-fail
    flag, after which a smoke that can no longer detect a broken reply stays
    green. The commands live in scripts/run-gates.py; run-gates' own tests prove
    a must-fail gate that exits 0 fails the run.
    """
    steps = WORKFLOW["jobs"]["validate"]["steps"]
    names = [step.get("name") for step in steps]
    assert "Eval SDK smoke (keyless, local server)" in names
    install = names.index("Install dependencies")
    smoke = names.index("Eval SDK smoke (keyless, local server)")
    assert smoke > install, "the smoke runs before the pinned SDKs are installed"
    assert "requirements-eval.txt" in steps[install]["run"]
    assert steps[smoke]["run"] == "python scripts/run-gates.py --only eval-sdk"

    registry = _gate_registry()
    eval_gates = {g.argv[1:]: g for g in registry.GATES if g.group == "eval-sdk"}
    assert not eval_gates[("scripts/smoke-eval-sdk.py",)].expect_failure
    assert eval_gates[("scripts/smoke-eval-sdk.py", "--break")].expect_failure, (
        "`--break` exiting 0 must fail the job"
    )
    assert ("scripts/check-eval-sdk-surface.py",) in eval_gates


# --------------------------------------------------------------------------
# A pipeline must not hide the failure of everything but its last stage.
#
# GitHub's implicit shell for `run:` on Linux is `bash -e {0}` — no pipefail.
# Writing `shell: bash` is what selects `bash --noprofile --norc -eo pipefail {0}`.
# verify-links.yml ran `python3 tools/verify_sources.py 2>&1 | tee verify_output.txt`
# under the implicit shell, so the pipeline returned tee's 0 however the script
# ended. Every counter downstream falls back to "0" through `|| echo "0"`, the
# issue condition then reads all-clear, and a crashed weekly check is
# indistinguishable from a clean week.
# --------------------------------------------------------------------------


WORKFLOW_DIR = ROOT / ".github" / "workflows"


def _pipes(run: str) -> bool:
    """Whether a run body pipes — `||` is a logical or, not a pipeline."""
    for line in run.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "|" in stripped.replace("||", ""):
            return True
    return False


def _steps_with_shell(path: Path):
    workflow = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    file_default = ((workflow.get("defaults") or {}).get("run") or {}).get("shell")
    for job_id, job in (workflow.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        job_default = ((job.get("defaults") or {}).get("run") or {}).get("shell")
        for step in job.get("steps") or []:
            if isinstance(step, dict) and "run" in step:
                shell = step.get("shell") or job_default or file_default
                yield job_id, step.get("name", job_id), str(step["run"]), shell


def test_every_step_that_pipes_selects_a_shell_with_pipefail():
    offenders = [
        f"{path.name}: {name!r}"
        for path in sorted(WORKFLOW_DIR.glob("*.yml"))
        for _job, name, run, shell in _steps_with_shell(path)
        if _pipes(run) and shell != "bash"
    ]
    assert offenders == [], (
        "these steps pipe under the implicit `bash -e` shell, which has no pipefail, "
        "so a failure in any stage but the last is swallowed: " + "; ".join(offenders)
    )


def test_the_weekly_check_fails_when_the_script_does_not_finish():
    """pipefail catches a crash; the Summary guard catches an early return that exits 0.

    Both halves are needed. Without the first, `| tee` reports success whatever the
    script did. Without the second, a run that stops after printing part of its output
    still satisfies every `grep … || echo "0"` with a zero.
    """
    import re

    steps = dict(
        (name, (run, shell))
        for _job, name, run, shell in _steps_with_shell(VERIFY_LINKS_PATH)
    )
    run, shell = steps["Run verify_sources.py (dry run)"]

    assert shell == "bash", "the step pipes into tee; without pipefail a crash reads as success"
    assert "grep -q '^Summary$' verify_output.txt" in run
    assert re.search(r"if ! grep -q '\^Summary\$' verify_output\.txt; then[\s\S]*?exit 1", run), (
        "a missing Summary block must fail the step, not fall through to counters that read 0"
    )


def test_the_weekly_issue_title_names_whatever_opened_it():
    """An alert whose headline says nothing is wrong is not an alert.

    The title named only `updates` and `failed`, so an issue opened because 19
    excerpt quotations were not in the cited fascicle read "0 URLs, 0 missing" —
    ten of the twelve conditions that can open it were invisible in the issue list,
    which is the only place a maintainer looks first.
    """
    import re

    text = VERIFY_LINKS_PATH.read_text(encoding="utf-8")
    condition = re.search(r"if: (steps\.verify[^\n]+)", text).group(1)
    triggers = set(re.findall(r"steps\.verify\.outputs\.([a-z_]+)", condition))

    counts_block = text.split("const counts = [")[1].split("const title")[0]
    in_title = set(re.findall(r"steps\.verify\.outputs\.([a-z_]+)", counts_block))
    # `updates` and `failed` reach the array through the consts declared above it.
    in_title |= {
        name for name in ("updates", "failed")
        if re.search(rf"\['[^']+', {name}\]", counts_block)
    }

    assert triggers - in_title == set(), (
        "these can open the weekly issue but never appear in its title: "
        + ", ".join(sorted(triggers - in_title))
    )
    assert in_title - triggers == set(), (
        "these are named in the title but cannot open the issue: "
        + ", ".join(sorted(in_title - triggers))
    )
