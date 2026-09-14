"""Tests for the PE subsystem check used by the Windows release smoke test."""

from __future__ import annotations

import importlib.util
import struct
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check-pe-subsystem.py"


@pytest.fixture
def mod():
    spec = importlib.util.spec_from_file_location("check_pe_subsystem", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_pe_subsystem"] = module
    spec.loader.exec_module(module)
    return module


def _pe(subsystem: int, *, magic: int = 0x20B, pe_offset: int = 0x80) -> bytes:
    """A header-only PE image: just the fields the check reads."""
    image = bytearray(512)
    image[:2] = b"MZ"
    struct.pack_into("<I", image, 0x3C, pe_offset)
    image[pe_offset:pe_offset + 4] = b"PE\0\0"
    struct.pack_into("<H", image, pe_offset + 24, magic)
    struct.pack_into("<H", image, pe_offset + 24 + 68, subsystem)
    return bytes(image)


def test_reads_a_gui_program(mod):
    assert mod.pe_subsystem(_pe(2)) == 2


def test_reads_a_console_program_in_pe32_as_well(mod):
    assert mod.pe_subsystem(_pe(3, magic=0x10B)) == 3


def test_a_console_binary_fails_when_a_gui_one_is_expected(mod, tmp_path, capsys):
    exe = tmp_path / "app.exe"
    exe.write_bytes(_pe(3))
    assert mod.main([str(exe), "--expect", "2"]) == 1
    assert "subsystem 3 (Windows console), expected 2 (Windows GUI)" in capsys.readouterr().out


def test_the_expected_subsystem_passes(mod, tmp_path):
    exe = tmp_path / "app.exe"
    exe.write_bytes(_pe(2))
    assert mod.main([str(exe), "--expect", "2"]) == 0


def test_a_file_that_is_not_a_pe_image_fails(mod, tmp_path):
    exe = tmp_path / "app"
    exe.write_bytes(b"\x7fELF" + bytes(100))
    assert mod.main([str(exe), "--expect", "2"]) == 1


def test_a_header_pointing_past_the_data_fails_instead_of_raising(mod, tmp_path):
    image = bytearray(_pe(2))
    struct.pack_into("<I", image, 0x3C, 10_000)
    exe = tmp_path / "app.exe"
    exe.write_bytes(bytes(image))
    assert mod.main([str(exe), "--expect", "2"]) == 1
