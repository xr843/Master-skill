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
    are CI/eval machinery and belong in requirements-eval.txt and
    requirements-dev.txt respectively.
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
    """A bare `pip install anthropic` (or pytest) anywhere undoes the pin."""
    workflows = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    offenders = [
        f"{path.name}:{n}"
        for path in sorted(workflows.glob("*.yml"))
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if "pip install" in line
        and (
            (("anthropic" in line or "openai" in line) and "requirements-eval.txt" not in line)
            or ("pytest" in line and "requirements-dev.txt" not in line)
        )
    ]
    assert offenders == [], offenders


def test_pytest_lives_in_the_dev_requirements_not_the_eval_ones():
    """Offline jobs need pytest and not the model SDKs; the split lets them say so.

    persona-fidelity.yml's schema stage runs pytest and nothing that imports
    anthropic / openai, yet installed both because pytest was only reachable
    through requirements-eval.txt.
    """
    root = Path(__file__).resolve().parents[1]
    dev = (root / "requirements-dev.txt").read_text(encoding="utf-8")
    eval_reqs = (root / "requirements-eval.txt").read_text(encoding="utf-8")
    pins = lambda text: [  # noqa: E731
        line.split(";")[0].strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert any(p.startswith("pytest>=9.1.1") for p in pins(dev)), pins(dev)
    assert not any(p.startswith("pytest") for p in pins(eval_reqs))
    assert not any(p.startswith(("anthropic", "openai")) for p in pins(dev))


def test_every_job_that_runs_pytest_installs_the_dev_requirements():
    """A job that collects the test suite without pytest installed fails at run
    time, not at install — and check-gate-liveness.py collects it too, so every
    job that runs that script needs requirements-dev.txt as well."""
    import yaml

    workflows = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    missing = []
    for path in sorted(workflows.glob("*.yml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for job_id, job in (doc.get("jobs") or {}).items():
            runs = " ".join(str(s.get("run", "")) for s in job.get("steps") or [])
            needs_pytest = (
                "pytest" in runs
                or "check-gate-liveness.py" in runs
                or "npm test" in runs
                or "--only content" in runs
                or "--only python-tests" in runs
            )
            if needs_pytest and "requirements-dev.txt" not in runs:
                missing.append(f"{path.name}:{job_id}")
    assert missing == [], missing


def test_the_eval_sdk_pins_record_why_their_version_was_chosen():
    """A pin comment that cites a version the file no longer holds is worse
    than no comment: it reads as verification of something never checked.

    This bit once already — the openai comment claimed 3.x was where
    `max_tokens` gives way to `max_completion_tokens`, which is not what 3.8.0
    does, and the anthropic comment kept vouching for 0.122.0 after the pin
    moved. Both were guesses left standing next to a pinned number.
    """
    import re

    text = (Path(__file__).resolve().parents[1] / "requirements-eval.txt").read_text(
        encoding="utf-8"
    )
    pinned = dict(re.findall(r"^([a-z-]+)==([\d.]+)$", text, re.M))
    assert {"anthropic", "openai"} <= set(pinned), pinned

    for package, version in pinned.items():
        # The version must appear in prose above the pin, not only in the pin.
        prose = text.split(f"{package}=={version}")[0]
        assert version in prose, (
            f"{package}=={version} is pinned but no comment says why that "
            "version — the reasoning has to move with the number"
        )


def test_the_python_floor_for_the_eval_is_documented_where_it_bites():
    """anthropic 1.x and openai 3.x both require >= 3.10, while the project
    badge says 3.9+. The badge is about the generator tools; this file is not,
    and a contributor following CONTRIBUTING must not discover the difference
    from a traceback."""
    root = Path(__file__).resolve().parents[1]
    contributing = (root / "CONTRIBUTING.md").read_text(encoding="utf-8")
    section = contributing[: contributing.index("§ 1")]
    assert "requirements-eval.txt" in section
    assert "3.10" in section, "the eval's Python floor is not stated where it is installed"
