#!/usr/bin/env python3
"""Check which Windows subsystem a PE executable was linked for.

The field is the Subsystem word of the PE optional header: 2 for a GUI
program, 3 for a console one (`file` prints the latter as `PE32+ executable
(console)`). The desktop manager is kept a console program. A GUI-subsystem
build stops double-clicking from opening a console window, but on
release-desktop run 34858072308 PowerShell did not wait for it, closed the
pipe, and `--help > help.txt` panicked. The release smoke test runs this with
`--expect 3` so the switch cannot come back unmeasured.

Output is ASCII only. This runs on the Windows release runner, whose console
encoding is cp1252; a check mark there raised UnicodeEncodeError after the
check itself had passed.

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
        print(f"FAIL {args.exe}: {exc}")
        return 1
    found = f"{subsystem} ({SUBSYSTEMS.get(subsystem, 'other')})"
    if subsystem != args.expect:
        wanted = f"{args.expect} ({SUBSYSTEMS.get(args.expect, 'other')})"
        print(f"FAIL {args.exe}: subsystem {found}, expected {wanted}")
        return 1
    print(f"OK {args.exe}: subsystem {found}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
