#!/usr/bin/env python3
from __future__ import annotations
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKENS_PATH = ROOT / 'tokens/colors.yaml'

def hex_to_rgb01(h: str):
    s=h.lstrip('#')
    r=int(s[0:2],16)/255
    g=int(s[2:4],16)/255
    b=int(s[4:6],16)/255
    return r,g,b

def srgb_to_linear(c: float) -> float:
    return c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4

def rel_lum(hexv: str) -> float:
    r,g,b=hex_to_rgb01(hexv)
    rl,gl,bl=map(srgb_to_linear,(r,g,b))
    return 0.2126*rl+0.7152*gl+0.0722*bl

def contrast(hex_a: str, hex_b: str) -> float:
    la,lb=rel_lum(hex_a),rel_lum(hex_b)
    L1,L2=(la,lb) if la>lb else (lb,la)
    return (L1+0.05)/(L2+0.05)

def main() -> int:
    tokens = yaml.safe_load(TOKENS_PATH.read_text())
    bg = tokens['palette']['black']['dark']['value']  # Dark Black (dark background case)
    palette = tokens['palette']
    base_colors = {
        'Black Base': palette['black']['base']['value'],
        'White Base': palette['white']['base']['value'],
        'Red Base': palette['red']['base']['value'],
        'Green Base': palette['green']['base']['value'],
        'Blue Base': palette['blue']['base']['value'],
        'Yellow Base': palette['yellow']['base']['value'],
        'Magenta Base': palette['magenta']['base']['value'],
        'Cyan Base': palette['cyan']['base']['value'],
    }
    print(f"Dark background (Black Dark {bg})")
    print("Name, Hex, Contrast, Pass(4.5)")
    for name,hexv in base_colors.items():
        ratio = contrast(hexv, bg)
        print(f"{name}, {hexv}, {ratio:.2f}, {'PASS' if ratio>=4.5 else 'FAIL'}")

    # Light background case: use Light White as background, check dark hues for text
    light_bg = palette['white']['light']['value']
    dark_colors = {
        'Black Dark': palette['black']['dark']['value'],
        'White Dark': palette['white']['dark']['value'],
        'Red Dark': palette['red']['dark']['value'],
        'Green Dark': palette['green']['dark']['value'],
        'Blue Dark': palette['blue']['dark']['value'],
        'Yellow Dark': palette['yellow']['dark']['value'],
        'Magenta Dark': palette['magenta']['dark']['value'],
        'Cyan Dark': palette['cyan']['dark']['value'],
    }
    print()
    print(f"Light background (White Light {light_bg})")
    print("Name, Hex, Contrast, Pass(4.5)")
    for name,hexv in dark_colors.items():
        ratio = contrast(hexv, light_bg)
        print(f"{name}, {hexv}, {ratio:.2f}, {'PASS' if ratio>=4.5 else 'FAIL'}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
