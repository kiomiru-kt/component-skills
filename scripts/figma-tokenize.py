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


def _rgba_to_hex(r: float, g: float, b: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        round(r * 255), round(g * 255), round(b * 255)
    )


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
            first_value = next(iter(values.values()))

            if resolved_type == "COLOR" and isinstance(first_value, dict):
                hex_key = _rgba_to_hex(
                    first_value["r"], first_value["g"], first_value["b"]
                )
                self._map[hex_key] = name

            elif resolved_type == "FLOAT" and isinstance(first_value, (int, float)):
                px_key = f"{int(first_value)}px"
                self._map[px_key] = name

    def lookup(self, key: str):
        return self._map.get(key)


class NodeScanner:
    def __init__(self, client: "FigmaClient", file_id: str, page_id: str):
        self._client = client
        self._file_id = file_id
        self._page_id = page_id
        self.counts: dict = {
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
        # Colors from SOLID fills only
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

        # Spacing: padding fields + itemSpacing
        for field in ("paddingLeft", "paddingRight", "paddingTop", "paddingBottom", "itemSpacing"):
            val = node.get(field)
            if val is not None and val > 0:
                key = f"{int(val)}px"
                self.counts["spacing"][key] = self.counts["spacing"].get(key, 0) + 1


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

    @staticmethod
    def name_font_size(px_key: str) -> str:
        pass

    @staticmethod
    def name_line_height(ratio_key: str) -> str:
        pass

    @staticmethod
    def name_border_radius(px_key: str) -> str:
        pass

    @staticmethod
    def name_spacing(px_key: str) -> str:
        pass


class TokenBuilder:
    pass


def main():
    pass


if __name__ == "__main__":
    main()
