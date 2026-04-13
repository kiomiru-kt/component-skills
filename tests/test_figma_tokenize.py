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


def test_node_scanner_collects_letter_spacing(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    scanner = NodeScanner(client, "file-abc", "page-id")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "nodes": {
            "page-id": {
                "document": {
                    "id": "page-id",
                    "type": "FRAME",
                    "fills": [],
                    "children": [
                        {
                            "id": "n1",
                            "type": "TEXT",
                            "fills": [],
                            "style": {"letterSpacing": 5.0, "letterSpacingUnit": "PERCENT"},
                        },
                        {
                            "id": "n2",
                            "type": "TEXT",
                            "fills": [],
                            "style": {"letterSpacing": 5.0, "letterSpacingUnit": "PERCENT"},
                        },
                        {
                            "id": "n3",
                            "type": "TEXT",
                            "fills": [],
                            "style": {"letterSpacing": 0.0, "letterSpacingUnit": "PERCENT"},
                        },
                    ],
                }
            }
        }
    }
    with patch("requests.get", return_value=mock_resp):
        scanner.scan()
    # 5.0% は2回登場、0% は除外
    assert scanner.counts["letter-spacing"]["5.0%"] == 2
    assert "0.0%" not in scanner.counts["letter-spacing"]


def test_node_scanner_ignores_pixel_letter_spacing(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    scanner = NodeScanner(client, "file-abc", "page-id")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "nodes": {
            "page-id": {
                "document": {
                    "id": "page-id",
                    "type": "FRAME",
                    "fills": [],
                    "children": [
                        {
                            "id": "n1",
                            "type": "TEXT",
                            "fills": [],
                            "style": {"letterSpacing": 2.0, "letterSpacingUnit": "PIXELS"},
                        },
                    ],
                }
            }
        }
    }
    with patch("requests.get", return_value=mock_resp):
        scanner.scan()
    # PIXELS 単位は収集しない
    assert len(scanner.counts["letter-spacing"]) == 0


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


def test_token_namer_font_size_xs():
    assert TokenNamer.name_font_size("11px") == "font-size-xs"

def test_token_namer_font_size_base():
    assert TokenNamer.name_font_size("16px") == "font-size-base"

def test_token_namer_font_size_xl():
    assert TokenNamer.name_font_size("28px") == "font-size-xl"

def test_token_namer_font_size_2xl():
    assert TokenNamer.name_font_size("40px") == "font-size-2xl"

def test_token_namer_line_height_tight():
    assert TokenNamer.name_line_height("1.2") == "line-height-tight"

def test_token_namer_line_height_normal():
    assert TokenNamer.name_line_height("1.6") == "line-height-normal"

def test_token_namer_line_height_loose():
    assert TokenNamer.name_line_height("1.8") == "line-height-loose"

def test_token_namer_radius_xs():
    assert TokenNamer.name_border_radius("2px") == "radius-xs"

def test_token_namer_radius_full():
    assert TokenNamer.name_border_radius("9999px") == "radius-full"

def test_token_namer_spacing_sm():
    assert TokenNamer.name_spacing("8px") == "spacing-sm"

def test_token_namer_spacing_2xl():
    assert TokenNamer.name_spacing("48px") == "spacing-2xl"

def test_token_namer_letter_spacing_tight():
    assert TokenNamer.name_letter_spacing("-2.0%") == "letter-spacing-tight"

def test_token_namer_letter_spacing_normal():
    assert TokenNamer.name_letter_spacing("2.0%") == "letter-spacing-normal"

def test_token_namer_letter_spacing_wide():
    assert TokenNamer.name_letter_spacing("5.0%") == "letter-spacing-wide"

def test_token_namer_letter_spacing_wider():
    assert TokenNamer.name_letter_spacing("10.0%") == "letter-spacing-wider"


from figma_tokenize import TokenBuilder
from unittest.mock import MagicMock
import subprocess
import json
import tempfile
from pathlib import Path


def _make_resolver(mapping: dict):
    resolver = MagicMock()
    resolver.lookup.side_effect = lambda k: mapping.get(k)
    return resolver


def _empty_counts():
    return {"colors": {}, "font-size": {}, "line-height": {}, "letter-spacing": {}, "border-radius": {}, "spacing": {}}


