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


from figma_tokenize import NodeScanner

MOCK_NODES_RESPONSE = {
    "nodes": {
        "page-id": {
            "document": {
                "id": "page-id",
                "type": "FRAME",
                "fills": [{"type": "SOLID", "color": {"r": 0.1, "g": 0.1, "b": 0.1, "a": 1.0}}],
                "style": {"fontSize": 16, "lineHeightPx": 25.6},
                "cornerRadius": 4,
                "paddingLeft": 16,
                "paddingRight": 16,
                "paddingTop": 8,
                "paddingBottom": 8,
                "itemSpacing": 8,
                "children": [
                    {
                        "id": "child-1",
                        "type": "TEXT",
                        "fills": [{"type": "SOLID", "color": {"r": 0.1, "g": 0.1, "b": 0.1, "a": 1.0}}],
                        "style": {"fontSize": 14, "lineHeightPx": 22.4},
                        "cornerRadius": 0,
                    }
                ],
            }
        }
    }
}


def test_node_scanner_collects_colors(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    scanner = NodeScanner(client, "file-abc", "page-id")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_NODES_RESPONSE
    with patch("requests.get", return_value=mock_resp):
        scanner.scan()
    # #1a1a1a は親 + 子で 2回登場
    assert scanner.counts["colors"]["#1a1a1a"] == 2


def test_node_scanner_collects_font_sizes(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    scanner = NodeScanner(client, "file-abc", "page-id")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_NODES_RESPONSE
    with patch("requests.get", return_value=mock_resp):
        scanner.scan()
    assert scanner.counts["font-size"]["16px"] == 1
    assert scanner.counts["font-size"]["14px"] == 1


def test_node_scanner_excludes_border_radius_zero(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    scanner = NodeScanner(client, "file-abc", "page-id")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_NODES_RESPONSE
    with patch("requests.get", return_value=mock_resp):
        scanner.scan()
    assert "0px" not in scanner.counts["border-radius"]
    assert scanner.counts["border-radius"].get("4px") == 1


def test_node_scanner_collects_spacing(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    scanner = NodeScanner(client, "file-abc", "page-id")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_NODES_RESPONSE
    with patch("requests.get", return_value=mock_resp):
        scanner.scan()
    # paddingLeft=16, paddingRight=16 → 16px: 2回
    # paddingTop=8, paddingBottom=8, itemSpacing=8 → 8px: 3回
    assert scanner.counts["spacing"]["16px"] == 2
    assert scanner.counts["spacing"]["8px"] == 3


def test_node_scanner_ignores_non_solid_fills(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    scanner = NodeScanner(client, "file-abc", "page-id")
    response = {
        "nodes": {
            "page-id": {
                "document": {
                    "id": "page-id",
                    "type": "FRAME",
                    "fills": [{"type": "GRADIENT_LINEAR"}],
                    "children": [],
                }
            }
        }
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = response
    with patch("requests.get", return_value=mock_resp):
        scanner.scan()
    assert scanner.counts["colors"] == {}


from figma_tokenize import TokenNamer


def test_token_namer_black():
    assert TokenNamer.name_color("#0a0a0a") == "color-black"

def test_token_namer_white():
    assert TokenNamer.name_color("#f5f5f5") == "color-white"

def test_token_namer_gray():
    name = TokenNamer.name_color("#808080")
    assert name.startswith("color-gray-")

def test_token_namer_red():
    assert TokenNamer.name_color("#e60000") == "color-red"

def test_token_namer_blue():
    assert TokenNamer.name_color("#0066ff") == "color-blue"

def test_token_namer_green():
    assert TokenNamer.name_color("#00cc44") == "color-green"

def test_token_namer_orange():
    assert TokenNamer.name_color("#ff6600") == "color-orange"

def test_token_namer_yellow():
    assert TokenNamer.name_color("#ffcc00") == "color-yellow"

def test_token_namer_purple():
    assert TokenNamer.name_color("#9900cc") == "color-purple"
