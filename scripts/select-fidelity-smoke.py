#!/usr/bin/env python3
"""Select one fidelity smoke target from persona metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


class SelectionError(ValueError):
    """Raised when a smoke target cannot be selected safely."""


def discover_roster(prebuilt: Path) -> list[str]:
    """Return sorted persona directories with a non-empty sources list."""
    roster: list[str] = []
    for meta_path in sorted(prebuilt.glob("master-*/meta.json")):
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SelectionError(f"Invalid metadata {meta_path}: {exc}") from exc
        sources = metadata.get("sources")
        if isinstance(sources, list) and sources:
            roster.append(meta_path.parent.name)
    return roster


def parse_day_of_year(raw_day: str) -> int:
    """Parse a zero-padded day of year explicitly as base 10."""
    try:
        day = int(raw_day, 10)
    except ValueError as exc:
        raise SelectionError(f"Invalid day-of-year: {raw_day!r}") from exc
    if not 1 <= day <= 366:
        raise SelectionError(f"Invalid day-of-year: {raw_day!r}")
    return day


def select_target(
    roster: list[str], day_of_year: int, changed: list[str]
) -> str:
    """Prefer the first discovered changed persona; otherwise rotate by day."""
    if not roster:
        raise SelectionError("No persona smoke targets discovered from metadata sources")
    for candidate in changed:
        if candidate in roster:
            return candidate
    return roster[day_of_year % len(roster)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prebuilt", type=Path, default=Path("prebuilt"))
    parser.add_argument("--day-of-year", required=True)
    parser.add_argument(
        "--changed",
        action="append",
        default=[],
        help="changed prebuilt directory; repeat to preserve diff order",
    )
    args = parser.parse_args()

    try:
        roster = discover_roster(args.prebuilt)
        day_of_year = parse_day_of_year(args.day_of_year)
        target = select_target(roster, day_of_year, args.changed)
    except SelectionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
