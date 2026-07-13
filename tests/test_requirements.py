"""Compatibility contract for the published generator requirements."""

from pathlib import Path


def test_requests_constraints_preserve_the_documented_python39_floor():
    requirements = (
        Path(__file__).resolve().parents[1] / "requirements.txt"
    ).read_text(encoding="utf-8")
    assert 'requests>=2.32.5,<2.33; python_version < "3.10"' in requirements
    assert 'requests>=2.34.2; python_version >= "3.10"' in requirements
