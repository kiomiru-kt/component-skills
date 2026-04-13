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
