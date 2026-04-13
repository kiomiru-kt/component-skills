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
    pass


class TokenNamer:
    pass


class TokenBuilder:
    pass


def main():
    pass


if __name__ == "__main__":
    main()
