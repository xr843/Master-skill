"""Tests for fojin_bridge.py — uses mocked HTTP, no real API calls."""

import pytest
from unittest.mock import MagicMock, patch
from fojin_bridge import FojinBridge, FojinUnavailableError, create_bridge
import requests


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
    mock_response = MagicMock()
    mock_response.json.return_value = {"total": 1, "results": [{"id": 1}]}
    mock_response.raise_for_status = MagicMock()
    with patch.object(bridge.session, "get", return_value=mock_response) as mock_get:
        result = bridge.search_texts("般若")
        assert result["total"] == 1
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "q" in call_args.kwargs["params"]
        assert call_args.kwargs["params"]["q"] == "般若"


def test_search_texts_with_filters(bridge):
    mock_response = MagicMock()
    mock_response.json.return_value = {"total": 0, "results": []}
    mock_response.raise_for_status = MagicMock()
    with patch.object(bridge.session, "get", return_value=mock_response) as mock_get:
        bridge.search_texts("禅", sources="cbeta", lang="lzh", page=2, size=50)
        params = mock_get.call_args.kwargs["params"]
        assert params["sources"] == "cbeta"
        assert params["lang"] == "lzh"
        assert params["page"] == 2
        assert params["size"] == 50


def test_get_text_content(bridge):
    mock_response = MagicMock()
    mock_response.json.return_value = {"content": "test content", "juan_num": 1}
    mock_response.raise_for_status = MagicMock()
    with patch.object(bridge.session, "get", return_value=mock_response):
        result = bridge.get_text_content(123, 1)
        assert result["content"] == "test content"


def test_search_kg_entities(bridge):
    mock_response = MagicMock()
    mock_response.json.return_value = {"total": 1, "results": [{"id": 456, "name_zh": "玄奘"}]}
    mock_response.raise_for_status = MagicMock()
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
