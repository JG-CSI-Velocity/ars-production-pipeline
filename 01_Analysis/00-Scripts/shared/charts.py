"""Shared chart theme and export helpers.

COLORS and CATEGORY_PALETTE are now thin views over ars_analysis.shared.brand,
the single source of truth for the CSI Velocity brand. Old hex literals here
(#2E4057 / #F18F01) were the 5th competing navy and 3rd competing accent --
brand.BRAND collapses them onto the canonical CSI Navy (#00274C) and
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


def draw_funnel(
    ax: object,
    stages: list[str],
    values: list[float],
    *,
    bar_color: str | None = None,
    final_color: str | None = None,
    value_fmt: str = "{:,.0f}",
    highlight_biggest_drop: bool = True,
    label_fontsize: int = 14,
) -> None:
    """Draw a horizontal funnel: centered bars + drop-off connectors.

    Replaces the ax.table screenshots and nested-circle funnels scattered
    across the deck with one perceptually honest encoding. Stage names go
    on the y-axis, each bar is centered and sized by value, the count and
    %-of-first-stage sit inside the bar, and the drop between consecutive
    stages is annotated in the gap -- the biggest drop in the brand
    negative color.

    The final stage renders in `final_color` (default brand accent) so the
    surviving population pops. Callers own figure/axes lifecycle (pairs
    with charts.guards.chart_figure).
    """
    bar_color = bar_color or COLORS["primary"]
    final_color = final_color or COLORS["accent"]

    n = len(stages)
    if n == 0 or not values or values[0] <= 0:
        ax.axis("off")
        ax.text(0.5, 0.5, "No funnel data", ha="center", va="center",
                fontsize=label_fontsize, color=COLORS["neutral"])
        return

    vmax = float(max(values))
    drops = [
        (values[i] - values[i + 1]) / values[i] if values[i] else 0.0
        for i in range(n - 1)
    ]
    biggest = max(range(len(drops)), key=lambda i: drops[i]) if drops else -1

    for i, (stage, v) in enumerate(zip(stages, values)):
        color = final_color if i == n - 1 else bar_color
        ax.barh(i, v, left=(vmax - v) / 2, height=0.62, color=color, zorder=3)
        label = f"{value_fmt.format(v)}  ({v / values[0]:.0%})"
        if v > vmax * 0.22:
            ax.text(vmax / 2, i, label, ha="center", va="center",
                    fontsize=label_fontsize, fontweight="bold", color="white", zorder=4)
        else:
            ax.text((vmax + v) / 2 + vmax * 0.015, i, label, ha="left", va="center",
                    fontsize=label_fontsize, fontweight="bold",
                    color=COLORS["dark_text"], zorder=4)

    for i, pct in enumerate(drops):
        lost = values[i] - values[i + 1]
        if lost <= 0:
            continue
        emphasized = highlight_biggest_drop and i == biggest and pct > 0
        ax.text(
            vmax * 1.02, i + 0.5,
            f"−{value_fmt.format(lost)}  (−{pct:.0%})",
            ha="left", va="center", fontsize=label_fontsize - 2,
            fontweight="bold" if emphasized else "normal",
            color=COLORS["negative"] if emphasized else COLORS["neutral"],
        )

    ax.set_yticks(range(n))
    ax.set_yticklabels(stages, fontsize=label_fontsize)
    ax.invert_yaxis()
    ax.set_xlim(-vmax * 0.02, vmax * 1.30)
    ax.set_xticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


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
