"""Offline CLI contract tests for the installed create-master runtime."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys


TOOLS = Path(__file__).resolve().parents[1] / "tools"
BUNDLE_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_MEMBERS = (
    "SKILL.md",
    "tools",
    "prompts",
    "references",
    "requirements.txt",
    "ETHICS.md",
    "masters",
)


def run_tool(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOLS / name), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def run_installed_tool(
    installed: Path, name: str, *args: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(installed / "tools" / name), *args],
        cwd=installed,
        capture_output=True,
        text=True,
        check=False,
    )


def test_collector_and_builder_expose_real_argparse_help():
    for tool in ("sutra_collector.py", "master_builder.py"):
        result = run_tool(tool, "--help")
        assert result.returncode == 0
        assert "usage:" in result.stdout


def test_shipped_generator_cli_modules_defer_annotations_for_python39():
    for tool in (
        "sutra_collector.py",
        "master_builder.py",
        "verify_sources.py",
    ):
        content = (TOOLS / tool).read_text(encoding="utf-8")
        assert "from __future__ import annotations" in content, tool


def test_collector_offline_smoke_writes_verifiable_source_manifest(tmp_path):
    output = tmp_path / "collected.json"
    result = run_tool(
        "sutra_collector.py",
        "--offline-smoke",
        "--name",
        "Offline Demo",
        "--tradition",
        "南传",
        "--output",
        str(output),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"collected data written: {output}"
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["entity"]["name_zh"] == "Offline Demo"
    assert payload["sources"] == [
        {
            "type": "compiled_teaching",
            "id": "OfflineSmoke:Deterministic",
            "title": "Deterministic offline smoke source",
        }
    ]
    assert payload["citation_contract"]["allowed_source_types"] == [
        "compiled_teaching"
    ]


def test_master_builder_offline_smoke_persists_review_contract(tmp_path):
    output = tmp_path / "masters"
    result = run_tool(
        "master_builder.py",
        "--offline-smoke",
        "--output",
        str(output),
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    meta_path = Path(summary["meta_path"])
    review_path = Path(summary["review_input_path"])
    teacher_dir = Path(summary["teacher_dir"])
    assert meta_path.is_file()
    assert review_path.is_file()
    assert teacher_dir.name.startswith("master-")
    assert f"name: {teacher_dir.name}" in (teacher_dir / "SKILL.md").read_text(
        encoding="utf-8"
    )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert meta["citation_contract"] == review["citation_contract"]
    assert meta["citation_contract"]["allowed_source_types"] == [
        "compiled_teaching"
    ]


def test_exact_installed_bundle_runs_offline_after_source_copy_is_deleted(tmp_path):
    packed_source = tmp_path / "packed-source"
    installed = tmp_path / "installed-create-master"
    packed_source.mkdir()
    for member in BUNDLE_MEMBERS:
        source = BUNDLE_ROOT / member
        destination = packed_source / member
        if source.is_dir():
            shutil.copytree(
                source,
                destination,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        else:
            shutil.copy2(source, destination)

    shutil.copytree(packed_source, installed)
    shutil.rmtree(packed_source)
    assert not packed_source.exists()
    assert {path.name for path in installed.iterdir()} == set(BUNDLE_MEMBERS)

    collected = tmp_path / "collected.json"
    collector = run_installed_tool(
        installed,
        "sutra_collector.py",
        "--offline-smoke",
        "--name",
        "Offline Demo",
        "--tradition",
        "南传",
        "--output",
        str(collected),
    )
    assert collector.returncode == 0, collector.stderr
    assert collector.stdout.strip() == f"collected data written: {collected}"

    initial_check = run_installed_tool(
        installed, "verify_sources.py", "--check-links", str(collected)
    )
    assert initial_check.returncode == 0, initial_check.stderr
    assert initial_check.stdout.strip() == "declared sources OK (1 sources)"

    builder = run_installed_tool(
        installed,
        "master_builder.py",
        "--offline-smoke",
        "--output",
        str(installed / "masters"),
    )
    assert builder.returncode == 0, builder.stderr
    summary = json.loads(builder.stdout)
    teacher_dir = Path(summary["teacher_dir"])
    assert teacher_dir.is_relative_to(installed / "masters")
    assert teacher_dir.name == "master-offline-smoke-master"

    final_check = run_installed_tool(
        installed, "verify_sources.py", "--final-check", str(teacher_dir)
    )
    assert final_check.returncode == 0, final_check.stderr
    assert final_check.stdout.strip() == "final source check OK (1 sources)"
