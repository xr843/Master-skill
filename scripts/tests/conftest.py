"""Put scripts/ on sys.path, as `python3 scripts/<x>.py` does.

Scripts import their shared helpers as siblings (`from _skill_io import ROOT`).
tests/conftest.py already did this for a full `pytest` run; this one covers
running a single file here, e.g. `pytest scripts/tests/test_validate.py`.
"""
import sys
from pathlib import Path

SCRIPTS = str(Path(__file__).resolve().parents[1])
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
