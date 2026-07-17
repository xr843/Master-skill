"""Behavior tests for deterministic fidelity smoke-target selection."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SELECTOR = ROOT / "scripts" / "select-fidelity-smoke.py"


def _write_meta(prebuilt: Path, slug: str, sources: object) -> None:
    master_dir = prebuilt / slug
    master_dir.mkdir(parents=True)
    (master_dir / "meta.json").write_text(
        json.dumps({"sources": sources}),
        encoding="utf-8",
    )


def _run_selector(
    prebuilt: Path,
    day_of_year: str,
    changed: str | list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(SELECTOR),
        "--prebuilt",
        str(prebuilt),
        "--day-of-year",
        day_of_year,
    ]
    if changed is not None:
        changed_values = [changed] if isinstance(changed, str) else changed
        for candidate in changed_values:
            command.extend(["--changed", candidate])
    return subprocess.run(command, text=True, capture_output=True, check=False)


@pytest.mark.parametrize(
    ("day_of_year", "expected"),
    [("008", "master-gamma"), ("099", "master-alpha"), ("100", "master-beta")],
)
def test_rotation_parses_zero_padded_days_as_decimal(
    tmp_path: Path,
    day_of_year: str,
    expected: str,
):
    prebuilt = tmp_path / "prebuilt"
    _write_meta(prebuilt, "master-gamma", [{"id": "g"}])
    _write_meta(prebuilt, "master-alpha", [{"id": "a"}])
    _write_meta(prebuilt, "master-beta", [{"id": "b"}])

    result = _run_selector(prebuilt, day_of_year)

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{expected}\n"
    assert result.stderr == ""


def test_changed_persona_wins_only_when_in_discovered_roster(tmp_path: Path):
    prebuilt = tmp_path / "prebuilt"
    _write_meta(prebuilt, "master-alpha", [{"id": "a"}])
    _write_meta(prebuilt, "master-beta", [{"id": "b"}])

    selected = _run_selector(prebuilt, "008", "master-beta")
    rotated = _run_selector(prebuilt, "008", "master-not-discovered")

    assert selected.returncode == 0, selected.stderr
    assert selected.stdout == "master-beta\n"
    assert rotated.returncode == 0, rotated.stderr
    assert rotated.stdout == "master-alpha\n"


def test_meta_skill_before_persona_does_not_hide_changed_persona(tmp_path: Path):
    prebuilt = tmp_path / "prebuilt"
    _write_meta(prebuilt, "master-alpha", [{"id": "a"}])
    _write_meta(prebuilt, "master-beta", [{"id": "b"}])

    result = _run_selector(
        prebuilt,
        "008",
        ["compare", "master-beta", "master-alpha"],
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "master-beta\n"


def test_discovery_ignores_meta_skills_and_empty_sources(tmp_path: Path):
    prebuilt = tmp_path / "prebuilt"
    _write_meta(prebuilt, "compare", [{"id": "meta"}])
    _write_meta(prebuilt, "master-empty", [])
    _write_meta(prebuilt, "master-valid", [{"id": "source"}])

    result = _run_selector(prebuilt, "100")

    assert result.returncode == 0, result.stderr
    assert result.stdout == "master-valid\n"


def test_empty_roster_fails_closed(tmp_path: Path):
    prebuilt = tmp_path / "prebuilt"
    _write_meta(prebuilt, "master-empty", [])

    result = _run_selector(prebuilt, "008")

    assert result.returncode != 0
    assert result.stdout == ""
    assert "No persona smoke targets" in result.stderr


def test_invalid_json_after_valid_metadata_fails_without_partial_stdout(tmp_path: Path):
    prebuilt = tmp_path / "prebuilt"
    _write_meta(prebuilt, "master-alpha", [{"id": "a"}])
    invalid_dir = prebuilt / "master-zeta"
    invalid_dir.mkdir(parents=True)
    (invalid_dir / "meta.json").write_text("{not-json", encoding="utf-8")

    result = _run_selector(prebuilt, "008")

    assert result.returncode != 0
    assert result.stdout == ""
    assert "master-zeta/meta.json" in result.stderr


@pytest.mark.parametrize("day_of_year", ["0", "367", "not-a-day"])
def test_invalid_day_fails_closed(tmp_path: Path, day_of_year: str):
    prebuilt = tmp_path / "prebuilt"
    _write_meta(prebuilt, "master-alpha", [{"id": "a"}])

    result = _run_selector(prebuilt, day_of_year)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "day-of-year" in result.stderr
