"""Single source of truth for CSI Velocity brand.

Every chart, Excel sheet, PPTX, and UI surface should read brand values from
this module. Before this module existed, five different navies and three
different accents lived across shared/charts.py, charts/style.py,
output/excel_formatter.py, shared/excel.py, output/deck_builder.py,
05_UI/index.html, and the README -- giving each deck a slightly different
look on every run.

BRAND dict holds the canonical CSI palette plus semantic roles for charts.
CHART_PALETTE is the categorical sequence for multi-series plots; semantic
slots (PERSONAL, BUSINESS, ...) are aliases that resolve here.
"""

from __future__ import annotations

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

# Categorical sequence for multi-series charts. Order matters -- series 1 = CHART_PALETTE[0].
# Pinned to a palette that reads well against the navy/orange identity without
# muddying single-series brand emphasis.
CHART_PALETTE: tuple[str, ...] = (
    "#00274C",   # CSI Navy (series 1)
    "#F15D22",   # CSI Orange / accent (series 2)
    "#2A8B3E",   # positive (series 3)
    "#EB2A2E",   # CSI Red / negative (series 4)
    "#8B95A2",   # neutral (series 5)
    "#5B6770",   # slate (series 6)
    "#F8971D",   # CSI Gold (series 7)
    "#48A6A7",   # teal (series 8)
)

# Semantic aliases the analytics layer reads. Keep names stable; resolve to brand.
PERSONAL    = CHART_PALETTE[0]   # navy -- consumer accounts
BUSINESS    = CHART_PALETTE[1]   # accent -- business accounts
HISTORICAL  = "#5B9BD5"          # historical reference line -- intentionally muted blue
TTM         = CHART_PALETTE[1]   # accent -- recent / L12M emphasis
ELIGIBLE    = CHART_PALETTE[0]   # navy -- canonical denominator base
SILVER      = BRAND["muted"]
TEAL        = CHART_PALETTE[7]

# Font family
FONTS: dict[str, str] = {
    "title": "Montserrat",
    "body":  "Montserrat",
    "mono":  "Space Mono",
}

# Font sizes per the SLIDE_DESIGN.md anatomy.
SIZES: dict[str, int] = {
    "action_title":  24,
    "subtitle":      16,
    "body":          12,
    "callout_hero":  44,
    "callout_label": 14,
    "axis":          11,
    "footnote":      9,
}


def as_tokens() -> dict:
    """Return the brand as a plain, JSON-serializable token dict.

    This is the neutral hand-off other surfaces consume (the HTML review's
    CSS :root, future design tools) so they don't each re-declare colors and
    fonts -- which is how five divergent navies appeared in the first place.
    """
    return {"colors": dict(BRAND), "fonts": dict(FONTS), "sizes": dict(SIZES)}


def export_tokens(path: "str | None" = None) -> "Path":
    """Write the brand tokens to ``03_Config/brand_tokens.json`` and return the path.

    Run as a module to regenerate: ``python -m ars_analysis.shared.brand``.
    """
    import json
    from pathlib import Path

    if path is None:
        # shared/ -> 00-Scripts -> 01_Analysis -> repo root
        repo_root = Path(__file__).resolve().parents[3]
        path = repo_root / "03_Config" / "brand_tokens.json"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(as_tokens(), indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":  # pragma: no cover - regeneration helper
    print(f"wrote {export_tokens()}")