def test_token_builder_filters_by_threshold():
    counts = _empty_counts()
    counts["colors"] = {"#0a0a0a": 5, "#cccccc": 2}
    builder = TokenBuilder(counts, _make_resolver({}), threshold=3)
    result = builder.build()
    assert "color-black" in result["colors"]
    assert len(result["colors"]) == 1  # #cccccc は count=2 で除外


def test_token_builder_uses_figma_variable_name():
    counts = _empty_counts()
    counts["colors"] = {"#e60000": 4}
    builder = TokenBuilder(counts, _make_resolver({"#e60000": "color/main"}), threshold=3)
    result = builder.build()
    assert "color/main" in result["colors"]
    assert result["colors"]["color/main"]["source"] == "figma_variable"


def test_token_builder_uses_node_name_when_no_variable():
    counts = _empty_counts()
    counts["colors"] = {"#0a0a0a": 5}
    builder = TokenBuilder(counts, _make_resolver({}), threshold=3)
    result = builder.build()
    assert result["colors"]["color-black"]["source"] == "node"


def test_token_builder_resolves_name_collision_with_suffix():
    # 異なる値が同じ名前（color-red）にマッピングされる
    counts = _empty_counts()
    counts["colors"] = {"#e60000": 5, "#cc0000": 4}
    builder = TokenBuilder(counts, _make_resolver({}), threshold=3)
    result = builder.build()
    names = list(result["colors"].keys())
    assert any(n.startswith("color-red") for n in names)
    assert len(names) == 2
    assert len(set(names)) == 2  # 重複なし


def test_token_builder_output_schema():
    counts = _empty_counts()
    counts["colors"] = {"#1a1a1a": 5}
    counts["font-size"] = {"16px": 4}
    counts["line-height"] = {"1.6": 3}
    counts["border-radius"] = {"4px": 3}
    counts["spacing"] = {"16px": 5}
    builder = TokenBuilder(counts, _make_resolver({}), threshold=3)
    result = builder.build()
    for category in ("colors", "font-size", "line-height", "letter-spacing", "border-radius", "spacing"):
        assert category in result
    first_color = next(iter(result["colors"].values()))
    assert "value" in first_color
    assert "count" in first_color
    assert "source" in first_color


def test_main_exits_with_error_without_token(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "FIGMA_TOKEN"}
    result = subprocess.run(
        ["python3", "scripts/figma-tokenize.py", "--file-id", "abc", "--output", str(tmp_path / "out.json")],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
        env=env,
    )
    assert result.returncode == 1
    assert "FIGMA_TOKEN" in (result.stderr + result.stdout)


def test_main_exits_with_usage_without_file_id():
    env = {**os.environ, "FIGMA_TOKEN": "fake"}
    result = subprocess.run(
        ["python3", "scripts/figma-tokenize.py"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
        env=env,
    )
    assert result.returncode == 2


def test_main_creates_output_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    output_path = tmp_path / "new_dir" / "tokens.json"

    mock_file_resp = MagicMock()
    mock_file_resp.status_code = 200
    mock_file_resp.json.return_value = {
        "document": {"children": [{"id": "p1", "name": "Components"}]}
    }
    mock_vars_resp = MagicMock()
    mock_vars_resp.status_code = 403
    http_error = requests.HTTPError(response=mock_vars_resp)
    mock_vars_resp.raise_for_status.side_effect = http_error

    mock_nodes_resp = MagicMock()
    mock_nodes_resp.status_code = 200
    mock_nodes_resp.json.return_value = {
        "nodes": {"p1": {"document": {"id": "p1", "type": "FRAME", "children": []}}}
    }

    import figma_tokenize as ft
    monkeypatch.setattr("sys.argv", [
        "figma-tokenize.py",
        "--file-id", "fake-file",
        "--output", str(output_path),
    ])

    call_count = [0]
    def side_effect(url, **kwargs):
        call_count[0] += 1
        if "variables" in url:
            return mock_vars_resp
        elif "nodes" in url:
            return mock_nodes_resp
        else:
            return mock_file_resp

    with patch("requests.get", side_effect=side_effect):
        ft.main()

    assert output_path.exists()
    data = json.loads(output_path.read_text())
    assert "meta" in data
    assert data["meta"]["file_id"] == "fake-file"
