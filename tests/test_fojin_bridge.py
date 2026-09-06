"""Tests for fojin_bridge.py — uses mocked HTTP, no real API calls."""

import json

import pytest
from unittest.mock import MagicMock, patch
from fojin_bridge import FojinBridge, FojinUnavailableError, create_bridge
import requests


def _mock_json_response(payload):
    """A stub shaped like the streamed response `_get` actually reads.

    `_get` reads the body through `iter_content` and caps it before parsing,
    so a mock that only implements `.json()` describes an implementation the
    bridge no longer has.
    """
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.iter_content = lambda _size: iter([json.dumps(payload).encode("utf-8")])
    response.json.return_value = payload
    return response


@pytest.fixture
def bridge():
    return FojinBridge(mode="api", base_url="https://fojin.app")


def test_bridge_init_defaults():
    b = FojinBridge()
    assert b.mode == "api"
    assert b.base_url == "https://fojin.app"


def test_bridge_init_strips_trailing_slash():
    b = FojinBridge(base_url="https://fojin.app/")
    assert b.base_url == "https://fojin.app"


def test_search_texts_basic(bridge):
    mock_response = _mock_json_response({"total": 1, "results": [{"id": 1}]})
    with patch.object(bridge.session, "get", return_value=mock_response) as mock_get:
        result = bridge.search_texts("般若")
        assert result["total"] == 1
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "q" in call_args.kwargs["params"]
        assert call_args.kwargs["params"]["q"] == "般若"


def test_search_texts_with_filters(bridge):
    mock_response = _mock_json_response({"total": 0, "results": []})
    with patch.object(bridge.session, "get", return_value=mock_response) as mock_get:
        bridge.search_texts("禅", sources="cbeta", lang="lzh", page=2, size=50)
        params = mock_get.call_args.kwargs["params"]
        assert params["sources"] == "cbeta"
        assert params["lang"] == "lzh"
        assert params["page"] == 2
        assert params["size"] == 50


def test_get_text_content(bridge):
    mock_response = _mock_json_response({"content": "test content", "juan_num": 1})
    with patch.object(bridge.session, "get", return_value=mock_response):
        result = bridge.get_text_content(123, 1)
        assert result["content"] == "test content"


def test_search_kg_entities(bridge):
    mock_response = _mock_json_response({"total": 1, "results": [{"id": 456, "name_zh": "玄奘"}]})
    with patch.object(bridge.session, "get", return_value=mock_response):
        result = bridge.search_kg_entities("玄奘", entity_type="person")
        assert result["results"][0]["name_zh"] == "玄奘"


def test_fojin_unavailable_on_connection_error(bridge):
    with patch.object(bridge.session, "get", side_effect=requests.ConnectionError("test")):
        with pytest.raises(FojinUnavailableError):
            bridge.search_texts("test")


def test_fojin_unavailable_on_timeout(bridge):
    with patch.object(bridge.session, "get", side_effect=requests.Timeout("test")):
        with pytest.raises(FojinUnavailableError):
            bridge.get_text(123)


def test_test_connection_returns_false_on_failure(bridge):
    with patch.object(bridge.session, "get", side_effect=requests.ConnectionError("test")):
        assert bridge.test_connection() is False


def test_create_bridge_from_env(monkeypatch):
    monkeypatch.setenv("FOJIN_URL", "https://custom.fojin.test")
    b = create_bridge()
    assert b.base_url == "https://custom.fojin.test"


# --------------------------------------------------------------------------
# FOJIN_URL comes from the environment and decides where citations get
# verified against. It had no scheme check, no response size cap, and a
# `mode` argument documented as a feature that was never written.
# --------------------------------------------------------------------------

import pytest

from fojin_bridge import (
    DEFAULT_TIMEOUT,
    MAX_RESPONSE_BYTES,
    FojinBridge,
    FojinConfigError,
    FojinUnavailableError,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://fojin.app",
        "http://evil.example.com",
        "ftp://fojin.app",
        "file:///etc/passwd",
        "//fojin.app",
        "fojin.app",
    ],
)
def test_a_non_https_base_url_is_refused(url):
    with pytest.raises(FojinConfigError):
        FojinBridge(base_url=url)


@pytest.mark.parametrize(
    "url",
    ["https://fojin.app", "https://staging.fojin.app/", "http://localhost:8000",
     "http://127.0.0.1:8000"],
)
def test_https_and_local_development_urls_are_accepted(url):
    assert FojinBridge(base_url=url).base_url == url.rstrip("/")


def test_a_trailing_slash_is_normalised_away():
    assert FojinBridge(base_url="https://fojin.app/").base_url == "https://fojin.app"


def test_an_unimplemented_mode_is_reported_not_silently_honoured(caplog):
    bridge = FojinBridge(mode="local")
    assert bridge.mode == "api"
    assert any("not implemented" in r.message for r in caplog.records)


def test_the_timeout_is_split_into_connect_and_read():
    """One scalar applied 30s to both, so a host that connects then goes
    silent held the caller for the full 30s."""
    connect, read = DEFAULT_TIMEOUT
    assert connect < read


class _FakeResponse:
    def __init__(self, chunks):
        self._chunks = chunks
        self.closed = False

    def raise_for_status(self):
        return None

    def iter_content(self, _size):
        yield from self._chunks

    def close(self):
        self.closed = True


def test_an_oversized_response_is_refused_rather_than_buffered():
    oversized = [b"x" * (1024 * 1024)] * (MAX_RESPONSE_BYTES // (1024 * 1024) + 2)
    with pytest.raises(FojinUnavailableError, match="exceeded"):
        FojinBridge._read_capped(_FakeResponse(oversized))


def test_a_normal_response_is_read_whole():
    assert FojinBridge._read_capped(_FakeResponse([b'{"a"', b":1}"])) == b'{"a":1}'


def test_the_streamed_response_is_always_closed():
    bridge = FojinBridge()
    response = _FakeResponse([b"{}"])
    bridge.session = type("S", (), {"get": staticmethod(lambda *a, **k: response)})()
    assert bridge._get("/api/stats") == {}
    assert response.closed, "a streamed response holds its connection until closed"
