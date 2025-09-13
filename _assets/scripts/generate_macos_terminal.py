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
    from AppKit import NSColor, NSFont  # type: ignore
    from Foundation import NSKeyedArchiver, NSURL  # type: ignore
    # Optional: CoreText for registering app-bundled fonts at runtime
    try:
        from CoreText import (
            CTFontManagerRegisterFontsForURL,
            kCTFontManagerScopeProcess,
        )  # type: ignore
    except Exception:
        CTFontManagerRegisterFontsForURL = None  # type: ignore
        kCTFontManagerScopeProcess = None  # type: ignore
except Exception:
    print("ERROR: PyObjC not installed. Install with: pip3 install pyobjc", file=sys.stderr)
    sys.exit(1)


ROOT = Path(__file__).resolve().parents[2]
TOKENS_PATH = ROOT / "tokens/colors.yaml"

# Embedded default font configuration for simplicity
DEFAULT_FONT_NAME = "SF Mono Terminal"
DEFAULT_FONT_SIZE = 12.0


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


def color_entry_to_rgba(tokens: dict, entry: dict) -> tuple[float, float, float, float]:
    """Resolve a color token entry to RGBA floats in [0,1].

    Honors an `alpha` on the entry itself; if absent, will inherit from a
    referenced token if present, otherwise defaults to 1.0.
    """
    a: float = float(entry.get('alpha', 1.0))
    hex_source = entry.get('value')
    if isinstance(hex_source, str) and not hex_source.startswith('#'):
        refd = resolve_ref(tokens, hex_source)
        if refd:
            if 'alpha' in refd and 'alpha' not in entry:
                try:
                    a = float(refd['alpha'])
                except Exception:
                    a = 1.0
            hex_source = refd.get('value', hex_source)
    if isinstance(hex_source, str) and hex_source.startswith('#'):
        r, g, b = hex_to_rgb01(hex_source)
        return (r, g, b, a)
    raise ValueError(f"Unsupported color value: {hex_source}")


def hex_to_rgb01(hex_str: str) -> tuple[float, float, float]:
    s = hex_str.strip().lstrip('#')
    if len(s) not in (6, 8):
        raise ValueError(f"Unsupported hex length: {hex_str}")
    r = int(s[0:2], 16) / 255.0
    g = int(s[2:4], 16) / 255.0
    b = int(s[4:6], 16) / 255.0
    return (r, g, b)


def archive_color_rgb(r: float, g: float, b: float, a: float = 1.0) -> bytes:
    """Return NSKeyedArchiver bytes for an NSColor using sRGB color space.

    Falls back to calibrated RGB if sRGB initializer is unavailable.
    """
    # Prefer sRGB to match token color space and ensure consistent rendering
    if hasattr(NSColor, 'colorWithSRGBRed_green_blue_alpha_'):
        color = NSColor.colorWithSRGBRed_green_blue_alpha_(r, g, b, a)
    else:
        # Fallback for older macOS versions
        color = NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)
    # Use non-secure coding for broader compatibility with Terminal imports
    data = NSKeyedArchiver.archivedDataWithRootObject_(color)
    # Convert to Python bytes for plistlib.Data
    return bytes(data)


def _register_sf_mono_terminal_if_needed(requested_name: str) -> None:
    """Attempt to register Terminal's bundled SF Mono font for this process.

    Terminal.app bundles its own SF Mono fonts that are not globally installed.
    Registering them at process-scope allows NSFont lookups to succeed, so we
    can embed the font in the .terminal profile.
    """
    # Only attempt if CoreText is available and the requested name looks like SF Mono
    if CTFontManagerRegisterFontsForURL is None:
        return
    lower = requested_name.lower()
    if not ("sf mono" in lower or "sfmono" in lower):
        return
    font_dir = "/System/Applications/Utilities/Terminal.app/Contents/Resources/Fonts"
    # The essential faces for Terminal rendering; register if present
    candidates = [
        "SFMono-Terminal.ttf",
        "SFMonoItalic-Terminal.ttf",
    ]
    for fname in candidates:
        fpath = Path(font_dir) / fname
        if not fpath.exists():
            continue
        try:
            url = NSURL.fileURLWithPath_(str(fpath))
            # Ignore errors; if registration fails we'll fall back later
            CTFontManagerRegisterFontsForURL(url, kCTFontManagerScopeProcess, None)
        except Exception:
            # Silently ignore; fallback will handle missing fonts
            pass


def archive_font(name: str, size: float) -> bytes:
    """Return NSKeyedArchiver bytes for an NSFont with given name and size.

    Falls back to Menlo if the requested font cannot be created.
    """
    # First try the requested name directly
    font = NSFont.fontWithName_size_(name, float(size))
    # If not found, and the name suggests SF Mono, try registering Terminal's bundled fonts
    if font is None:
        _register_sf_mono_terminal_if_needed(name)
        font = NSFont.fontWithName_size_(name, float(size))
    # Try common aliases/PostScript names for SF Mono if initial lookup fails
    if font is None and name.lower().startswith("sf mono"):
        for alt in ("SF Mono", "SFMono-Regular"):
            font = NSFont.fontWithName_size_(alt, float(size))
            if font is not None:
                break
    if font is None:
        # Fallback to a common monospaced font and warn
        print(f"WARN: Font '{name}' not found. Falling back to Menlo {size}pt.", file=sys.stderr)
        font = NSFont.fontWithName_size_("Menlo", float(size))
    data = NSKeyedArchiver.archivedDataWithRootObject_(font)
    return bytes(data)


def build_profile(tokens: dict, font_name: str, font_size: float) -> dict:
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

    def d_entry_with_alpha(entry: dict) -> bytes:
        r, g, b, a = color_entry_to_rgba(tokens, entry)
        return archive_color_rgb(r, g, b, a)

    profile: dict[str, object] = {
        "name": "Kumanui",
        # Core color keys
        "BackgroundColor": d(bg_hex),
        "TextColor": d(fg_hex),
        "TextBoldColor": d(bold_hex),
        # Honor alpha on selection/cursor if provided by tokens
        "SelectionColor": d_entry_with_alpha(term['selection']),
        "CursorColor": d_entry_with_alpha(term['cursor']),
        # Set cursor text to background for contrast
        "CursorTextColor": d(bg_hex),
        # Window size (in character cells)
        "columnCount": 108,
        "rowCount": 40,
        # Text rendering and bold behavior
        # Enable font antialiasing and use bright colors for bold text
        "FontAntialias": True,
        "UseBrightBold": True,
        # Font and spacing config
        # Font info embedded below
        # Height and width spacing multipliers
        "FontHeightSpacing": 0.90,
        "FontWidthSpacing": 1.0,
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

    # Embedded font configuration
    profile["Font"] = archive_font(font_name, float(font_size))
    return profile


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate macOS Terminal .terminal profile from tokens/colors.yaml")
    ap.add_argument("out", help="Output path (.terminal) or '-' for stdout")
    ap.add_argument("--font-name", default=DEFAULT_FONT_NAME, help="Font name or PostScript name (e.g. 'SF Mono' or 'SFMono-Regular')")
    ap.add_argument("--font-size", type=float, default=DEFAULT_FONT_SIZE, help="Font size in points")
    args = ap.parse_args()

    tokens = load_tokens(TOKENS_PATH)
    profile = build_profile(tokens, args.font_name, args.font_size)

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
