"""A1b: Product Code Distribution -- product mix with personal/business split.

The status-code chart is rendered by stat_codes.py (A1). This module owns the
product-code view: a stacked personal-vs-business bar of the top codes (the
split A1 doesn't show) plus the full distribution as Excel detail.
"""

from __future__ import annotations

import pandas as pd
from loguru import logger

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import BUSINESS, NEUTRAL, PERSONAL
from ars_analysis.pipeline.context import PipelineContext

# Bars beyond this are aggregated into a single "Other" row
_TOP_CODES = 12

_BUSINESS_LABELS = {
    "Yes": "Business",
    "No": "Personal",
    "Y": "Business",
    "N": "Personal",
    "": "Unknown",
    "Unknown": "Unknown",
}


@register
class ProductCodeDistribution(AnalysisModule):
    """Product code breakdown -- Excel detail only (chart is in A1)."""

    module_id = "overview.product_codes"
    display_name = "Product Code Distribution"
    section = "overview"
    required_columns = ("Product Code", "Business?")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A1b: Product Code Distribution for {client}", client=ctx.client.client_id)
        data = ctx.data.copy()
        data["Product Code"] = data["Product Code"].fillna("Unknown")
        data["Business?"] = data["Business?"].fillna("Unknown")

        grouped = data.groupby(["Product Code", "Business?"]).size().reset_index(name="Total Count")
        total = grouped["Total Count"].sum()

        output_rows: list[dict] = []
        summary_rows: list[dict] = []

        for pc in grouped["Product Code"].unique():
            rows = grouped[grouped["Product Code"] == pc]
            prod_total = rows["Total Count"].sum()
            output_rows.append(
                {
                    "Product Code": pc,
                    "Account Type": "All",
                    "Total Count": prod_total,
                    "Percent of Product": prod_total / total if total else 0,
                }
            )

            biz, pers = 0, 0
            for _, r in rows.iterrows():
                label = _BUSINESS_LABELS.get(str(r["Business?"]).strip(), str(r["Business?"]))
                cnt = r["Total Count"]
                if label == "Business":
                    biz = cnt
                elif label == "Personal":
                    pers = cnt
                output_rows.append(
                    {
                        "Product Code": pc,
                        "Account Type": f"  -> {label}",
                        "Total Count": cnt,
                        "Percent of Product": cnt / prod_total if prod_total else 0,
                    }
                )

            summary_rows.append(
                {
                    "Product Code": pc,
                    "Total Count": prod_total,
                    "Percent of Total": prod_total / total if total else 0,
                    "Business Count": biz,
                    "Personal Count": pers,
                }
            )

        distribution = pd.DataFrame(output_rows).sort_values(["Product Code", "Account Type"])
        summary = (
            pd.DataFrame(summary_rows)
            .sort_values("Total Count", ascending=False)
            .reset_index(drop=True)
        )

        top_code = summary.iloc[0]["Product Code"] if len(summary) > 0 else "N/A"
        top_pct = summary.iloc[0]["Percent of Total"] if len(summary) > 0 else 0

        chart_path = self._draw_mix_chart(ctx, summary, total)

        notes = (
            f"Top product '{top_code}': {top_pct:.1%}. "
            f"{len(summary)} product codes. "
            f"Total: {total:,}"
        )

        logger.info(
            "A1b complete -- {n} product codes, top: {top} ({pct:.1%})",
            n=len(summary),
            top=top_code,
            pct=top_pct,
        )
        return [
            AnalysisResult(
                slide_id="A1b",
                title="Product Mix — Personal vs Business",
                chart_path=chart_path,
                excel_data={"Distribution": distribution, "Summary": summary},
                notes=notes,
            )
        ]

    def _draw_mix_chart(self, ctx: PipelineContext, summary: pd.DataFrame, total: int):
        """Stacked horizontal bar: top product codes split personal/business."""
        if ctx.paths.charts_dir == ctx.paths.base_dir or summary.empty or not total:
            return None
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
        save_to = ctx.paths.charts_dir / "a1b_product_mix.png"

        top = summary.head(_TOP_CODES).copy()
        rest = summary.iloc[_TOP_CODES:]
        if len(rest) > 0:
            top = pd.concat([top, pd.DataFrame([{
                "Product Code": f"Other ({len(rest)} codes)",
                "Total Count": rest["Total Count"].sum(),
                "Percent of Total": rest["Percent of Total"].sum(),
                "Business Count": rest["Business Count"].sum(),
                "Personal Count": rest["Personal Count"].sum(),
            }])], ignore_index=True)

        epc = set(ctx.client.eligible_prod_codes or [])
        labels = [
            f"✓ {r['Product Code']}" if r["Product Code"] in epc else str(r["Product Code"])
            for _, r in top.iterrows()
        ]
        pers = top["Personal Count"].astype(float).tolist()
        biz = top["Business Count"].astype(float).tolist()
        # Accounts with an unknown Business? flag still belong on the bar
        unk = (top["Total Count"] - top["Personal Count"] - top["Business Count"]).clip(lower=0).astype(float).tolist()

        try:
            with chart_figure(figsize=(14, 8), save_path=save_to) as (fig, ax):
                y = range(len(top))
                ax.barh(y, pers, color=PERSONAL, label="Personal", zorder=3)
                ax.barh(y, biz, left=pers, color=BUSINESS, label="Business", zorder=3)
                if any(v > 0 for v in unk):
                    ax.barh(y, unk, left=[p + b for p, b in zip(pers, biz)],
                            color=NEUTRAL, label="Unknown", zorder=3)
                ax.set_yticks(list(y))
                ax.set_yticklabels(labels, fontsize=14)
                ax.invert_yaxis()

                xmax = max(t for t in top["Total Count"]) if len(top) else 1
                for i, (_, r) in enumerate(top.iterrows()):
                    # Segment counts inside when they fit
                    for left, width, seg_color in (
                        (0, pers[i], "white"),
                        (pers[i], biz[i], "white"),
                    ):
                        if width > xmax * 0.07:
                            ax.text(left + width / 2, i, f"{width:,.0f}",
                                    ha="center", va="center", fontsize=12,
                                    fontweight="bold", color=seg_color, zorder=4)
                    # Portfolio share at bar end
                    ax.text(r["Total Count"] + xmax * 0.012, i,
                            f"{r['Percent of Total']:.1%}",
                            ha="left", va="center", fontsize=13, fontweight="bold")

                ax.set_xlim(0, xmax * 1.12)
                ax.set_xticks([])
                for spine in ax.spines.values():
                    spine.set_visible(False)
                title = "Product Mix — Personal vs Business"
                if epc:
                    title += "   (✓ = eligible product code)"
                ax.set_title(title, fontsize=20, fontweight="bold", pad=20)
                ax.legend(loc="lower right", fontsize=13)
            return save_to
        except Exception as exc:
            logger.warning("A1b chart failed: {err}", err=exc)
            return None
