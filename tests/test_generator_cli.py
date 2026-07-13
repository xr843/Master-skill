"""Offline CLI contract tests for the installed create-master runtime."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


TOOLS = Path(__file__).resolve().parents[1] / "tools"


def run_tool(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOLS / name), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_collector_and_builder_expose_real_argparse_help():
    for tool in ("sutra_collector.py", "master_builder.py"):
        result = run_tool(tool, "--help")
        assert result.returncode == 0
        assert "usage:" in result.stdout


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
    assert meta_path.is_file()
    assert review_path.is_file()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert meta["citation_contract"] == review["citation_contract"]
    assert meta["citation_contract"]["allowed_source_types"] == [
        "compiled_teaching"
    ]
