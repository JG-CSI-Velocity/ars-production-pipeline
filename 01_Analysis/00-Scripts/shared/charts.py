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

import matplotlib.patches as mpatches

from ars_analysis.shared.brand import (
    BRAND,
    CHART_PALETTE,
    ELIGIBLE,
    HISTORICAL,
    TEAL,
)

POSITIVE = BRAND["positive"]
NEGATIVE = BRAND["negative"]

# Canonical box-funnel palette (one stage per color). The final stage uses the
# brand accent so the surviving population pops. Shared by the Reg E, DCTR, and
# eligibility funnels so they read as one family.
BOX_FUNNEL_PALETTE = [HISTORICAL, ELIGIBLE, TEAL, POSITIVE, BRAND["accent"]]

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
    pct_of: str = "first",
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
        # pct_of="first": share of the top stage. pct_of="prev": conversion
        # from the preceding stage -- so a rate DEFINED as stageN/stageN-1
        # (e.g. Reg E opt-in = personal w/ Reg E / eligible personal w/debit)
        # appears on the bar itself, not just in a side box.
        pct_base = values[0] if (pct_of == "first" or i == 0) else values[i - 1]
        pct = (v / pct_base) if pct_base else 0.0
        label = f"{value_fmt.format(v)}  ({pct:.1%})" if pct_of == "prev" else             f"{value_fmt.format(v)}  ({pct:.0%})"
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


def draw_box_funnel(
    ax: object,
    stage_names: list[str],
    stage_totals: list[float],
    title: str,
    subtitle: str = "",
    callout: str = "",
    palette: list[str] | None = None,
) -> None:
    """Draw a proportional box funnel: centered rounded boxes + conversion badges.

    The single renderer behind the Reg E, DCTR, and eligibility funnels so they
    read as one family: a light canvas, proportional FancyBboxPatch boxes in the
    brand palette, centered number-only labels in white, left-side stage names,
    and between-stage conversion-% badges. The final stage uses the brand accent
    to make the surviving population pop. Each stage is shown as a conversion of
    the prior stage, so the last badge is the final-stage opt-in / pass-through
    rate.

    Callers own figure/axes lifecycle (pairs with charts.guards.chart_figure).

    Args:
        ax: A matplotlib Axes to draw on.
        stage_names: Stage labels, top to bottom.
        stage_totals: Stage counts, parallel to stage_names; box width is sized
            against the first stage.
        title: Bold title drawn at the top of the axes.
        subtitle: Italic subtitle under the title.
        callout: Optional metric callout drawn in a boxed label at the bottom.
        palette: Optional per-stage color override; defaults to the canonical
            box-funnel palette (final stage = brand accent).
    """
    palette = palette or BOX_FUNNEL_PALETTE
    totals = [float(t) for t in stage_totals]
    base_total = totals[0] if totals and totals[0] > 0 else 1.0
    n = len(stage_names)

    ax.set_facecolor("#f8f9fa")
    max_width = 0.8
    min_width = 0.08
    stage_gap = 0.02
    y_start = 0.82
    # Reserve bottom space so the callout box sits clearly below the final
    # (orange) stage instead of touching it.
    bottom_reserve = 0.13
    stage_height = min(0.15, (y_start - bottom_reserve - (n - 1) * stage_gap) / max(n, 1))

    # The final stage always renders in the last palette color (brand accent)
    # so the surviving population pops regardless of stage count; non-final
    # stages cycle the remaining colors. For the canonical 5-stage funnel this
    # is identical to indexing the full palette in order (so the Reg E / DCTR
    # funnels are unchanged); for the 6-stage eligibility funnel it keeps the
    # final ELIGIBLE box on the accent instead of wrapping back to the start.
    final_color = palette[-1]
    cycle = palette[:-1] if len(palette) > 1 else palette

    current_y = y_start
    for i in range(n):
        total = totals[i]
        width = max(min_width, max_width * (total / base_total))
        face = final_color if i == n - 1 else cycle[i % len(cycle)]

        rect = mpatches.FancyBboxPatch(
            (0.5 - width / 2, current_y - stage_height),
            width,
            stage_height,
            boxstyle="round,pad=0.01",
            facecolor=face,
            edgecolor="white",
            linewidth=3,
            alpha=0.9,
        )
        ax.add_patch(rect)
        ax.text(
            0.5,
            current_y - stage_height / 2,
            f"{int(total):,}",
            ha="center",
            va="center",
            fontsize=24,
            fontweight="bold",
            color="white",
            zorder=10,
        )
        ax.text(
            0.5 - width / 2 - 0.04,
            current_y - stage_height / 2,
            stage_names[i].replace(" ", "\n", 1),
            ha="right",
            va="center",
            fontsize=18,
            fontweight="600",
            color="#2c3e50",
        )
        if i > 0 and totals[i - 1] > 0:
            conv = total / totals[i - 1] * 100
            arrow_y = current_y + stage_gap / 2
            ax.annotate(
                "",
                xy=(0.5, arrow_y - stage_gap + 0.01),
                xytext=(0.5, arrow_y - 0.01),
                arrowprops={"arrowstyle": "->", "lw": 3, "color": NEGATIVE},
            )
            ax.text(
                0.45,
                arrow_y - stage_gap / 2,
                f"{conv:.1f}%",
                ha="center",
                va="center",
                fontsize=16,
                fontweight="bold",
                color="#e74c3c",
                bbox={
                    "boxstyle": "round,pad=0.3",
                    "facecolor": "white",
                    "edgecolor": "#e74c3c",
                    "alpha": 0.9,
                },
            )
        current_y -= stage_height + stage_gap

    ax.text(
        0.5, 0.98, title, ha="center", va="top", fontsize=26,
        fontweight="bold", color="#1e3d59", transform=ax.transAxes,
    )
    if subtitle:
        ax.text(
            0.5, 0.93, subtitle, ha="center", va="top", fontsize=18,
            style="italic", color="#7f8c8d", transform=ax.transAxes,
        )
    if callout:
        ax.text(
            0.5, 0.015, callout, transform=ax.transAxes,
            fontsize=13, fontweight="bold", ha="center", va="bottom",
            bbox={
                "boxstyle": "round,pad=0.5",
                "facecolor": "white",
                "edgecolor": BRAND["navy"],
                "linewidth": 1.5,
            },
        )

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")


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
