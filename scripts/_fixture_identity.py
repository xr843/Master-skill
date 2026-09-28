"""Stable identity for the complete fidelity fixture used to grade an answer."""

from __future__ import annotations

import hashlib
import json


def fixture_sha256(fixture: dict) -> str:
    encoded = json.dumps(
        fixture, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
