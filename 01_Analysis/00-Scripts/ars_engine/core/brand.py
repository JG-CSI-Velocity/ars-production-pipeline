"""Single source of truth for CSI Velocity brand (v3 home).

Ported from the legacy ``shared/brand.py`` (which had already unified five
divergent navies and three accents). The token file at
``03_Config/brand_tokens.json`` is generated FROM this module -- regenerate
with ``python -m ars_engine.core.brand`` after any change. Every chart, Excel
sheet, PPTX, and UI surface reads brand values from here or the token file;
no other module may declare colors.
"""

from __future__ import annotations

from pathlib import Path

# Canonical CSI brand, per the CSI brand guidelines / PowerPoint skill
# (owner-provided 2026-06-11): Navy #00274C anchor; Gold #F8971D, Orange
# #F15D22, Red #EB2A2E accents; white / #F8F8F8 backgrounds.
BRAND: dict[str, str] = {
    # Identity
    "navy":         "#00274C",   # CSI Navy -- primary anchor: titles, axis labels, brand bars
    "navy_soft":    "#1B4569",   # softened navy -- body text on dark surfaces
    "accent":       "#F15D22",   # CSI Orange -- single-color emphasis, callout hero
    "accent_light": "#fef0e8",   # accent background tint
    "accent_dark":  "#d14e1a",   # accent hover / pressed
    "gold":         "#F8971D",   # CSI Gold -- secondary accent

    # Semantic
    "positive":     "#2A8B3E",   # rate up, opt-in growth (no CSI green; used sparingly)
    "negative":     "#EB2A2E",   # CSI Red -- rate down, churn, gap
    "warning":      "#F8971D",   # CSI Gold -- caution, anomaly highlight
    "neutral":      "#8B95A2",   # baseline series, contextual reference
    "muted":        "#B0B0B0",   # secondary text, axis ticks
    "light_gray":   "#F8F8F8",   # light background per guidelines; gridlines/separators

    # Surface
    "bg":           "#FFFFFF",
    "text":         "#222222",
    "text_muted":   "#777777",
}

# Categorical sequence for multi-series charts. Order matters -- series 1 =
# CHART_PALETTE[0]. The four CSI anchors first, then two neutrals and two
# navy-derived steel-blue tints so the whole deck reads as one system.
CHART_PALETTE: tuple[str, ...] = (
    "#00274C",   # CSI Navy (series 1)
    "#F15D22",   # CSI Orange / accent (series 2)
    "#F8971D",   # CSI Gold (series 3)
    "#EB2A2E",   # CSI Red / negative (series 4)
    "#8B95A2",   # neutral gray (series 5)
    "#5B6770",   # slate (series 6)
    "#7BA0C4",   # light navy tint (series 7) -- derived from CSI Navy
    "#3E6B94",   # navy tint / steel blue (series 8) -- derived from CSI Navy
)

# Semantic aliases the analytics layer reads. Keep names stable; resolve to brand.
PERSONAL = CHART_PALETTE[0]      # navy -- consumer accounts
BUSINESS = CHART_PALETTE[1]      # accent -- business accounts
HISTORICAL = "#9AA7B5"           # historical reference line -- muted navy-gray
TTM = CHART_PALETTE[1]           # accent -- recent / L12M emphasis
ELIGIBLE = CHART_PALETTE[0]      # navy -- canonical denominator base
SILVER = BRAND["muted"]

FONTS: dict[str, str] = {
    "title": "Montserrat",
    "body": "Montserrat",
    "mono": "Space Mono",
}

# Font sizes per the SLIDE_DESIGN.md anatomy.
SIZES: dict[str, int] = {
    "action_title": 24,
    "subtitle": 16,
    "body": 12,
    "callout_hero": 44,
    "callout_label": 14,
    "axis": 11,
    "footnote": 9,
}


def as_tokens() -> dict:
    """Return the brand as a plain, JSON-serializable token dict."""
    return {"colors": dict(BRAND), "fonts": dict(FONTS), "sizes": dict(SIZES)}


def export_tokens(path: str | Path | None = None) -> Path:
    """Write the brand tokens to ``03_Config/brand_tokens.json``."""
    import json

    if path is None:
        # core/ -> ars_engine -> 00-Scripts -> 01_Analysis -> repo root
        repo_root = Path(__file__).resolve().parents[4]
        path = repo_root / "03_Config" / "brand_tokens.json"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(as_tokens(), indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":  # pragma: no cover - regeneration helper
    print(f"wrote {export_tokens()}")
