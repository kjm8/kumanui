#!/usr/bin/env python3
"""
Generate README color sections from tokens/colors.yaml

Requires: PyYAML (`pip install pyyaml`)

Usage:
  python3 _assets/scripts/generate_readme.py
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception as e:
    print("ERROR: PyYAML not installed. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# Repo root (this file lives in _assets/scripts/)
ROOT = Path(__file__).resolve().parents[2]
TOKENS_PATH = ROOT / "tokens/colors.yaml"
README_PATH = ROOT / "README.md"
SWATCH_DIR = ROOT / "_assets/swatches"


def load_tokens(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    s = hex_str.strip().lstrip('#')
    if len(s) not in (6, 8):
        raise ValueError(f"Unsupported hex length: {hex_str}")
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return r, g, b


def rgb_to_hsl(r: int, g: int, b: int) -> tuple[int, int, int]:
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    mx, mn = max(rf, gf, bf), min(rf, gf, bf)
    l = (mx + mn) / 2.0
    if mx == mn:
        h = s = 0.0
    else:
        d = mx - mn
        s = d / (2.0 - mx - mn) if l > 0.5 else d / (mx + mn)
        if mx == rf:
            h = (gf - bf) / d + (6 if gf < bf else 0)
        elif mx == gf:
            h = (bf - rf) / d + 2
        else:
            h = (rf - gf) / d + 4
        h /= 6.0
    return round(h * 360), round(s * 100), round(l * 100)


def ensure_swatch(hex_str: str) -> None:
    s = hex_str.upper().lstrip('#')
    SWATCH_DIR.mkdir(parents=True, exist_ok=True)
    svg_path = SWATCH_DIR / f"{s}.svg"
    if svg_path.exists():
        return
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12"><rect width="12" height="12" fill="#{s}"/></svg>'
    svg_path.write_text(svg, encoding='utf-8')


def resolve_ref(tokens: dict, ref: str) -> dict | None:
    # Supports strings like "{palette.brand.KumaYellow}"
    if not (ref.startswith('{') and ref.endswith('}')):
        return None
    path = ref[1:-1].split('.')
    cur: object = tokens
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur if isinstance(cur, dict) else None


def color_entry_to_hex(tokens: dict, entry: dict) -> str:
    """Return hex for a color token entry. Accepts either literal hex value or a reference to another token."""
    val = entry.get('value')
    if isinstance(val, str):
        if val.startswith('#'):
            return val.upper()
        refd = resolve_ref(tokens, val)
        if refd and isinstance(refd.get('value'), str) and refd['value'].startswith('#'):
            return refd['value'].upper()
    raise ValueError(f"Unsupported color value: {val}")


# Primary palette block has been removed; brand colors are now consolidated


def render_neutrals(tokens: dict) -> str:
    rows = [
        "| 🎨 | Tier | Name | Hex | RGB | HSL |",
        "|---|------|------|-----|-----|-----|",
    ]
    mapping = [
        ("Base", "Black", tokens['palette']['black']['base']),
        ("Base", "White", tokens['palette']['white']['base']),
        ("Light", "Black", tokens['palette']['black']['light']),
        ("Light", "White", tokens['palette']['white']['light']),
        ("Dark", "Black", tokens['palette']['black']['dark']),
        ("Dark", "White", tokens['palette']['white']['dark']),
    ]
    for tier, name, entry in mapping:
        hexv = entry['value'].upper()
        r, g, b = hex_to_rgb(hexv)
        h, s, l = rgb_to_hsl(r, g, b)
        ensure_swatch(hexv)
        rows.append(
            f"| <img src=\"_assets/swatches/{hexv[1:]}.svg\" width=\"12\" height=\"12\" alt=\"{hexv}\" /> | {tier:<5} | {name:<5} | `{hexv}` | {r}, {g}, {b} | {h}°, {s}%, {l}% |"
        )
    return "\n".join(rows)


def render_tiers(tokens: dict) -> str:
    rows = [
        "| 🎨 | Tier | Hue | Hex | RGB | HSL |",
        "|---|------|-----|-----|-----|-----|",
    ]
    hues = ['black', 'white', 'red', 'green', 'blue', 'magenta', 'cyan', 'yellow']
    tiers = [('Base', 'base'), ('Light', 'light'), ('Dark', 'dark')]
    for tier_label, tier_key in tiers:
        for hue in hues:
            entry = tokens['palette'][hue][tier_key]
            hexv = entry['value'].upper()
            r, g, b = hex_to_rgb(hexv)
            h, s, l = rgb_to_hsl(r, g, b)
            ensure_swatch(hexv)
            rows.append(
                f"| <img src=\"_assets/swatches/{hexv[1:]}.svg\" width=\"12\" height=\"12\" alt=\"{hexv}\" /> | {tier_label:<5} | {hue.capitalize():<8} | `{hexv}` | {r}, {g}, {b} | {h}°, {s}%, {l}% |"
            )
    return "\n".join(rows)


def render_terminal(tokens: dict) -> str:
    term = tokens['semantics']['terminal']

    def name_from_entry(entry: dict, fallback: str) -> str:
        val = entry.get('value', '')
        if isinstance(val, str) and val.startswith('{'):
            parts = val.strip('{}').split('.')
            # palette.<hue>.<tier> -> "Tier Hue"
            if len(parts) >= 3 and parts[0] == 'palette' and parts[2] in ('base', 'light', 'dark'):
                tier_map = {'base': 'Base', 'light': 'Light', 'dark': 'Dark'}
                hue = parts[1].capitalize()
                tier = tier_map.get(parts[2], parts[2].capitalize())
                return f"{tier} {hue}"
            # palette.brand.<Name>
            if len(parts) >= 3 and parts[0] == 'palette' and parts[1] == 'brand':
                return parts[-1]
        return fallback

    bg_hex = color_entry_to_hex(tokens, term['background'])
    fg_hex = color_entry_to_hex(tokens, term['text'])
    bold_hex = color_entry_to_hex(tokens, term['boldText'])

    bg_name = name_from_entry(term['background'], 'Background')
    fg_name = name_from_entry(term['text'], 'Text')

    # selection/cursor: keep color name + base hex + opacity from alpha
    def format_named_alpha(entry: dict) -> tuple[str, str, int]:
        val = entry.get('value', '')
        alpha = entry.get('alpha', 1)
        name = ''
        base_hex = ''
        if isinstance(val, str) and val.startswith('{'):
            # derive a friendly name from the reference path
            parts = val.strip('{}').split('.')
            # palette.<hue>.<tier> -> "Base/Light/Dark Hue"
            if len(parts) >= 3 and parts[0] == 'palette' and parts[2] in ('base', 'light', 'dark'):
                tier_map = {'base': 'Base', 'light': 'Light', 'dark': 'Dark'}
                hue = parts[1].capitalize()
                tier = tier_map.get(parts[2], parts[2].capitalize())
                name = f"{tier} {hue}"
            else:
                # fallback to last segment
                name = parts[-1]
            refd = resolve_ref(tokens, val)
            if refd:
                base_hex = refd['value'].upper()
        return name or 'Color', base_hex or '#000000', int(round(float(alpha) * 100))

    sel_name, sel_hex, sel_op = format_named_alpha(term['selection'])
    cur_name, cur_hex, cur_op = format_named_alpha(term['cursor'])

    lines = [
        f"- **Background**: {bg_name} `{bg_hex}`",
        f"- **Text**: {fg_name} `{fg_hex}`",
        f"- **Bold Text**: Light White `{bold_hex}`",
        f"- **Selection**: {sel_name} `{sel_hex}` at {sel_op}% opacity",
        f"- **Cursor**: {cur_name} `{cur_hex}` at {cur_op}% opacity",
    ]
    # Include ANSI note inline under Terminal section
    lines.append("- **ANSI Colors**: Base-tier colors for standard ANSI colors (0-7), and light-tier colors for bright ANSI colors (8-15)")
    return "\n".join(lines)


# ANSI note is included in render_terminal(); no separate renderer needed.


def replace_block(text: str, begin: str, end: str, payload: str) -> str:
    pattern = re.compile(rf"(<!--\s*{re.escape(begin)}\s*-->)(.*?)(<!--\s*{re.escape(end)}\s*-->)", re.DOTALL)
    repl = f"<!-- {begin} -->\n{payload}\n<!-- {end} -->"
    if not pattern.search(text):
        # If markers are missing, append at the end as a fallback
        return text + "\n\n" + repl + "\n"
    return pattern.sub(repl, text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate README color sections from tokens/colors.yaml")
    parser.add_argument("--check", action="store_true", help="Only check if README is up to date; exit 1 if changes are needed")
    args = parser.parse_args()

    tokens = load_tokens(TOKENS_PATH)

    tiers_md = render_tiers(tokens)
    terminal_md = render_terminal(tokens)

    readme = README_PATH.read_text(encoding='utf-8')
    readme = replace_block(readme, 'BEGIN:COLORS (generated from tokens/colors.yaml)', 'END:COLORS', tiers_md)
    readme = replace_block(readme, 'BEGIN:TERMINAL (generated from tokens/colors.yaml)', 'END:TERMINAL', terminal_md)

    current = README_PATH.read_text(encoding='utf-8')
    if args.check:
        if current == readme:
            print("README is up to date with tokens/colors.yaml")
            return 0
        else:
            print("README is out of date with tokens/colors.yaml", file=sys.stderr)
            return 1
    else:
        README_PATH.write_text(readme, encoding='utf-8')
        print("README color sections regenerated from tokens/colors.yaml")
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
