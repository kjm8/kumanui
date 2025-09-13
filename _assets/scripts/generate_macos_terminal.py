#!/usr/bin/env python3
"""
Generate a macOS Terminal .terminal profile from tokens/colors.yaml

Requirements:
  - PyYAML:   pip3 install pyyaml
  - PyObjC:   pip3 install pyobjc

Usage:
  python3 _assets/scripts/generate_macos_terminal.py dist/macos-terminal/Kumanui.terminal
  # or write to stdout
  python3 _assets/scripts/generate_macos_terminal.py -
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import plistlib

try:
    import yaml  # type: ignore
except Exception:
    print("ERROR: PyYAML not installed. Install with: pip3 install pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    from AppKit import NSColor  # type: ignore
    from Foundation import NSKeyedArchiver  # type: ignore
except Exception:
    print("ERROR: PyObjC not installed. Install with: pip3 install pyobjc", file=sys.stderr)
    sys.exit(1)


ROOT = Path(__file__).resolve().parents[2]
TOKENS_PATH = ROOT / "tokens/colors.yaml"


def load_tokens(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_ref(tokens: dict, ref: str) -> dict | None:
    if not (ref.startswith('{') and ref.endswith('}')):
        return None
    parts = ref[1:-1].split('.')
    cur: object = tokens
    for key in parts:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur if isinstance(cur, dict) else None


def color_entry_to_hex(tokens: dict, entry: dict) -> str:
    val = entry.get('value')
    if isinstance(val, str):
        if val.startswith('#'):
            return val.upper()
        refd = resolve_ref(tokens, val)
        if refd and isinstance(refd.get('value'), str) and refd['value'].startswith('#'):
            return refd['value'].upper()
    raise ValueError(f"Unsupported color value: {val}")


def hex_to_rgb01(hex_str: str) -> tuple[float, float, float]:
    s = hex_str.strip().lstrip('#')
    if len(s) not in (6, 8):
        raise ValueError(f"Unsupported hex length: {hex_str}")
    r = int(s[0:2], 16) / 255.0
    g = int(s[2:4], 16) / 255.0
    b = int(s[4:6], 16) / 255.0
    return (r, g, b)


def archive_color_rgb(r: float, g: float, b: float, a: float = 1.0) -> bytes:
    """Return NSKeyedArchiver bytes for an NSColor in calibrated RGB space."""
    color = NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)
    # Use non-secure coding for broader compatibility with Terminal imports
    data = NSKeyedArchiver.archivedDataWithRootObject_(color)
    # Convert to Python bytes for plistlib.Data
    return bytes(data)


def build_profile(tokens: dict) -> dict:
    term = tokens['semantics']['terminal']

    # Core colors
    bg_hex = color_entry_to_hex(tokens, term['background'])
    fg_hex = color_entry_to_hex(tokens, term['text'])
    bold_hex = color_entry_to_hex(tokens, term['boldText'])
    sel_hex = color_entry_to_hex(tokens, term['selection'])
    cur_hex = color_entry_to_hex(tokens, term['cursor'])

    # ANSI standard and bright
    ansi_std = term['ansi']['standard']
    ansi_bri = term['ansi']['bright']

    def d(hexv: str) -> bytes:
        r, g, b = hex_to_rgb01(hexv)
        # plistlib will serialize bytes as <data> (base64) in XML plists
        return archive_color_rgb(r, g, b, 1.0)

    profile: dict[str, object] = {
        "name": "Kumanui",
        # Core color keys
        "BackgroundColor": d(bg_hex),
        "TextColor": d(fg_hex),
        "TextBoldColor": d(bold_hex),
        "SelectionColor": d(sel_hex),  # Terminal doesn't support alpha; using opaque
        "CursorColor": d(cur_hex),
        # Set cursor text to background for contrast
        "CursorTextColor": d(bg_hex),
        # ANSI standard (0-7)
        "ANSIBlackColor": d(color_entry_to_hex(tokens, ansi_std['black'])),
        "ANSIRedColor": d(color_entry_to_hex(tokens, ansi_std['red'])),
        "ANSIGreenColor": d(color_entry_to_hex(tokens, ansi_std['green'])),
        "ANSIYellowColor": d(color_entry_to_hex(tokens, ansi_std['yellow'])),
        "ANSIBlueColor": d(color_entry_to_hex(tokens, ansi_std['blue'])),
        "ANSIMagentaColor": d(color_entry_to_hex(tokens, ansi_std['magenta'])),
        "ANSICyanColor": d(color_entry_to_hex(tokens, ansi_std['cyan'])),
        "ANSIWhiteColor": d(color_entry_to_hex(tokens, ansi_std['white'])),
        # ANSI bright (8-15)
        "ANSIBrightBlackColor": d(color_entry_to_hex(tokens, ansi_bri['black'])),
        "ANSIBrightRedColor": d(color_entry_to_hex(tokens, ansi_bri['red'])),
        "ANSIBrightGreenColor": d(color_entry_to_hex(tokens, ansi_bri['green'])),
        "ANSIBrightYellowColor": d(color_entry_to_hex(tokens, ansi_bri['yellow'])),
        "ANSIBrightBlueColor": d(color_entry_to_hex(tokens, ansi_bri['blue'])),
        "ANSIBrightMagentaColor": d(color_entry_to_hex(tokens, ansi_bri['magenta'])),
        "ANSIBrightCyanColor": d(color_entry_to_hex(tokens, ansi_bri['cyan'])),
        "ANSIBrightWhiteColor": d(color_entry_to_hex(tokens, ansi_bri['white'])),
        # Mark type so Terminal recognizes it as a profile
        "type": "Window Settings",
    }
    return profile


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate macOS Terminal .terminal profile from tokens/colors.yaml")
    ap.add_argument("out", help="Output path (.terminal) or '-' for stdout")
    args = ap.parse_args()

    tokens = load_tokens(TOKENS_PATH)
    profile = build_profile(tokens)

    if args.out == "-":
        plistlib.dump(profile, sys.stdout.buffer, fmt=plistlib.FMT_XML)
    else:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("wb") as f:
            plistlib.dump(profile, f, fmt=plistlib.FMT_XML)
        print(f"Wrote Terminal profile: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
