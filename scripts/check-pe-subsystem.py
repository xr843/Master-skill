#!/usr/bin/env python3
"""Check which Windows subsystem a PE executable was linked for.

A Rust binary is a console program unless `#![windows_subsystem = "windows"]`
says otherwise, and Windows gives every console program a console window.
v0.12.1's desktop manager was one: double-clicking it opened a console window
behind the GUI. `file` reports such a binary as `PE32+ executable (console)`.
The field behind that is the Subsystem word of the optional header: 2 for a
GUI program, 3 for a console one.

Usage:
    python scripts/check-pe-subsystem.py <exe> --expect 2
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

SUBSYSTEMS = {2: "Windows GUI", 3: "Windows console"}


def pe_subsystem(data: bytes) -> int:
    """Return the Subsystem field of a PE image's optional header."""
    if data[:2] != b"MZ":
        raise ValueError("not a PE file: no MZ header")
    (pe_offset,) = struct.unpack_from("<I", data, 0x3C)
    if data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("not a PE file: no PE signature")
    # The optional header follows the 4-byte signature and the 20-byte COFF
    # header; Subsystem sits 68 bytes into it in both PE32 and PE32+.
    (subsystem,) = struct.unpack_from("<H", data, pe_offset + 24 + 68)
    return subsystem


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("exe", type=Path)
    parser.add_argument("--expect", type=int, required=True, help="2 = GUI, 3 = console")
    args = parser.parse_args(argv)
    try:
        with args.exe.open("rb") as handle:
            subsystem = pe_subsystem(handle.read(4096))
    except (OSError, ValueError, struct.error) as exc:
        print(f"✗ {args.exe}: {exc}")
        return 1
    found = f"{subsystem} ({SUBSYSTEMS.get(subsystem, 'other')})"
    if subsystem != args.expect:
        wanted = f"{args.expect} ({SUBSYSTEMS.get(args.expect, 'other')})"
        print(f"✗ {args.exe}: subsystem {found}, expected {wanted}")
        return 1
    print(f"✓ {args.exe}: subsystem {found}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
