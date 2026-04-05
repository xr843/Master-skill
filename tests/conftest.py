"""Shared pytest fixtures for Buddha-skill tests."""

import sys
import os
from pathlib import Path

# Add tools/ to path so tests can import modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))
