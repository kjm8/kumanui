#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
TOKENS_PATH = ROOT / 'tokens/colors.yaml'
OUT_DIR = ROOT / 'dist/css'
OUT_FILE = OUT_DIR / 'kumanui.css'


def resolve_ref(tokens: dict, ref: str) -> dict | None:
    if not (isinstance(ref, str) and ref.startswith('{') and ref.endswith('}')):
        return None
    cur: object = tokens
    for key in ref[1:-1].split('.'):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur if isinstance(cur, dict) else None


def hex_to_rgb(hexv: str) -> tuple[int, int, int]:
    s = hexv.lstrip('#')
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def token_to_css_color(entry: dict, tokens: dict) -> str:
    val = entry.get('value')
    alpha = entry.get('alpha')
    hexv: str | None = None
    if isinstance(val, str) and val.startswith('#'):
        hexv = val.upper()
    elif isinstance(val, str) and val.startswith('{'):
        refd = resolve_ref(tokens, val)
        if refd and isinstance(refd.get('value'), str) and refd['value'].startswith('#'):
            hexv = refd['value'].upper()
    if hexv is None:
        raise ValueError(f"Unsupported color token value: {val}")
    if alpha is not None:
        r, g, b = hex_to_rgb(hexv)
        return f"rgba({r}, {g}, {b}, {float(alpha)})"
    return hexv


def generate_css(tokens: dict) -> str:
    lines: list[str] = []
    lines.append("/* Generated from tokens/colors.yaml — do not edit directly. */")
    lines.append(":root {")

    # Palette variables
    palette = tokens.get('palette', {})
    order = ['black', 'white', 'red', 'green', 'blue', 'yellow', 'magenta', 'cyan']
    tiers = ['base', 'light', 'dark']
    for hue in order:
        group = palette.get(hue, {})
        if not isinstance(group, dict):
            continue
        for tier in tiers:
            entry = group.get(tier)
            if not isinstance(entry, dict):
                continue
            val = entry.get('value')
            if isinstance(val, str) and val.startswith('#'):
                lines.append(f"  --kumanui-{hue}-{tier}: {val.upper()};")

    # Note: semantic variables omitted by request

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    tokens = yaml.safe_load(TOKENS_PATH.read_text(encoding='utf-8'))
    css = generate_css(tokens)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(css, encoding='utf-8')
    print(f"Wrote {OUT_FILE}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
