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
from pathlib import Path

import requests


def _rgba_to_hex(r: float, g: float, b: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        round(r * 255), round(g * 255), round(b * 255)
    )


def _to_color_key(fill: dict) -> str:
    """Return hex for opaque fills, rgba(...) string for semi-transparent fills."""
    c = fill["color"]
    fill_opacity = fill.get("opacity", 1.0)
    color_alpha = c.get("a", 1.0)
    alpha = round(fill_opacity * color_alpha, 2)
    if alpha >= 0.99:
        return _rgba_to_hex(c["r"], c["g"], c["b"])
    r = round(c["r"] * 255)
    g = round(c["g"] * 255)
    b = round(c["b"] * 255)
    return f"rgba({r}, {g}, {b}, {alpha})"


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
            "letter-spacing": {},
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
        # Colors from SOLID fills (opaque → hex, semi-transparent → rgba)
        for fill in node.get("fills", []):
            if fill.get("type") == "SOLID" and fill.get("visible", True):
                color_key = _to_color_key(fill)
                self.counts["colors"][color_key] = (
                    self.counts["colors"].get(color_key, 0) + 1
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

        # letter-spacing (PERCENT unit only, exclude 0)
        if "letterSpacing" in style and style.get("letterSpacingUnit") == "PERCENT":
            ls = style["letterSpacing"]
            if ls != 0:
                key = f"{round(ls, 2)}%"
                self.counts["letter-spacing"][key] = (
                    self.counts["letter-spacing"].get(key, 0) + 1
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
    def _name_from_hex(hex_value: str) -> str:
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
    def name_color(key: str) -> str:
        if key.startswith("rgba("):
            parts = key[5:-1].split(",")
            r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
            alpha_pct = int(round(float(parts[3]) * 100))
            hex_val = "#{:02x}{:02x}{:02x}".format(r, g, b)
            base = TokenNamer._name_from_hex(hex_val)
            return f"{base}-a{alpha_pct}"
        return TokenNamer._name_from_hex(key)

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

    @staticmethod
    def name_letter_spacing(pct_key: str) -> str:
        pct = float(pct_key.rstrip("%"))
        if pct < 0:
            return "letter-spacing-tight"
        elif pct < 4:
            return "letter-spacing-normal"
        elif pct < 8:
            return "letter-spacing-wide"
        else:
            return "letter-spacing-wider"


class TokenBuilder:
    _NAMERS = {
        "colors": TokenNamer.name_color,
        "font-size": TokenNamer.name_font_size,
        "line-height": TokenNamer.name_line_height,
        "letter-spacing": TokenNamer.name_letter_spacing,
        "border-radius": TokenNamer.name_border_radius,
        "spacing": TokenNamer.name_spacing,
    }
    _VALUE_FORMATTERS = {
        "colors": lambda k: k,
        "font-size": lambda k: f"{int(k.rstrip('px')) / 16}rem",
        "line-height": lambda k: float(k),
        "letter-spacing": lambda k: k,
        "border-radius": lambda k: k,
        "spacing": lambda k: f"{int(k.rstrip('px')) / 16}rem",
    }

    def __init__(self, counts: dict, resolver, threshold: int = 3):
        self._counts = counts
        self._resolver = resolver
        self._threshold = threshold

    def build(self) -> dict:
        result = {cat: {} for cat in self._counts}

        for category, values in self._counts.items():
            above = {k: v for k, v in values.items() if v >= self._threshold}

            # 各値に名前を割り当てる
            entries = []  # (raw_key, name, formatted_value, count, source)
            for raw_key, count in sorted(above.items(), key=lambda x: -x[1]):
                figma_name = self._resolver.lookup(raw_key)
                if figma_name:
                    name = figma_name
                    source = "figma_variable"
                else:
                    name = self._NAMERS[category](raw_key)
                    source = "node"
                formatted_value = self._VALUE_FORMATTERS[category](raw_key)
                entries.append((raw_key, name, formatted_value, count, source))

            # 衝突カウント（node のみ対象）
            node_name_counts: dict = {}
            for _, name, _, _, source in entries:
                if source == "node":
                    node_name_counts[name] = node_name_counts.get(name, 0) + 1

            collision_idx: dict = {}
            for raw_key, name, value, count, source in entries:
                if source == "node" and node_name_counts.get(name, 0) > 1:
                    collision_idx[name] = collision_idx.get(name, 0) + 1
                    final_name = f"{name}-{collision_idx[name]:02d}"
                else:
                    final_name = name
                result[category][final_name] = {
                    "value": value,
                    "count": count,
                    "source": source,
                }

        return result


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


if __name__ == "__main__":
    main()
