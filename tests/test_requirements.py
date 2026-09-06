"""Compatibility contract for the published generator requirements."""

from pathlib import Path


def test_requests_constraints_preserve_the_documented_python39_floor():
    requirements = (
        Path(__file__).resolve().parents[1] / "requirements.txt"
    ).read_text(encoding="utf-8")
    assert 'requests>=2.32.5,<2.33; python_version < "3.10"' in requirements
    assert 'requests>=2.34.2; python_version >= "3.10"' in requirements


def test_the_eval_only_dependencies_are_not_in_the_published_requirements():
    """`npx master-skill` users must not pull the paid-eval SDK.

    requirements.txt is what an installer sees; the anthropic SDK and pytest
    are CI/eval machinery and belong in requirements-eval.txt.
    """
    requirements = (
        Path(__file__).resolve().parents[1] / "requirements.txt"
    ).read_text(encoding="utf-8")
    assert "anthropic" not in requirements
    assert "pytest" not in requirements


def test_the_eval_sdk_is_pinned_exactly_not_floored():
    """CI installs these into a job that holds a live ANTHROPIC_API_KEY.

    A floor lets any new release of the SDK land in that process. It also lets
    the grading harness change SDK major versions between runs — anthropic is
    at 1.x on PyPI while every number in eval/reports/ came from the 0.x line.
    """
    eval_requirements = (
        Path(__file__).resolve().parents[1] / "requirements-eval.txt"
    ).read_text(encoding="utf-8")
    pins = [
        line.strip()
        for line in eval_requirements.splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert any(p.startswith("anthropic==") for p in pins), pins


def test_every_workflow_that_installs_the_eval_sdk_uses_the_pinned_file():
    """A bare `pip install anthropic` anywhere undoes the pin."""
    workflows = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    offenders = [
        f"{path.name}:{n}"
        for path in sorted(workflows.glob("*.yml"))
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if "pip install" in line
        and ("anthropic" in line or "pytest" in line)
        and "requirements-eval.txt" not in line
    ]
    assert offenders == [], offenders
