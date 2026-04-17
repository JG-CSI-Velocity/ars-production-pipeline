"""CSI color palette from SLIDE_MAPPING.md.

One focal color per chart; everything else muted to MUTED_ALPHA.
"""

from __future__ import annotations

import math

from pptx.dml.color import RGBColor

NAVY = RGBColor(0x1B, 0x36, 0x5D)
TEAL = RGBColor(0x0D, 0x94, 0x88)
CORAL = RGBColor(0xE7, 0x4C, 0x3C)
AMBER = RGBColor(0xF3, 0x9C, 0x12)
GRAY = RGBColor(0x95, 0xA5, 0xA6)
SLATE = RGBColor(0x6B, 0x72, 0x80)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

MUTED_ALPHA = 0.3

PALETTE: tuple[RGBColor, ...] = (NAVY, TEAL, CORAL, AMBER, GRAY, SLATE, WHITE)


def _distance(a: RGBColor, b: RGBColor) -> float:
    """Euclidean distance in 0-255 RGB space."""
    return math.sqrt(
        (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2
    )


def is_palette_color(rgb: RGBColor) -> bool:
    """True if rgb is an exact-hex match for any palette color."""
    return any(rgb == p for p in PALETTE)


def nearest_palette(
    rgb: RGBColor, threshold: float = 5.0
) -> RGBColor | None:
    """Return the closest palette color if within `threshold`, else None.

    Colors within Euclidean distance <= threshold of a palette entry are
    assumed off-by-hex and snap to the palette entry. Farther colors are
    treated as intentional.
    """
    best: RGBColor | None = None
    best_d = float("inf")
    for p in PALETTE:
        d = _distance(rgb, p)
        if d < best_d:
            best_d = d
            best = p
    if best is not None and best_d <= threshold:
        return best
    return None


_BY_NAME: dict[str, RGBColor] = {
    "navy": NAVY, "teal": TEAL, "coral": CORAL, "amber": AMBER,
    "gray": GRAY, "slate": SLATE, "white": WHITE,
}


def focal(name: str) -> dict[str, RGBColor | list[RGBColor]]:
    """Return {'focal': <color>, 'muted': [other palette colors]}.

    For charts that emphasize one series: use focal for the highlight,
    render others in muted with MUTED_ALPHA applied by the caller.
    """
    key = name.lower()
    if key not in _BY_NAME:
        raise KeyError(f"Unknown palette color: {name}")
    emphasis = _BY_NAME[key]
    return {
        "focal": emphasis,
        "muted": [c for c in PALETTE if c != emphasis and c != WHITE],
    }
