"""Brand authority tests.

shared/brand.py is the single source of truth. shared/charts.py COLORS and
charts/style.py aliases are thin views that must resolve to brand values.
If a future change introduces a divergent navy or accent, these tests catch it.
"""

from __future__ import annotations

from ars_analysis.shared.brand import (
    BRAND,
    BUSINESS,
    CHART_PALETTE,
    ELIGIBLE,
    FONTS,
    HISTORICAL,
    PERSONAL,
    SIZES,
    TEAL,
)


def test_brand_navy_is_csi_canonical():
    assert BRAND["navy"] == "#1A1A1A"


def test_brand_accent_is_csi_orange():
    assert BRAND["accent"] == "#F15D22"


def test_fonts_are_csi_typeface():
    assert FONTS["title"] == "Montserrat"
    assert FONTS["mono"] == "Space Mono"


def test_sizes_match_slide_design_anatomy():
    assert SIZES["action_title"] == 24
    assert SIZES["callout_hero"] == 44


def test_chart_palette_starts_with_brand_identity():
    assert CHART_PALETTE[0] == BRAND["navy"]
    assert CHART_PALETTE[1] == BRAND["accent"]


def test_semantic_aliases_resolve_to_brand():
    assert PERSONAL == CHART_PALETTE[0]
    assert BUSINESS == CHART_PALETTE[1]
    assert ELIGIBLE == CHART_PALETTE[0]
    assert TEAL == CHART_PALETTE[7]
    # Historical is intentionally an off-palette muted blue (reference line)
    assert HISTORICAL.startswith("#")


def test_shared_charts_colors_view_pins_to_brand():
    from ars_analysis.shared.charts import COLORS
    assert COLORS["primary"] == BRAND["navy"]
    assert COLORS["accent"] == BRAND["accent"]
    assert COLORS["positive"] == BRAND["positive"]
    assert COLORS["negative"] == BRAND["negative"]


def test_charts_style_primary_is_brand_navy():
    from ars_analysis.charts.style import PRIMARY, POSITIVE, NEGATIVE
    assert PRIMARY == BRAND["navy"]
    assert POSITIVE == BRAND["positive"]
    assert NEGATIVE == BRAND["negative"]
