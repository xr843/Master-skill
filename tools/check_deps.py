#!/usr/bin/env python3
"""Check the Python packages create-master's tools import at startup.

Every generator tool imports `fojin_bridge` (which imports `requests`) or
`skill_writer` (which imports `yaml` and `pypinyin`) at module level. Without those
packages each one exits with `ModuleNotFoundError` before doing anything — even
`master_builder.py --offline-smoke`, which never touches the network. Measured
2026-09-17 in a clean venv: `rag_query.py`, `sutra_collector.py` and
`master_builder.py` all failed that way.

Nothing told an npx user to install them. The only mention was the clone guide's
`pip install -r requirements.txt`, and on recent Debian, Ubuntu and Homebrew Pythons
that command is itself refused as an externally-managed environment (PEP 668).

Standard library only, so it runs where the tools cannot.

Usage:
    python3 tools/check_deps.py          # exit 1 and print how to install if missing
    python3 tools/check_deps.py --json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from pathlib import Path

# import name -> distribution name in requirements.txt
REQUIRED = {"requests": "requests", "yaml": "pyyaml", "pypinyin": "pypinyin"}
MIN_PYTHON = (3, 9)
REQUIREMENTS = Path(__file__).resolve().parent.parent / "requirements.txt"


def missing(find_spec=importlib.util.find_spec) -> list[str]:
    """Distributions whose import name cannot be found."""
    return [dist for module, dist in REQUIRED.items() if find_spec(module) is None]


def guidance(missing_dists: list[str], requirements: Path = REQUIREMENTS) -> str:
    venv_python = (
        r"%USERPROFILE%\.venvs\master-skill\Scripts\python"
        if sys.platform == "win32"
        else "~/.venvs/master-skill/bin/python"
    )
    return "\n".join(
        [
            "create-master needs Python packages that are not installed: "
            + ", ".join(missing_dists),
            "",
            f'  python3 -m pip install -r "{requirements}"',
            "",
            'If pip refuses with "externally-managed-environment" (PEP 668), use a virtual environment:',
            "",
            "  python3 -m venv ~/.venvs/master-skill",
            f'  {venv_python} -m pip install -r "{requirements}"',
            "",
            "and start Claude Code with that environment active, so that `python3` is its interpreter.",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print a JSON result")
    args = parser.parse_args(argv)

    too_old = sys.version_info < MIN_PYTHON
    absent = missing()
    ok = not absent and not too_old
    if args.json:
        print(
            json.dumps(
                {
                    "ok": ok,
                    "python": platform.python_version(),
                    "python_too_old": too_old,
                    "missing": absent,
                    "requirements": str(REQUIREMENTS),
                }
            )
        )
    elif ok:
        print(f"OK: Python {platform.python_version()} with {', '.join(REQUIRED.values())}")
    else:
        if too_old:
            print(f"create-master needs Python {'.'.join(map(str, MIN_PYTHON))}+; this is {platform.python_version()}.")
        if absent:
            print(guidance(absent))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
