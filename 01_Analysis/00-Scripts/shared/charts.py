"""Shared chart theme and export helpers.

Color authority for all pipelines. Individual packages can import these
colors to ensure visual consistency across ARS (matplotlib) and Txn/ICS (Plotly).
"""

from __future__ import annotations

import warnings
from pathlib import Path

# Single color authority. Aligned to docs/SLIDE_DESIGN.md §5 (issue 142, item 3.6).
# Keep this dict and SLIDE_DESIGN.md §5 in lockstep; everything else
# (mplstyle, style.py aliases) reads from here.
COLORS = {
    "primary": "#1E3D59",       # SLIDE_DESIGN: Primary navy
    "secondary": "#17A2B8",     # SLIDE_DESIGN: Accent teal -- "current"/L12M/focus
    "secondary_alt": "#6FB3C0", # SLIDE_DESIGN: Secondary teal when paired with primary teal
    "accent": "#17A2B8",        # Alias of secondary -- "accent" is a common semantic name
    "positive": "#28A745",      # SLIDE_DESIGN: positive delta
    "negative": "#DC3545",      # SLIDE_DESIGN: negative delta
    "neutral": "#999999",       # SLIDE_DESIGN: historical baselines / muted reference
    "neutral_strong": "#555555",
    "light_bg": "#F7F9FC",
    "dark_text": "#1E3D59",
}

# Used when a chart needs more than two semantic series. Max 4 distinct
# values per SLIDE_DESIGN.md §5 "deck never uses more than 4 colors on a
# single slide" -- after the 4th, callers should switch to neutrals.
CATEGORY_PALETTE = [
    "#1E3D59",   # navy
    "#17A2B8",   # accent teal
    "#28A745",   # positive
    "#DC3545",   # negative
    "#6FB3C0",   # secondary teal (only if first 4 already used)
    "#999999",   # neutral
    "#555555",   # neutral strong
    "#1E3D59",   # repeat back to primary as a safety net
]

# Documented constraint (SLIDE_DESIGN.md §5). Modules building charts with
# CATEGORY_PALETTE should not exceed this; if they need more series, render
# extras in COLORS["neutral"] so the eye still tracks the highlighted ones.
MAX_CATEGORICAL_COLORS = 4


def save_chart_png(fig: object, path: Path, scale: int = 1) -> Path:
    """Save a chart figure to PNG. Works with both matplotlib and Plotly.

    Args:
        fig: A matplotlib Figure or Plotly Figure.
        path: Output file path.
        scale: 1 for Excel embedding, 3 for standalone/presentation.

    Returns:
        The saved file path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Detect figure type
    fig_type = type(fig).__module__

    if "matplotlib" in fig_type:
        fig.savefig(str(path), dpi=150 * scale, bbox_inches="tight", facecolor="white")
        import matplotlib.pyplot as plt

        plt.close(fig)
    elif "plotly" in fig_type:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            fig.write_image(str(path), scale=scale)
    else:
        raise TypeError(f"Unsupported figure type: {type(fig)}")

    return path
