# figma-tokenize.py Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FigmaのComponentsページを走査してデザイントークン（色・font-size・line-height・border-radius・spacing）を集計し、SCSS変数のベースとなるJSONを生成するPythonスクリプトを実装する。

**Architecture:** シングルファイル（`scripts/figma-tokenize.py`）に `FigmaClient` / `VariableResolver` / `NodeScanner` / `TokenNamer` / `TokenBuilder` の5クラスと `main()` を収める。Figma Variables APIで既定義トークンを取得し、Nodes APIで走査した値と突き合わせて重複を排除する。

**Tech Stack:** Python 3.10+, `requests`, `colorsys`（標準ライブラリ）, `pytest`, `pytest-mock`

---

## File Structure

```
component-skills/
├── scripts/
│   └── figma-tokenize.py   # 全クラスとmain()を収めるシングルファイル
├── tests/
│   ├── conftest.py          # figma-tokenize.pyをimportlib経由でロード
│   └── test_figma_tokenize.py
└── requirements-dev.txt     # pytest, pytest-mock
```

---

## Task 1: Scaffold

**Files:**
- Create: `scripts/figma-tokenize.py`
- Create: `tests/conftest.py`
- Create: `tests/test_figma_tokenize.py`
- Create: `requirements-dev.txt`

- [ ] **Step 1: `requirements-dev.txt` を作成する**

```
pytest
pytest-mock
requests
```

- [ ] **Step 2: `scripts/figma-tokenize.py` のスケルトンを作成する**

```python
#!/usr/bin/env python3
"""
figma-tokenize: Extract design tokens from a Figma file.

Usage:
    python3 figma-tokenize.py --file-id FILE_ID --output PATH [--page COMPONENTS] [--threshold 3]
"""
import argparse
import colorsys
import json
import os
import sys
import time
from datetime import datetime

import requests


class FigmaClient:
    pass


class VariableResolver:
    pass


class NodeScanner:
    pass


class TokenNamer:
    pass


class TokenBuilder:
    pass


def main():
    pass


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: `tests/conftest.py` を作成する**

```python
import importlib.util
import sys
from pathlib import Path


