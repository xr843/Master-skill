"""Tests for verify_sources.py — pure logic, no API calls."""

import pytest
from verify_sources import full_to_short_cbeta, FULL_CBETA_RE, FOJIN_URL_RE


def test_verify_sources_module_imports():
    """Verify verify_sources.py can be imported without errors."""
    import verify_sources
    assert callable(getattr(verify_sources, "main", None))


def test_full_to_short_cbeta_t_series():
    assert full_to_short_cbeta("T08n0235") == "T0235"


def test_full_to_short_cbeta_x_series():
    assert full_to_short_cbeta("X62n1182") == "X1182"


def test_full_to_short_cbeta_j_series():
    assert full_to_short_cbeta("J36n0348") == "J0348"


def test_full_to_short_cbeta_strips_volume_number():
    # Volume number (middle digits) must be dropped
    assert full_to_short_cbeta("T34n1718") == "T1718"
    assert full_to_short_cbeta("T01n0001") == "T0001"


def test_full_to_short_cbeta_invalid_returns_none():
    assert full_to_short_cbeta("invalid") is None
    assert full_to_short_cbeta("") is None
    assert full_to_short_cbeta("123") is None


def test_cbeta_id_format_recognition():
    """CBETA IDs follow format like T48n2008, X62n1182, J36n0348."""
    valid_ids = ["T48n2008", "X62n1182", "J36n0348", "T01n0001"]
    for cbeta_id in valid_ids:
        assert FULL_CBETA_RE.match(cbeta_id), f"{cbeta_id} should match FULL_CBETA_RE"


def test_cbeta_id_rejects_invalid():
    invalid_ids = ["T48", "n2008", "abc123", "t48n2008"]  # lowercase prefix is invalid
    for cbeta_id in invalid_ids:
        assert not FULL_CBETA_RE.match(cbeta_id), f"{cbeta_id} should not match FULL_CBETA_RE"


def test_fojin_url_re_matches_cbeta_url():
    line = "See https://fojin.app/texts/T08n0235 for reference"
    m = FOJIN_URL_RE.search(line)
    assert m is not None
    assert m.group(2) == "T08n0235"


def test_fojin_url_re_matches_numeric_id():
    line = "Link: https://fojin.app/texts/12345"
    m = FOJIN_URL_RE.search(line)
    assert m is not None
    assert m.group(2) == "12345"


def test_fojin_url_re_no_match_on_unrelated_url():
    line = "Visit https://example.com/texts/something"
    assert FOJIN_URL_RE.search(line) is None
