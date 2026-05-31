"""Shared chart constants for all analysis modules.

Constants only -- no functions. Use ars.mplstyle for rcParams defaults.
Import what you need: from ars_analysis.charts.style import PERSONAL, BUSINESS, TITLE_SIZE

Color authority imported from shared.charts_palette.COLORS (canonical).
Legacy ARS-specific semantic names (PERSONAL, BUSINESS, etc.) preserved as aliases.
"""

from typing import Iterable

from matplotlib.ticker import FuncFormatter

from ars_analysis.shared.charts_palette import COLORS, MAX_CATEGORICAL_COLORS, SECTION_COLORS, section_color

# Canonical semantic colors (from shared authority).
# All values flow from SLIDE_DESIGN.md §5 via shared.charts_palette.COLORS -- do not
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


# ---------------------------------------------------------------------------
# Chart helpers (T1.3 — SLIDE_DESIGN.md §6)
#
# Centralized so individual analytics modules can opt into consistent axis,
# legend, annotation, and grid styling without re-implementing the rules.
# ---------------------------------------------------------------------------

# Auto-rotate threshold for x-axis labels: rotate to 45deg when there are
# more than this many tick labels OR any label exceeds the char limit.
AXIS_ROTATE_TICK_COUNT = 5
AXIS_ROTATE_CHAR_LIMIT = 6


def apply_section_color(ax, section_key: str, primary_series=None) -> None:
    """Tint axis spines and tick labels with the section accent (§5.1).

    The primary chart series stays accent teal (project rule: focus series
    is always teal regardless of section). This only colors the *chrome* --
    spines, tick labels, title underline -- so the slide visually anchors
    to its section without overwhelming the data.
    """
    accent = section_color(section_key)
    for spine in ("left", "bottom"):
        if spine in ax.spines:
            ax.spines[spine].set_color(accent)
            ax.spines[spine].set_linewidth(1.2)
    ax.tick_params(colors=accent)
    if primary_series is not None:
        # Caller passed the series handle; tint the focus color to section.
        try:
            primary_series.set_color(accent)
        except Exception:
            pass


def auto_rotate_xticks(ax, labels: Iterable[str] | None = None) -> None:
    """Rotate x-tick labels to 45deg when they're tight (§6.1).

    Never rotates to 90 (deck rule). If neither label count nor char count
    triggers, leaves labels horizontal.
    """
    if labels is None:
        try:
            labels = [t.get_text() for t in ax.get_xticklabels()]
        except Exception:
            return
    labels = list(labels)
    if not labels:
        return
    too_many = len(labels) > AXIS_ROTATE_TICK_COUNT
    too_wide = any(len(s) > AXIS_ROTATE_CHAR_LIMIT for s in labels)
    if too_many or too_wide:
        for t in ax.get_xticklabels():
            t.set_rotation(45)
            t.set_ha("right")
            t.set_rotation_mode("anchor")


def abbreviate_label(label: str, max_chars: int = 12) -> str:
    """Abbreviate long category labels in place (§6.1).

    Truncates with an ellipsis; preserves any leading digits (branch IDs,
    month codes) so the abbreviation still sorts and reads correctly.
    """
    if not label or len(label) <= max_chars:
        return label
    return label[: max_chars - 1].rstrip() + "…"


def standard_legend(ax, loc: str = "upper right") -> None:
    """Place the legend per §6 rules: right-aligned, 10pt, no background."""
    leg = ax.get_legend()
    if leg is None:
        try:
            leg = ax.legend(loc=loc)
        except Exception:
            return
    if leg is None:
        return
    leg.set_frame_on(False)
    for text in leg.get_texts():
        text.set_fontsize(10)


def annotate(ax, x, y, text: str, section_key: str | None = None) -> None:
    """Section-tinted annotation per §6: small box, accent border."""
    accent = section_color(section_key) if section_key else COLORS["primary"]
    ax.annotate(
        text,
        xy=(x, y),
        fontsize=10,
        color="#FFFFFF",
        bbox=dict(boxstyle="round,pad=0.3", facecolor=accent, edgecolor=accent, lw=0),
        ha="center",
    )


def light_grid(ax, axis: str = "y") -> None:
    """Light gray, 0.5pt grid per §6.1. Always behind data."""
    ax.grid(axis=axis, color=COLORS["light_bg"], linewidth=0.5, linestyle="-")
    ax.set_axisbelow(True)