def _load_script():
    script_path = Path(__file__).parent.parent / "scripts" / "figma-tokenize.py"
    spec = importlib.util.spec_from_file_location("figma_tokenize", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


figma_tokenize = _load_script()
sys.modules["figma_tokenize"] = figma_tokenize
```

- [ ] **Step 4: `tests/test_figma_tokenize.py` にインポートテストを書く**

```python
import figma_tokenize


def test_classes_are_importable():
    assert hasattr(figma_tokenize, "FigmaClient")
    assert hasattr(figma_tokenize, "VariableResolver")
    assert hasattr(figma_tokenize, "NodeScanner")
    assert hasattr(figma_tokenize, "TokenNamer")
    assert hasattr(figma_tokenize, "TokenBuilder")
```

- [ ] **Step 5: テストが通ることを確認する**

```bash
cd ~/Workspace/component-skills
pip install -r requirements-dev.txt
pytest tests/test_figma_tokenize.py::test_classes_are_importable -v
```

Expected: `PASSED`

- [ ] **Step 6: コミットする**

```bash
git add scripts/figma-tokenize.py tests/conftest.py tests/test_figma_tokenize.py requirements-dev.txt
git commit -m "feat: scaffold figma-tokenize.py with class stubs"
```

---

## Task 2: FigmaClient

**Files:**
- Modify: `scripts/figma-tokenize.py` — `FigmaClient` クラスを実装
- Modify: `tests/test_figma_tokenize.py` — FigmaClient テストを追加

- [ ] **Step 1: 失敗するテストを書く**

```python
import os
import pytest
from unittest.mock import patch, MagicMock
import figma_tokenize
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
    mock_resp.raise_for_status.side_effect = requests.HTTPError(response=mock_resp)
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_figma_tokenize.py -k "figma_client" -v
```

Expected: 全件 `FAILED`

- [ ] **Step 3: `FigmaClient` を実装する**

```python
class FigmaClient:
    BASE_URL = "https://api.figma.com/v1"

    def __init__(self):
        token = os.environ.get("FIGMA_TOKEN")
        if not token:
            raise SystemExit("Error: FIGMA_TOKEN environment variable is not set.")
        self._headers = {"X-Figma-Token": token}

    def get(self, path: str, params: dict = None) -> dict:
        url = f"{self.BASE_URL}{path}"
        for attempt in range(3):
            resp = requests.get(url, headers=self._headers, params=params)
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            if resp.status_code == 401:
                raise SystemExit(
                    "Error: Figma API returned 401. Please check your FIGMA_TOKEN."
                )
            resp.raise_for_status()
            return resp.json()
        raise SystemExit("Error: Figma API rate limit exceeded after 3 retries.")
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
pytest tests/test_figma_tokenize.py -k "figma_client" -v
```

Expected: 全件 `PASSED`

- [ ] **Step 5: コミットする**

```bash
git add scripts/figma-tokenize.py tests/test_figma_tokenize.py
git commit -m "feat: implement FigmaClient with auth and retry"
```

---

## Task 3: VariableResolver

**Files:**
- Modify: `scripts/figma-tokenize.py` — `VariableResolver` クラスを実装
- Modify: `tests/test_figma_tokenize.py` — VariableResolver テストを追加

- [ ] **Step 1: 失敗するテストを書く**

```python
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
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_VARIABLES_RESPONSE
        mock_get.return_value = mock_resp
        resolver.load()
    assert resolver.lookup("#e60000") == "color/main"


def test_variable_resolver_builds_float_map(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    resolver = VariableResolver(client, "file-abc")
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_VARIABLES_RESPONSE
        mock_get.return_value = mock_resp
        resolver.load()
    assert resolver.lookup("16px") == "font-size/base"


def test_variable_resolver_fallback_on_403(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    resolver = VariableResolver(client, "file-abc")
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.raise_for_status.side_effect = requests.HTTPError(response=mock_resp)
    with patch("requests.get", return_value=mock_resp):
        resolver.load()  # Should NOT raise
    assert resolver.lookup("#e60000") is None


def test_variable_resolver_returns_none_for_unknown(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    resolver = VariableResolver(client, "file-abc")
    resolver.load.__func__  # unloaded — map is empty
    assert resolver.lookup("#ffffff") is None
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_figma_tokenize.py -k "variable_resolver" -v
```

Expected: 全件 `FAILED`

- [ ] **Step 3: `VariableResolver` を実装する**

```python
class VariableResolver:
    def __init__(self, client: "FigmaClient", file_id: str):
        self._client = client
        self._file_id = file_id
        self._map: dict[str, str] = {}

    def load(self) -> None:
        try:
            data = self._client.get(f"/files/{self._file_id}/variables/local")
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                print(
                    "Warning: Figma Variables API returned 403 (paid plan required). "
                    "Proceeding without pre-defined variables.",
                    file=sys.stderr,
                )
                return
            raise

        variables = data.get("meta", {}).get("variables", {})
        for var in variables.values():
            name = var.get("name", "")
            resolved_type = var.get("resolvedType")
            values = var.get("valuesByMode", {})
            if not values:
                continue
            # Use first mode's value
            first_value = next(iter(values.values()))

            if resolved_type == "COLOR" and isinstance(first_value, dict):
                hex_key = _rgba_to_hex(
                    first_value["r"], first_value["g"], first_value["b"]
                )
                self._map[hex_key] = name

            elif resolved_type == "FLOAT" and isinstance(first_value, (int, float)):
                px_key = f"{int(first_value)}px"
                self._map[px_key] = name

    def lookup(self, key: str) -> str | None:
        return self._map.get(key)


def _rgba_to_hex(r: float, g: float, b: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        round(r * 255), round(g * 255), round(b * 255)
    )
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
pytest tests/test_figma_tokenize.py -k "variable_resolver" -v
```

Expected: 全件 `PASSED`

- [ ] **Step 5: コミットする**

```bash
git add scripts/figma-tokenize.py tests/test_figma_tokenize.py
git commit -m "feat: implement VariableResolver with 403 fallback"
```

---

## Task 4: NodeScanner

**Files:**
- Modify: `scripts/figma-tokenize.py` — `NodeScanner` クラスを実装
- Modify: `tests/test_figma_tokenize.py` — NodeScanner テストを追加

- [ ] **Step 1: 失敗するテストを書く**

```python
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
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_NODES_RESPONSE
        mock_get.return_value = mock_resp
        scanner.scan()
    # #1a1a1a appears twice (parent + child)
    assert scanner.counts["colors"]["#1a1a1a"] == 2


def test_node_scanner_collects_font_sizes(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    scanner = NodeScanner(client, "file-abc", "page-id")
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_NODES_RESPONSE
        mock_get.return_value = mock_resp
        scanner.scan()
    assert scanner.counts["font-size"]["16px"] == 1
    assert scanner.counts["font-size"]["14px"] == 1


def test_node_scanner_excludes_border_radius_zero(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    scanner = NodeScanner(client, "file-abc", "page-id")
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_NODES_RESPONSE
        mock_get.return_value = mock_resp
        scanner.scan()
    # child has cornerRadius=0, should be excluded
    assert "0px" not in scanner.counts["border-radius"]
    assert scanner.counts["border-radius"].get("4px") == 1


def test_node_scanner_collects_spacing(monkeypatch):
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")
    client = FigmaClient()
    scanner = NodeScanner(client, "file-abc", "page-id")
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_NODES_RESPONSE
        mock_get.return_value = mock_resp
        scanner.scan()
    # paddingLeft=16, paddingRight=16, paddingTop=8, paddingBottom=8, itemSpacing=8
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
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = response
        mock_get.return_value = mock_resp
        scanner.scan()
    assert scanner.counts["colors"] == {}
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_figma_tokenize.py -k "node_scanner" -v
```

Expected: 全件 `FAILED`

- [ ] **Step 3: `NodeScanner` を実装する**

```python
class NodeScanner:
    def __init__(self, client: "FigmaClient", file_id: str, page_id: str):
        self._client = client
        self._file_id = file_id
        self._page_id = page_id
        self.counts: dict[str, dict[str, int]] = {
            "colors": {},
            "font-size": {},
            "line-height": {},
            "border-radius": {},
            "spacing": {},
        }

    def scan(self) -> None:
        data = self._client.get(
            f"/files/{self._file_id}/nodes",
            params={"ids": self._page_id},
        )
        page_node = data["nodes"][self._page_id]["document"]
        self._walk(page_node)

    def _walk(self, node: dict) -> None:
        self._extract(node)
        for child in node.get("children", []):
            self._walk(child)

    def _extract(self, node: dict) -> None:
        # Colors from SOLID fills
        for fill in node.get("fills", []):
            if fill.get("type") == "SOLID":
                c = fill["color"]
                hex_val = _rgba_to_hex(c["r"], c["g"], c["b"])
                self.counts["colors"][hex_val] = (
                    self.counts["colors"].get(hex_val, 0) + 1
                )

        # font-size and line-height
        style = node.get("style", {})
        if "fontSize" in style:
            key = f"{int(style['fontSize'])}px"
            self.counts["font-size"][key] = self.counts["font-size"].get(key, 0) + 1
        if "lineHeightPx" in style:
            # Store as ratio relative to fontSize when available, else raw px
            fs = style.get("fontSize", style["lineHeightPx"])
            ratio = round(style["lineHeightPx"] / fs, 2) if fs else 0
            key = str(ratio)
            self.counts["line-height"][key] = (
                self.counts["line-height"].get(key, 0) + 1
            )

        # border-radius (exclude 0)
        radius = node.get("cornerRadius")
        if radius is not None and radius > 0:
            key = f"{int(radius)}px"
            self.counts["border-radius"][key] = (
                self.counts["border-radius"].get(key, 0) + 1
            )

        # Spacing: padding + itemSpacing
        for field in ("paddingLeft", "paddingRight", "paddingTop", "paddingBottom", "itemSpacing"):
            val = node.get(field)
            if val is not None and val > 0:
                key = f"{int(val)}px"
                self.counts["spacing"][key] = self.counts["spacing"].get(key, 0) + 1
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
pytest tests/test_figma_tokenize.py -k "node_scanner" -v
```

Expected: 全件 `PASSED`

- [ ] **Step 5: コミットする**

```bash
git add scripts/figma-tokenize.py tests/test_figma_tokenize.py
git commit -m "feat: implement NodeScanner with recursive node walking"
```

---

## Task 5: TokenNamer — colors

**Files:**
- Modify: `scripts/figma-tokenize.py` — `TokenNamer` のカラー命名を実装
- Modify: `tests/test_figma_tokenize.py` — カラー命名テストを追加

- [ ] **Step 1: 失敗するテストを書く**

```python
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_figma_tokenize.py -k "token_namer_" -v
```

Expected: 全件 `FAILED`

- [ ] **Step 3: `TokenNamer` のカラー命名を実装する**

```python
class TokenNamer:
    @staticmethod
    def name_color(hex_value: str) -> str:
        hex_value = hex_value.lstrip("#")
        r = int(hex_value[0:2], 16) / 255
        g = int(hex_value[2:4], 16) / 255
        b = int(hex_value[4:6], 16) / 255
        h, s, v = colorsys.rgb_to_hsv(r, g, b)

        if v < 0.1:
            return "color-black"
        if v > 0.95 and s < 0.05:
            return "color-white"
        if s < 0.15:
            gray_pct = int(v * 100)
            return f"color-gray-{gray_pct}"

        hue_deg = h * 360
        if hue_deg < 15 or hue_deg >= 345:
            return "color-red"
        elif hue_deg < 45:
            return "color-orange"
        elif hue_deg < 75:
            return "color-yellow"
        elif hue_deg < 165:
            return "color-green"
        elif hue_deg < 255:
            return "color-blue"
        else:
            return "color-purple"
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
pytest tests/test_figma_tokenize.py -k "token_namer_" -v
```

Expected: 全件 `PASSED`

- [ ] **Step 5: コミットする**

```bash
git add scripts/figma-tokenize.py tests/test_figma_tokenize.py
git commit -m "feat: implement TokenNamer color naming"
```

---

## Task 6: TokenNamer — sizes

**Files:**
- Modify: `scripts/figma-tokenize.py` — `TokenNamer` のサイズ命名を実装
- Modify: `tests/test_figma_tokenize.py` — サイズ命名テストを追加

- [ ] **Step 1: 失敗するテストを書く**

```python
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_figma_tokenize.py -k "font_size or line_height or radius or spacing" -v
```

Expected: 全件 `FAILED`

- [ ] **Step 3: `TokenNamer` のサイズ命名を実装する（`TokenNamer` クラスに追記）**

```python
    @staticmethod
    def name_font_size(px_key: str) -> str:
        px = int(px_key.rstrip("px"))
        rem = px / 16
        if rem < 0.75:
            return "font-size-xs"
        elif rem < 0.875:
            return "font-size-sm"
        elif rem < 1.125:
            return "font-size-base"
        elif rem < 1.375:
            return "font-size-md"
        elif rem < 1.75:
            return "font-size-lg"
        elif rem < 2.25:
            return "font-size-xl"
        else:
            return "font-size-2xl"

    @staticmethod
    def name_line_height(ratio_key: str) -> str:
        ratio = float(ratio_key)
        if ratio < 1.3:
            return "line-height-tight"
        elif ratio < 1.5:
            return "line-height-snug"
        elif ratio <= 1.7:
            return "line-height-normal"
        else:
            return "line-height-loose"

    @staticmethod
    def name_border_radius(px_key: str) -> str:
        px = int(px_key.rstrip("px"))
        if px <= 3:
            return "radius-xs"
        elif px <= 6:
            return "radius-sm"
        elif px <= 12:
            return "radius-md"
        elif px <= 20:
            return "radius-lg"
        else:
            return "radius-full"

    @staticmethod
    def name_spacing(px_key: str) -> str:
        px = int(px_key.rstrip("px"))
        rem = px / 16
        if rem <= 0.25:
            return "spacing-xs"
        elif rem <= 0.625:
            return "spacing-sm"
        elif rem <= 1.125:
            return "spacing-md"
        elif rem <= 1.75:
            return "spacing-lg"
        elif rem <= 2.5:
            return "spacing-xl"
        else:
            return "spacing-2xl"
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
pytest tests/test_figma_tokenize.py -k "font_size or line_height or radius or spacing" -v
```

Expected: 全件 `PASSED`

- [ ] **Step 5: コミットする**

```bash
git add scripts/figma-tokenize.py tests/test_figma_tokenize.py
git commit -m "feat: implement TokenNamer size naming (font-size, line-height, radius, spacing)"
```

---

## Task 7: TokenBuilder

**Files:**
- Modify: `scripts/figma-tokenize.py` — `TokenBuilder` クラスを実装
- Modify: `tests/test_figma_tokenize.py` — TokenBuilder テストを追加

- [ ] **Step 1: 失敗するテストを書く**

```python
from figma_tokenize import TokenBuilder, VariableResolver, TokenNamer
from unittest.mock import MagicMock


def _make_resolver(mapping: dict) -> VariableResolver:
    resolver = MagicMock(spec=VariableResolver)
    resolver.lookup.side_effect = lambda k: mapping.get(k)
    return resolver


def test_token_builder_filters_by_threshold():
    counts = {
        "colors": {"#1a1a1a": 5, "#cccccc": 2},
        "font-size": {}, "line-height": {}, "border-radius": {}, "spacing": {},
    }
    resolver = _make_resolver({})
    builder = TokenBuilder(counts, resolver, threshold=3)
    result = builder.build()
    assert "color-black" in result["colors"]
    assert len(result["colors"]) == 1  # #cccccc excluded (count=2 < threshold=3)


def test_token_builder_uses_figma_variable_name():
    counts = {
        "colors": {"#e60000": 4},
        "font-size": {}, "line-height": {}, "border-radius": {}, "spacing": {},
    }
    resolver = _make_resolver({"#e60000": "color/main"})
    builder = TokenBuilder(counts, resolver, threshold=3)
    result = builder.build()
    assert "color/main" in result["colors"]
    assert result["colors"]["color/main"]["source"] == "figma_variable"


def test_token_builder_uses_node_name_when_no_variable():
    counts = {
        "colors": {"#1a1a1a": 5},
        "font-size": {}, "line-height": {}, "border-radius": {}, "spacing": {},
    }
    resolver = _make_resolver({})
    builder = TokenBuilder(counts, resolver, threshold=3)
    result = builder.build()
    assert result["colors"]["color-black"]["source"] == "node"


def test_token_builder_resolves_name_collision_with_suffix():
    # Two different hex values that map to same name
    counts = {
        "colors": {"#e60000": 5, "#cc0000": 4},
        "font-size": {}, "line-height": {}, "border-radius": {}, "spacing": {},
    }
    resolver = _make_resolver({})
    builder = TokenBuilder(counts, resolver, threshold=3)
    result = builder.build()
    names = list(result["colors"].keys())
    assert "color-red-01" in names
    assert "color-red-02" in names


def test_token_builder_output_schema():
    counts = {
        "colors": {"#1a1a1a": 5},
        "font-size": {"16px": 4},
        "line-height": {"1.6": 3},
        "border-radius": {"4px": 3},
        "spacing": {"16px": 5},
    }
    resolver = _make_resolver({})
    builder = TokenBuilder(counts, resolver, threshold=3)
    result = builder.build()
    for category in ("colors", "font-size", "line-height", "border-radius", "spacing"):
        assert category in result
    first_color = next(iter(result["colors"].values()))
    assert "value" in first_color
    assert "count" in first_color
    assert "source" in first_color
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_figma_tokenize.py -k "token_builder" -v
```

Expected: 全件 `FAILED`

- [ ] **Step 3: `TokenBuilder` を実装する**

```python
class TokenBuilder:
    _NAMERS = {
        "colors": TokenNamer.name_color,
        "font-size": TokenNamer.name_font_size,
        "line-height": TokenNamer.name_line_height,
        "border-radius": TokenNamer.name_border_radius,
        "spacing": TokenNamer.name_spacing,
    }
    _VALUE_FORMATTERS = {
        "colors": lambda k: k,                          # keep hex as-is
        "font-size": lambda k: f"{int(k.rstrip('px')) / 16}rem",
        "line-height": lambda k: float(k),
        "border-radius": lambda k: k,
        "spacing": lambda k: f"{int(k.rstrip('px')) / 16}rem",
    }

    def __init__(self, counts: dict, resolver: "VariableResolver", threshold: int = 3):
        self._counts = counts
        self._resolver = resolver
        self._threshold = threshold

    def build(self) -> dict:
        result: dict[str, dict] = {cat: {} for cat in self._counts}

        for category, values in self._counts.items():
            # Collect entries above threshold
            above = {k: v for k, v in values.items() if v >= self._threshold}

            # Separate Variables-defined from node-discovered
            named: dict[str, tuple[str, int, str]] = {}  # name -> (value, count, source)

            for raw_key, count in sorted(above.items(), key=lambda x: -x[1]):
                figma_name = self._resolver.lookup(raw_key)
                if figma_name:
                    name = figma_name
                    source = "figma_variable"
                else:
                    name = self._NAMERS[category](raw_key)
                    source = "node"
                formatted_value = self._VALUE_FORMATTERS[category](raw_key)
                named[raw_key] = (name, formatted_value, count, source)

            # Resolve name collisions
            name_counts: dict[str, int] = {}
            for raw_key, (name, value, count, source) in named.items():
                if source == "figma_variable":
                    continue  # Figma Variable names are authoritative — no collision handling
                name_counts[name] = name_counts.get(name, 0) + 1

            collision_idx: dict[str, int] = {}
            for raw_key, (name, value, count, source) in named.items():
                final_name = name
                if source == "node" and name_counts.get(name, 0) > 1:
                    collision_idx[name] = collision_idx.get(name, 0) + 1
                    final_name = f"{name}-{collision_idx[name]:02d}"
                result[category][final_name] = {
                    "value": value,
                    "count": count,
                    "source": source,
                }

        return result
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
pytest tests/test_figma_tokenize.py -k "token_builder" -v
```

Expected: 全件 `PASSED`

- [ ] **Step 5: コミットする**

```bash
git add scripts/figma-tokenize.py tests/test_figma_tokenize.py
git commit -m "feat: implement TokenBuilder with threshold filtering and collision resolution"
```

---

## Task 8: main() と CLI

**Files:**
- Modify: `scripts/figma-tokenize.py` — `main()` とヘルパー関数を実装
- Modify: `tests/test_figma_tokenize.py` — main / CLI テストを追加

- [ ] **Step 1: 失敗するテストを書く**

```python
import subprocess
import json
import tempfile
from pathlib import Path


def test_main_exits_with_error_without_token(monkeypatch):
    monkeypatch.delenv("FIGMA_TOKEN", raising=False)
    result = subprocess.run(
        ["python3", "scripts/figma-tokenize.py", "--file-id", "abc", "--output", "/tmp/out.json"],
        capture_output=True, text=True, cwd=str(Path(__file__).parent.parent)
    )
    assert result.returncode == 1
    assert "FIGMA_TOKEN" in result.stderr + result.stdout


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
    """output dir が存在しない場合は自動作成される"""
    from unittest.mock import patch, MagicMock
    monkeypatch.setenv("FIGMA_TOKEN", "fake-token")

    output_path = tmp_path / "new_dir" / "tokens.json"

    with patch("figma_tokenize.FigmaClient.get") as mock_get:
        mock_get.side_effect = [
            # GET /files/{id}?depth=2 → ページ一覧
            {"document": {"children": [{"id": "p1", "name": "Components"}]}},
            # GET /files/{id}/variables/local → 403 fallback
            (_ for _ in ()).throw(requests.HTTPError(response=MagicMock(status_code=403))),
            # GET /files/{id}/nodes → 空ノード
            {"nodes": {"p1": {"document": {"id": "p1", "type": "FRAME", "children": []}}}},
        ]
        monkeypatch.setattr("sys.argv", [
            "figma-tokenize.py",
            "--file-id", "fake-file",
            "--output", str(output_path),
        ])
        import figma_tokenize as ft
        ft.main()

    assert output_path.exists()
    data = json.loads(output_path.read_text())
    assert "meta" in data
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_figma_tokenize.py -k "main" -v
```

Expected: 全件 `FAILED`

- [ ] **Step 3: `main()` とヘルパー関数を実装する**

```python
def _find_page_id(client: FigmaClient, file_id: str, page_name: str) -> str:
    data = client.get(f"/files/{file_id}", params={"depth": "2"})
    pages = data["document"]["children"]
    for page in pages:
        if page["name"] == page_name:
            return page["id"]
    raise SystemExit(
        f"Error: Page '{page_name}' not found in Figma file. "
        f"Use --page to specify the correct page name."
    )


def main():
    parser = argparse.ArgumentParser(description="Extract design tokens from a Figma file.")
    parser.add_argument("--file-id", required=True, help="Figma file ID")
    parser.add_argument("--output", default=None, help="Output JSON path (default: stdout)")
    parser.add_argument("--page", default="Components", help="Page name to scan (default: Components)")
    parser.add_argument("--threshold", type=int, default=3, help="Min occurrences to include (default: 3)")
    args = parser.parse_args()

    client = FigmaClient()
    page_id = _find_page_id(client, args.file_id, args.page)

    resolver = VariableResolver(client, args.file_id)
    resolver.load()

    scanner = NodeScanner(client, args.file_id, page_id)
    scanner.scan()

    builder = TokenBuilder(scanner.counts, resolver, threshold=args.threshold)
    token_data = builder.build()

    output = {
        "meta": {
            "file_id": args.file_id,
            "page": args.page,
            "threshold": args.threshold,
            "generated_at": datetime.utcnow().isoformat(),
        },
        **token_data,
    }

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))
        print(f"Tokens written to {out_path}", file=sys.stderr)
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
pytest tests/test_figma_tokenize.py -k "main" -v
```

Expected: 全件 `PASSED`

- [ ] **Step 5: 全テストを通す**

```bash
pytest tests/test_figma_tokenize.py -v
```

Expected: 全件 `PASSED`

- [ ] **Step 6: コミットする**

```bash
git add scripts/figma-tokenize.py tests/test_figma_tokenize.py
git commit -m "feat: implement main() with CLI and file output"
```

---

## Task 9: グローバルインストールと最終確認

**Files:**
- Create: `~/.claude/scripts/figma-tokenize.py` — グローバル配置

- [ ] **Step 1: `~/.claude/scripts/` ディレクトリを作成してシンボリックリンクを張る**

```bash
mkdir -p ~/.claude/scripts
ln -s ~/Workspace/component-skills/scripts/figma-tokenize.py ~/.claude/scripts/figma-tokenize.py
ls -la ~/.claude/scripts/figma-tokenize.py
```

Expected: symlink が表示される

- [ ] **Step 2: グローバルパスから --help が動くことを確認する**

```bash
python3 ~/.claude/scripts/figma-tokenize.py --help
```

Expected: usage が表示される

- [ ] **Step 3: `figma-tokenize` SKILL.md のスクリプト解決パスを確認する**

```bash
cat ~/.claude/skills/figma-tokenize/SKILL.md | grep -A 10 "Step 1"
```

グローバルパス `~/.claude/scripts/figma-tokenize.py` がフォールバックとして記載されていることを確認する。

- [ ] **Step 4: コミットして push する**

```bash
cd ~/Workspace/component-skills
git add scripts/figma-tokenize.py
git commit -m "feat: add figma-tokenize.py implementation"
git push origin main
```

Expected: `main` へ push 成功
