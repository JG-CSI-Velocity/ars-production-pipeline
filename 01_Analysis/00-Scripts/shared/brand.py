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

# Canonical CSI Velocity brand. Aligns with README + UI header.
BRAND: dict[str, str] = {
    # Identity
    "navy":         "#1A1A1A",   # CSI navy -- titles, axis labels, brand bars
    "navy_soft":    "#2A2A2A",   # body text on dark surfaces
    "accent":       "#F15D22",   # CSI orange -- single-color emphasis, callout hero
    "accent_light": "#fef0e8",   # accent background tint
    "accent_dark":  "#d14e1a",   # accent hover / pressed

    # Semantic
    "positive":     "#2A8B3E",   # rate up, opt-in growth
    "negative":     "#C73E1D",   # rate down, churn, gap
    "warning":      "#F39C12",   # caution, anomaly highlight
    "neutral":      "#8B95A2",   # baseline series, contextual reference
    "muted":        "#B0B0B0",   # secondary text, axis ticks
    "light_gray":   "#E8E8E8",   # gridlines, separators

    # Surface
    "bg":           "#FFFFFF",
    "text":         "#222222",
    "text_muted":   "#777777",
}

# Categorical sequence for multi-series charts. Order matters -- series 1 = CHART_PALETTE[0].
# Pinned to a palette that reads well against the navy/orange identity without
# muddying single-series brand emphasis.
CHART_PALETTE: tuple[str, ...] = (
    "#1A1A1A",   # navy (series 1)
    "#F15D22",   # accent (series 2)
    "#2A8B3E",   # positive (series 3)
    "#C73E1D",   # negative (series 4)
    "#8B95A2",   # neutral (series 5)
    "#5B6770",   # slate (series 6)
    "#D4A76A",   # sand (series 7)
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
