import figma_tokenize


def test_classes_are_importable():
    assert hasattr(figma_tokenize, "FigmaClient")
    assert hasattr(figma_tokenize, "VariableResolver")
    assert hasattr(figma_tokenize, "NodeScanner")
    assert hasattr(figma_tokenize, "TokenNamer")
    assert hasattr(figma_tokenize, "TokenBuilder")


import os
import requests
import pytest
from unittest.mock import patch, MagicMock
from figma_tokenize import FigmaClient


def test_figma_client_raises_if_no_token(monkeypatch):
    monkeypatch.delenv("FIGMA_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        FigmaClient()


def test_figma_client_raises_on_401(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    http_error = requests.HTTPError(response=mock_resp)
    mock_resp.raise_for_status.side_effect = http_error
    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(SystemExit, match="FIGMA_TOKEN"):
            client.get("/files/abc")


def test_figma_client_retries_on_429(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_ok = MagicMock()
    mock_ok.status_code = 200
    mock_ok.json.return_value = {"ok": True}
    with patch("requests.get", side_effect=[mock_429, mock_ok]):
        with patch("time.sleep"):
            result = client.get("/files/abc")
    assert result == {"ok": True}


def test_figma_client_raises_after_3_retries_on_429(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    mock_429 = MagicMock()
    mock_429.status_code = 429
    with patch("requests.get", return_value=mock_429):
        with patch("time.sleep"):
            with pytest.raises(SystemExit, match="rate limit"):
                client.get("/files/abc")


def test_figma_client_returns_json_on_success(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"name": "MyFile"}
    with patch("requests.get", return_value=mock_resp):
        result = client.get("/files/abc")
    assert result == {"name": "MyFile"}


from figma_tokenize import VariableResolver

MOCK_VARIABLES_RESPONSE = {
    "meta": {
        "variables": {
            "VariableID:1": {
                "name": "color/main",
                "resolvedType": "COLOR",
                "valuesByMode": {
                    "1:0": {"r": 0.902, "g": 0.0, "b": 0.0, "a": 1.0}
                },
            },
            "VariableID:2": {
                "name": "font-size/base",
                "resolvedType": "FLOAT",
                "valuesByMode": {"1:0": 16.0},
            },
        }
    }
}


def test_variable_resolver_builds_color_map(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    resolver = VariableResolver(client, "file-abc")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_VARIABLES_RESPONSE
    with patch("requests.get", return_value=mock_resp):
        resolver.load()
    # r=0.902 → round(0.902*255)=230=0xe6, g=0→0x00, b=0→0x00
    assert resolver.lookup("#e60000") == "color/main"


def test_variable_resolver_builds_float_map(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    resolver = VariableResolver(client, "file-abc")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_VARIABLES_RESPONSE
    with patch("requests.get", return_value=mock_resp):
        resolver.load()
    assert resolver.lookup("16px") == "font-size/base"


def test_variable_resolver_fallback_on_403(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    resolver = VariableResolver(client, "file-abc")
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    http_error = requests.HTTPError(response=mock_resp)
    mock_resp.raise_for_status.side_effect = http_error
    with patch("requests.get", return_value=mock_resp):
        resolver.load()  # Should NOT raise
    assert resolver.lookup("#e60000") is None


def test_variable_resolver_returns_none_for_unknown(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    resolver = VariableResolver(client, "file-abc")
    # load() 未呼び出し → マップは空
    assert resolver.lookup("#ffffff") is None
