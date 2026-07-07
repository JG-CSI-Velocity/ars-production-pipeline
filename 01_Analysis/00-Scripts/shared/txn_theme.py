"""Shared TXN conference theme -- clean import home for structured TXN modules.

The exec TXN sections get their palette + chart helpers from the mutable shared
namespace: ``analytics/general/01_general_theme.py`` runs first (execution order
100) and dumps ``GEN_COLORS`` / ``BRACKET_PALETTE`` / ``gen_fmt_*`` / ``gen_clean_axes``
into the namespace, and later sections (product at 210, ...) rely on those globals
already being present. That execution-order coupling is exactly the fragility the
exec->module migration removes.

A structured TXN module imports its theme from here instead:

    from ars_analysis.shared.txn_theme import GEN_COLORS, gen_fmt_pct, gen_clean_axes

Values are copied verbatim from ``general/01_general_theme.py`` so migrated charts
render identically. This is the projector-safe conference palette -- deliberately
distinct from the CSI brand palette in ``shared/brand.py`` (which is the single
source of truth for CSI brand identity and must not be conflated with this).

When ``general`` itself is later migrated, it should import from here too, at which
point ``general/01_general_theme.py`` can be retired.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Color palette (bold, high-contrast, projector-safe) -- verbatim from
# general/01_general_theme.py:21
# ---------------------------------------------------------------------------
GEN_COLORS: dict[str, str] = {
    "primary":     "#1B2A4A",   # deep navy
    "accent":      "#E63946",   # signal red
    "success":     "#2EC4B6",   # teal
    "warning":     "#FF9F1C",   # amber
    "info":        "#457B9D",   # steel blue
    "light_bg":    "#F8F9FA",   # off-white
    "dark_text":   "#1B2A4A",
    "muted":       "#6C757D",
    "grid":        "#E9ECEF",
}

# Bracket palette (8 spending bins, ordered light-to-dark)
BRACKET_PALETTE: list[str] = [
    "#A8DADC",   # < $1
    "#457B9D",   # $1-5
    "#2EC4B6",   # $5-10
    "#FF9F1C",   # $10-25
    "#F4A261",   # $25-50
    "#E76F51",   # $50-100
    "#E63946",   # $100-500
    "#1B2A4A",   # $500+
]

# Engagement tier palette + order
ENGAGE_PALETTE: dict[str, str] = {
    "Power":    "#E63946",
    "Heavy":    "#FF9F1C",
    "Moderate": "#2EC4B6",
    "Light":    "#457B9D",
    "Dormant":  "#6C757D",
}
ENGAGE_ORDER: list[str] = ["Power", "Heavy", "Moderate", "Light", "Dormant"]

# ---------------------------------------------------------------------------
# Universal title / subtitle layout constants (verbatim from general theme)
# ---------------------------------------------------------------------------
GEN_TITLE_Y = 0.97
GEN_SUBTITLE_Y = 0.92
GEN_TOP_PAD = 0.85


# ---------------------------------------------------------------------------
# Conference-safe axis formatters
# ---------------------------------------------------------------------------
def gen_fmt_pct(x, _=None):
    return f"{x:.1f}%"


def gen_fmt_count(x, _=None):
    if x >= 1_000_000:
        return f"{x / 1_000_000:.1f}M"
    if x >= 1_000:
        return f"{x / 1_000:.0f}K"
    return f"{int(x)}"


def gen_fmt_index(x, _=None):
    return f"{x:.0f}"


def gen_fmt_dollar(x, _=None):
    if abs(x) >= 1_000_000:
        return f"${x / 1_000_000:.1f}M"
    if abs(x) >= 1_000:
        return f"${x / 1_000:.0f}K"
    return f"${x:,.0f}"


# ---------------------------------------------------------------------------
# Remove chart clutter for a clean conference look
# ---------------------------------------------------------------------------
def gen_clean_axes(ax, keep_left=True, keep_bottom=True):
    """Remove spines and ticks. Verbatim behavior from general/01_general_theme."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if not keep_left:
        ax.spines["left"].set_visible(False)
        ax.tick_params(left=False)
    if not keep_bottom:
        ax.spines["bottom"].set_visible(False)
        ax.tick_params(bottom=False)
    ax.grid(False)
