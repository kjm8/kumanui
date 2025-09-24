#!/usr/bin/env python3
"""
Showcase Kumanui colors in the terminal.

Features:
- Large "Kumanui" banner where each character is rendered with a single hue using its standard/bright ANSI pair (e.g., red + bright red)
- List ANSI hues with Standard/Bright swatches and representative hex values

Usage:
  python3 _assets/scripts/terminal_demo.py

Notes:
- Uses only ANSI 8/16 colors (no truecolor), so it displays well on
  terminals without 24-bit color support.
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import sys

try:
    import yaml  # type: ignore
except Exception:
    print(
        "ERROR: PyYAML not installed. Install with: pip3 install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[2]
TOKENS_PATH = ROOT / "tokens/colors.yaml"


RESET = "\x1b[0m"


def sgr(*codes: int) -> str:
    return "\x1b[" + ";".join(str(c) for c in codes) + "m"


def load_tokens(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def palette_order() -> list[str]:
    # Order consistent with README and CSS generation where appropriate
    return ["black", "white", "red", "green", "blue", "yellow", "magenta", "cyan"]


def representative_hex(tokens: dict, hue: str, bright: bool) -> str:
    """Map ANSI Standard/Bright to token hex values.

    - Standard -> palette.<hue>.base
    - Bright -> palette.<hue>.light
    Fallbacks to base if missing.
    """
    group = tokens.get("palette", {}).get(hue, {})
    if not isinstance(group, dict):
        return "#FFFFFF" if bright else "#EEEEEE"
    key = "light" if bright else "base"
    entry = group.get(key) or group.get("base")
    if isinstance(entry, dict) and isinstance(entry.get("value"), str):
        return entry["value"].upper()
    return "#FFFFFF" if bright else "#EEEEEE"


def hue_index(hue: str) -> int:
    idx = {
        "black": 0,
        "red": 1,
        "green": 2,
        "yellow": 3,
        "blue": 4,
        "magenta": 5,
        "cyan": 6,
        "white": 7,
    }
    return idx.get(hue, 7)


def ansi_fg_for(hue: str, tier: str) -> int:
    i = hue_index(hue)
    if tier == "light":
        return 90 + i  # bright
    return 30 + i  # standard for base/dark


def ansi_bg_for(hue: str, tier: str) -> int:
    i = hue_index(hue)
    if tier == "light":
        return 100 + i  # bright background
    return 40 + i


def hues_for_text(text: str) -> list[str]:
    cycle = ["red", "green", "blue", "magenta", "cyan", "yellow", "white"]
    res: list[str] = []
    for i, _ in enumerate(text):
        res.append(cycle[i % len(cycle)])
    return res


# Simple 6-row big-letter patterns using full blocks
LETTER_PATTERNS: dict[str, list[str]] = {
    # A 7-column block font for most letters
    "K": [
        "##   ##",
        "##  ## ",
        "#####  ",
        "##  ## ",
        "##   ##",
        "##   ##",
    ],
    "U": [
        "##   ##",
        "##   ##",
        "##   ##",
        "##   ##",
        "##   ##",
        " ##### ",
    ],
    "M": [
        "##   ##",
        "### ###",
        "## # ##",
        "##   ##",
        "##   ##",
        "##   ##",
    ],
    "A": [
        " ##### ",
        "##   ##",
        "#######",
        "##   ##",
        "##   ##",
        "##   ##",
    ],
    "N": [
        "##   ##",
        "###  ##",
        "#### ##",
        "## ####",
        "##  ###",
        "##   ##",
    ],
    "I": [
        "#######",
        "  ##   ",
        "  ##   ",
        "  ##   ",
        "  ##   ",
        "#######",
    ],
}


def render_banner(text: str, letter_hues: list[str]) -> str:
    text = text.upper()
    # Assemble rows by concatenating letter patterns with 2 spaces between
    # Build structured rows: list of cells with (filled, letter_idx, col_in_letter)
    rows: list[list[tuple[bool, int, int]]] = [[] for _ in range(6)]
    for idx, ch in enumerate(text):
        pat = LETTER_PATTERNS.get(ch)
        if not pat:
            pat = ["       "] * 6  # 7-wide empty
        for r in range(6):
            if rows[r]:
                # add 2-space gap as two empty cells (no letter association)
                rows[r].append((False, -1, -1))
                rows[r].append((False, -1, -1))
            for c, chpix in enumerate(pat[r]):
                rows[r].append((chpix == "#", idx, c))

    # Colorize per column using foreground colored full blocks
    # Each pattern cell becomes two characters: '██' for '#' and '  ' for space.
    out_lines: list[str] = []
    if not letter_hues:
        letter_hues = ["white"] * max(1, len(text))

    for r in rows:
        built = []
        for filled, letter_idx, col_in_letter in r:
            if filled and letter_idx >= 0:
                hue = letter_hues[letter_idx % len(letter_hues)].lower()
                # Alternate bright/normal by column within the letter
                tier = "light" if (col_in_letter % 2 == 0) else "base"
                code = ansi_fg_for(hue, tier)
                built.append(sgr(code) + "██" + RESET)
            else:
                built.append("  ")
        out_lines.append("".join(built))
    return "\n".join(out_lines)


def print_ansi_color_list(tokens: dict) -> None:
    print("\nANSI colors (Standard/Bright):\n")

    # Build 3-line blocks for each hue
    blocks: list[list[str]] = []
    for hue in palette_order():
        title = hue.capitalize()
        # Standard
        bg_norm = ansi_bg_for(hue, "base")
        hex_norm = representative_hex(tokens, hue, bright=False)
        std_line = f"  {sgr(bg_norm)}  {RESET} Standard {hex_norm}"
        # Bright
        bg_bright = ansi_bg_for(hue, "light")
        hex_bright = representative_hex(tokens, hue, bright=True)
        bri_line = f"  {sgr(bg_bright)}  {RESET} Bright   {hex_bright}"
        blocks.append([f"{title}:", std_line, bri_line])

    # Helper to strip ANSI for correct width calculations
    ansi_re = re.compile(r"\x1b\[[0-9;]*m")

    def visible_len(s: str) -> int:
        return len(ansi_re.sub("", s))

    def pad_ansi(s: str, width: int) -> str:
        pad = max(0, width - visible_len(s))
        return s + (" " * pad)

    # Compute column width and how many columns fit into 128 chars
    col_width = 0
    for block in blocks:
        for line in block:
            col_width = max(col_width, visible_len(line))
    col_width = max(col_width, 18)  # reasonable minimum

    total_width = min(shutil.get_terminal_size((128, 24)).columns, 128)
    gap = 2
    cols = max(1, total_width // (col_width + gap))

    # Print in rows of `cols` blocks
    for i in range(0, len(blocks), cols):
        row_blocks = blocks[i : i + cols]
        # Each block has exactly 3 lines
        for line_idx in range(3):
            line = (" " * 0).join(pad_ansi(b[line_idx], col_width) for b in row_blocks)
            # Insert gaps between columns by replacing single joins with gap spaces
            if len(row_blocks) > 1:
                pieces = [pad_ansi(b[line_idx], col_width) for b in row_blocks]
                line = (" " * gap).join(pieces)
            print(line)
        print("")


def main() -> int:
    tokens = load_tokens(TOKENS_PATH)

    print()
    print()
    text = "Kumanui"
    print(render_banner(text, hues_for_text(text)))
    print()
    print_ansi_color_list(tokens)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
