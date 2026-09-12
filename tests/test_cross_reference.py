"""Tests for cross_reference.py — the teacher slug is external input.

`--teachers xuanzang,kumarajiva` is split on commas and each piece is joined
onto `prebuilt/`. Every other entry point in this repo already restricted that
to a slug charset — `_SAFE_MASTER` in scripts/verify_citations.py and
scripts/query.py, `isSafeName` in bin/cli.mjs — and this one did not, so
`--teachers ../../../../etc` read a meta.json from anywhere on the machine.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import cross_reference

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(
    "slug",
    [
        "../outside",
        "../../etc",
        "../../../../../tmp/x",
        "master-huineng/../../../tmp",
        "/etc",
        "master huineng",      # space
        "master;rm -rf /",     # shell metacharacters
        "",
    ],
)
def test_a_slug_outside_the_charset_is_refused(slug):
    with pytest.raises(ValueError):
        cross_reference.load_teacher_meta(slug)


def test_a_traversing_slug_cannot_read_outside_prebuilt(tmp_path):
    """The concrete failure, not just the charset rule."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "meta.json").write_text(
        json.dumps({"name": "outside the repo"}), encoding="utf-8"
    )
    import os

    escape = os.path.relpath(outside, cross_reference.PREBUILT_DIR)
    with pytest.raises(ValueError):
        cross_reference.load_teacher_meta(escape)


def test_a_real_teacher_still_loads():
    """Don't fix it into uselessness."""
    meta = cross_reference.load_teacher_meta("master-huineng")
    assert meta["name"]


def test_a_missing_but_well_formed_slug_raises_file_not_found():
    """Distinct from the charset refusal: `cmd_concept` catches this one to
    report '未找到' per teacher, and must keep being able to."""
    with pytest.raises(FileNotFoundError):
        cross_reference.load_teacher_meta("master-does-not-exist")


def test_the_cli_reports_a_bad_slug_and_exits_two():
    """Matches scripts/query.py: a message a person can act on, not a traceback."""
    result = subprocess.run(
        [sys.executable, "tools/cross_reference.py", "concept", "空性",
         "--teachers", "../../etc"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert "invalid teacher slug" in result.stderr


def test_list_needs_no_network():
    """`list` reads prebuilt/ only, and returns before create_bridge().

    Checked because the opposite would make an offline user unable to see what
    is installed — and because a misconfigured FOJIN_URL now raises.
    """
    result = subprocess.run(
        [sys.executable, "tools/cross_reference.py", "list"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
        env={**__import__("os").environ, "FOJIN_URL": "http://not-allowed.example.com"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "master-huineng" in result.stdout
