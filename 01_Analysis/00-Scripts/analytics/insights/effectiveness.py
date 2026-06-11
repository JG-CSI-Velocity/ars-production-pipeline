"""Effectiveness Proof Analysis -- A18 series.

Counters the objection "ARS is ineffective" by showing:
- A18.1: DCTR progression over time (with program start marker if available)
- A18.2: Cumulative value delivered timeline

Slide IDs: A18.1, A18.2.

A18.3 (Industry Benchmarks) was retired -- the underlying benchmarks.json
source was fabricated, so the comparison was misleading. See git history
for the prior implementation if real benchmark data ever becomes available.
"""

from __future__ import annotations

import matplotlib.ticker as mticker
import numpy as np
from loguru import logger

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.insights._data import get_dctr_1, get_dctr_3
from ars_analysis.analytics.mailer._helpers import (
    RESPONSE_SEGMENTS,
    discover_metric_cols,
    discover_pairs,
    parse_month,
)
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import NEGATIVE, POSITIVE, TEAL
from ars_analysis.pipeline.context import PipelineContext


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------


def _draw_dctr_progression(
    ax,
    ctx: PipelineContext,
) -> str:
    """Draw DCTR trend line using available data. Returns insight."""
    # Try to get historical and L12M DCTR from upstream results
    dctr_1 = get_dctr_1(ctx)
    dctr_3 = get_dctr_3(ctx)

    hist_dctr = dctr_1.get("overall_dctr", 0) * 100
    l12m_dctr = dctr_3.get("dctr", 0) * 100

    if hist_dctr == 0 and l12m_dctr == 0:
        return ""

    # Build what we have: at minimum historical vs L12M
    labels = ["Historical", "L12M"]
    values = [hist_dctr, l12m_dctr]

    colors = []
    for v in values:
        colors.append(POSITIVE if v >= hist_dctr else NEGATIVE)

    bars = ax.bar(
        labels, values, color=[TEAL, POSITIVE], width=0.5, edgecolor="white", linewidth=1.5
    )

    # Data labels
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{val:.1f}%",
            ha="center",
            va="bottom",
            fontsize=20,
            fontweight="bold",
        )

    # Delta annotation
    delta = l12m_dctr - hist_dctr
    sign = "+" if delta >= 0 else ""
    delta_color = POSITIVE if delta >= 0 else NEGATIVE
    ax.annotate(
        f"{sign}{delta:.1f}pp",
        xy=(1, l12m_dctr),
        xytext=(1.4, (hist_dctr + l12m_dctr) / 2),
        fontsize=18,
        fontweight="bold",
        color=delta_color,
        arrowprops={"arrowstyle": "->", "color": delta_color, "lw": 2},
    )

    ax.set_title("DCTR Progression", fontsize=20, fontweight="bold")
    ax.set_ylabel("Debit Card Transaction Rate (%)", fontsize=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=14)

    return f"Historical: {hist_dctr:.1f}% -> L12M: {l12m_dctr:.1f}% ({sign}{delta:.1f}pp)"


def _draw_cumulative_value(
    ax,
    ctx: PipelineContext,
) -> str:
    """Draw cumulative IC value from activations over time. Returns insight."""
    pairs = discover_pairs(ctx)
    spend_cols, _ = discover_metric_cols(ctx)

    if not pairs or not spend_cols:
        return ""

    data = ctx.data
    from ars_analysis.shared.helpers import get_ic_rate
    ic_rate = get_ic_rate(ctx)

    # For each mail month, count new activations and compute incremental IC
    monthly_ic = []
    seen_responded: set = set()

    for month, resp_col, _mail_col in pairs:
        responded = set(data[data[resp_col].isin(RESPONSE_SEGMENTS)].index)
        new_resp = responded - seen_responded
        seen_responded |= responded

        # Avg spend of new responders (use latest available spend column)
        if new_resp and spend_cols:
            latest_spend_col = spend_cols[-1]
            avg_spend = data.loc[list(new_resp), latest_spend_col].mean()
        else:
            avg_spend = 0

        monthly_ic_value = len(new_resp) * avg_spend * ic_rate
        monthly_ic.append(
            {
                "month": month,
                "month_ts": parse_month(month),
                "new_activations": len(new_resp),
                "monthly_ic": monthly_ic_value,
            }
        )

    if not monthly_ic:
        return ""

    # Cumulative
    cum_ic = np.cumsum([m["monthly_ic"] for m in monthly_ic])
    months = [m["month"] for m in monthly_ic]
    x = np.arange(len(months))

    ax.fill_between(x, cum_ic, alpha=0.3, color=POSITIVE)
    ax.plot(x, cum_ic, marker="o", color=POSITIVE, linewidth=2.5, markersize=8)

    # Endpoint label
    if len(cum_ic) > 0:
        ax.annotate(
            f"${cum_ic[-1]:,.0f}",
            xy=(x[-1], cum_ic[-1]),
            xytext=(8, 8),
            textcoords="offset points",
            fontsize=16,
            fontweight="bold",
            color=POSITIVE,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(months, fontsize=14, rotation=45, ha="right")
    ax.set_ylabel("Cumulative Incremental IC Revenue ($)", fontsize=14)
    ax.set_title("Cumulative Value Delivered", fontsize=20, fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:,.0f}"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)

    total_ic = cum_ic[-1] if len(cum_ic) > 0 else 0
    total_act = sum(m["new_activations"] for m in monthly_ic)
    return f"${total_ic:,.0f} cumulative IC from {total_act:,} activations"


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class EffectivenessProof(AnalysisModule):
    """Effectiveness Proof Analysis -- A18 series."""

    module_id = "insights.effectiveness"
    display_name = "Effectiveness Proof"
    section = "insights"
    required_columns = ()

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Effectiveness proof for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        # A18.1 -- DCTR Progression
        save_to = ctx.paths.charts_dir / "a18_1_dctr_progression.png"
        with chart_figure(figsize=(12, 8), save_path=save_to) as (_fig, ax):
            insight = _draw_dctr_progression(ax, ctx)
        if insight:
            results.append(
                AnalysisResult(
                    slide_id="A18.1",
                    title="DCTR Progression",
                    chart_path=save_to,
                    notes=insight,
                )
            )

        # A18.2 -- Cumulative Value Delivered
        save_to = ctx.paths.charts_dir / "a18_2_cumulative_value.png"
        with chart_figure(figsize=(14, 8), save_path=save_to) as (_fig, ax):
            insight = _draw_cumulative_value(ax, ctx)
        if insight:
            results.append(
                AnalysisResult(
                    slide_id="A18.2",
                    title="Cumulative Value Delivered",
                    chart_path=save_to,
                    notes=insight,
                )
            )

        # A18.3 (Industry Benchmarks) retired -- source data was fabricated.

        if not results:
            return [
                AnalysisResult(
                    slide_id="A18",
                    title="Effectiveness Proof",
                    success=False,
                    error="Insufficient upstream data for effectiveness analysis",
                )
            ]

        return results
