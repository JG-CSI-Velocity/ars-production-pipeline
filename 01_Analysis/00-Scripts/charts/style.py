"""Shared chart constants for all analysis modules.

Constants only -- no functions. Use ars.mplstyle for rcParams defaults.
Import what you need: from ars_analysis.charts.style import PERSONAL, BUSINESS, TITLE_SIZE

Color authority imported from shared.charts.COLORS (canonical).
Legacy ARS-specific semantic names (PERSONAL, BUSINESS, etc.) preserved as aliases.
"""

from matplotlib.ticker import FuncFormatter

from shared.charts import COLORS, MAX_CATEGORICAL_COLORS

# Canonical semantic colors (from shared authority).
# All values flow from SLIDE_DESIGN.md §5 via shared.charts.COLORS -- do not
# hardcode hex here.
PRIMARY = COLORS["primary"]          # Navy #1E3D59 -- titles, primary bars, axis lines
POSITIVE = COLORS["positive"]        # #28A745
NEGATIVE = COLORS["negative"]        # #DC3545
NEUTRAL = COLORS["neutral"]          # #999999 -- historical / reference muted gray

# Accent + secondary teal per SLIDE_DESIGN §5.
TEAL = COLORS["secondary"]           # #17A2B8 -- accent, "our" data, L12M / current
TEAL_SECONDARY = COLORS["secondary_alt"]  # #6FB3C0 -- secondary series alongside primary teal

# ARS-specific semantic aliases. Realigned to SLIDE_DESIGN.md so charts that
# imported these by name automatically match the design system (issue 142,
# item 3.6). Historical = muted gray; TTM = accent teal (per §5: "Historical
# baselines are always muted gray; L12M or 'current' is always accent teal").
PERSONAL = COLORS["primary"]         # paired-comparison primary
BUSINESS = COLORS["secondary"]       # paired-comparison accent
HISTORICAL = COLORS["neutral"]       # always muted gray per §5
TTM = COLORS["secondary"]            # accent teal per §5
ELIGIBLE = COLORS["positive"]        # green for "in-scope" / "kept"
SILVER = "#BDC3C7"                   # legacy soft gray for table strokes
__all_legacy_overrides__ = ()        # marker for grep-able cleanup pass

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
