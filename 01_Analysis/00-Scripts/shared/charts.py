"""Shared chart theme and export helpers.

COLORS and CATEGORY_PALETTE are now thin views over ars_analysis.shared.brand,
the single source of truth for the CSI Velocity brand. Old hex literals here
(#2E4057 / #F18F01) were the 5th competing navy and 3rd competing accent --
brand.BRAND collapses them onto the canonical CSI navy (#1A1A1A) and
orange (#F15D22).
"""

from __future__ import annotations

import warnings
from pathlib import Path

from ars_analysis.shared.brand import BRAND, CHART_PALETTE

# Backward-compatible view over the canonical brand. Same keys as before so
# existing `from shared.charts import COLORS` call sites keep working.
COLORS = {
    "primary":   BRAND["navy"],
    "secondary": CHART_PALETTE[7],
    "accent":    BRAND["accent"],
    "positive":  BRAND["positive"],
    "negative":  BRAND["negative"],
    "neutral":   BRAND["neutral"],
    "light_bg":  "#F7F9FC",
    "dark_text": BRAND["navy"],
}

CATEGORY_PALETTE = list(CHART_PALETTE)


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
