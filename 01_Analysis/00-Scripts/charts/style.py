"""Shared chart constants for all analysis modules.

Constants only -- no functions. Use ars.mplstyle for rcParams defaults.
Import what you need: from ars_analysis.charts.style import PERSONAL, BUSINESS, TITLE_SIZE

Color authority is ars_analysis.shared.brand.BRAND. All semantic aliases
(PERSONAL, BUSINESS, HISTORICAL, TTM, ELIGIBLE, SILVER, TEAL) resolve there.
Old hex literals here (#4472C4 / #ED7D31 / #FFC000 / #70AD47 / etc.) were
divergent from the CSI brand; the brand module collapses them.
"""

from matplotlib.ticker import FuncFormatter

from ars_analysis.shared import brand as _brand
from ars_analysis.shared.brand import (  # noqa: F401  -- public surface
    BUSINESS,
    ELIGIBLE,
    HISTORICAL,
    PERSONAL,
    SILVER,
    TEAL,
    TTM,
)

# Canonical semantic colors (from the brand)
PRIMARY = _brand.BRAND["navy"]
POSITIVE = _brand.BRAND["positive"]
NEGATIVE = _brand.BRAND["negative"]
NEUTRAL = _brand.BRAND["neutral"]

# Presentation font sizes (for per-call overrides beyond rcParams)
TITLE_SIZE = 24
AXIS_LABEL_SIZE = 20
DATA_LABEL_SIZE = 20
TICK_SIZE = 18
LEGEND_SIZE = 16
ANNOTATION_SIZE = 18

# Bar chart defaults
BAR_EDGE = "none"
BAR_ALPHA = 0.9

# Percentage formatter (pre-instantiated, reuse everywhere)
PCT_FORMATTER = FuncFormatter(lambda x, p: f"{x:.0f}%")
