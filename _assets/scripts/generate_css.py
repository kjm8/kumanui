#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import yaml

from token_utils import color_entry_to_hex, hex_to_rgb

ROOT = Path(__file__).resolve().parents[2]
TOKENS_PATH = ROOT / 'tokens/colors.yaml'
OUT_DIR = ROOT / 'dist/css'
OUT_FILE = OUT_DIR / 'kumanui.css'


def token_to_css_color(entry: dict, tokens: dict) -> str:
    hexv = color_entry_to_hex(tokens, entry)
    alpha = entry.get('alpha')
    if alpha is not None:
        r, g, b = hex_to_rgb(hexv)
        return f"rgba({r}, {g}, {b}, {float(alpha)})"
    return hexv


def semantic_entry_to_css_value(entry: dict, tokens: dict) -> str:
    """Prefer referencing palette CSS variables when possible.

    - If entry.value is a palette ref (e.g., {palette.cyan.dark}), emit
      var(--kumanui-cyan-dark) or a color-mix with transparent when alpha exists.
    - Otherwise, fall back to concrete color via token_to_css_color.
    """
    val = entry.get('value')
    alpha = entry.get('alpha')
    if isinstance(val, str) and val.startswith('{') and val.endswith('}'):
        parts = val[1:-1].split('.')
        if len(parts) == 3 and parts[0] == 'palette':
            hue, tier = parts[1], parts[2]
            var_name = f"--kumanui-{hue}-{tier}"
            if alpha is not None:
                try:
                    pct = float(alpha) * 100.0
                except Exception:
                    pct = 100.0
                # Use color-mix to apply alpha relative to transparent
                # Keep 2 decimal precision, strip trailing zeros
                pct_str = (f"{pct:.2f}".rstrip('0').rstrip('.')) + '%'
                return f"color-mix(in srgb, var({var_name}) {pct_str}, transparent)"
            return f"var({var_name})"
    # Fallback to resolved color (hex or rgba)
    return token_to_css_color(entry, tokens)


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

    lines.append("}")
    lines.append("")

    # Web semantics (light/dark)
    web = tokens.get('semantics', {}).get('web', {})

    def collect_web_properties(mode: str) -> list[tuple[str, str]]:
        group = web.get(mode)
        if not isinstance(group, dict):
            return []

        properties: list[tuple[str, str]] = []

        flat_keys = [
            'background', 'surface', 'text', 'mutedText', 'heading',
            'link', 'linkHover', 'border', 'accent', 'selection',
        ]
        for key in flat_keys:
            entry = group.get(key)
            if isinstance(entry, dict):
                css_val = semantic_entry_to_css_value(entry, tokens)
                var_name = key.replace('mutedText', 'muted-text').replace('linkHover', 'link-hover')
                properties.append((f"--kumanui-web-{var_name}", css_val))

        code = group.get('code')
        if isinstance(code, dict):
            for sub in ('bg', 'text'):
                entry = code.get(sub)
                if isinstance(entry, dict):
                    css_val = semantic_entry_to_css_value(entry, tokens)
                    properties.append((f"--kumanui-web-code-{sub}", css_val))

        return properties

    def add_web_block(mode: str, selector: str, *, include_color_scheme: bool) -> None:
        properties = collect_web_properties(mode)
        if not properties:
            return
        lines.append(f"{selector} {{")
        if include_color_scheme:
            scheme = 'dark' if mode == 'dark' else 'light'
            lines.append(f"  color-scheme: {scheme};")
        for name, value in properties:
            lines.append(f"  {name}: {value};")
        lines.append("}")
        lines.append("")

    # Emit variables for light and dark modes.
    # Attach to data-theme attribute selectors for easy toggling in apps.
    add_web_block('light', ":root, [data-theme='light']", include_color_scheme=True)
    add_web_block('dark',  "[data-theme='dark']", include_color_scheme=True)

    # System preference fallback when no explicit theme is set.
    dark_properties = collect_web_properties('dark')
    if dark_properties:
        lines.append("@media (prefers-color-scheme: dark) {")
        lines.append("  :root:not([data-theme]) {")
        lines.append("    color-scheme: dark;")
        for name, value in dark_properties:
            lines.append(f"    {name}: {value};")
        lines.append("  }")
        lines.append("}")

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
