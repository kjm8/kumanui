from __future__ import annotations


def resolve_ref(tokens: dict, ref: str) -> dict | None:
    """Follow a reference string like "{path.to.token}" within tokens."""
    if not (isinstance(ref, str) and ref.startswith("{") and ref.endswith("}")):
        return None
    cur: object = tokens
    for key in ref[1:-1].split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur if isinstance(cur, dict) else None


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Return RGB ints from a hex string of length 6 or 8."""
    s = hex_str.strip().lstrip("#")
    if len(s) not in (6, 8):
        raise ValueError(f"Unsupported hex length: {hex_str}")
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return r, g, b


def hex_to_rgb01(hex_str: str) -> tuple[float, float, float]:
    """Return RGB floats in [0,1] from a hex string."""
    r, g, b = hex_to_rgb(hex_str)
    return r / 255.0, g / 255.0, b / 255.0


def color_entry_to_hex(tokens: dict, entry: dict) -> str:
    """Resolve a color token entry to a hex value."""
    val = entry.get("value")
    if isinstance(val, str):
        if val.startswith("#"):
            return val.upper()
        refd = resolve_ref(tokens, val)
        if (
            refd
            and isinstance(refd.get("value"), str)
            and refd["value"].startswith("#")
        ):
            return refd["value"].upper()
    raise ValueError(f"Unsupported color value: {val}")


def color_entry_to_rgba(tokens: dict, entry: dict) -> tuple[float, float, float, float]:
    """Resolve a color token entry to RGBA floats in [0,1]."""
    try:
        a = float(entry.get("alpha", 1.0))
    except Exception:
        a = 1.0
    hex_source = entry.get("value")
    if isinstance(hex_source, str) and not hex_source.startswith("#"):
        refd = resolve_ref(tokens, hex_source)
        if refd:
            if "alpha" in refd and "alpha" not in entry:
                try:
                    a = float(refd["alpha"])
                except Exception:
                    a = 1.0
            hex_source = refd.get("value", hex_source)
    if isinstance(hex_source, str) and hex_source.startswith("#"):
        r, g, b = hex_to_rgb01(hex_source)
        return r, g, b, a
    raise ValueError(f"Unsupported color value: {hex_source}")
