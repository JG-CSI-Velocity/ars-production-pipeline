"""Reg E Dimensional Analysis -- age, product, funnels.

Slide IDs: A8.5, A8.6, A8.7, A8.10, A8.11.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.dctr._helpers import debit_mask, filter_l12m
from ars_analysis.analytics.rege._helpers import (
    ACCT_AGE_ORDER,
    HOLDER_AGE_ORDER,
    categorize_account_age,
    categorize_holder_age,
    reg_e_base,
    rege,
    total_row,
)
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import ELIGIBLE, HISTORICAL, NEGATIVE, POSITIVE
from ars_analysis.pipeline.context import PipelineContext
from ars_analysis.shared.brand import BRAND
from ars_analysis.shared.charts import draw_box_funnel


def _safe(fn, label: str, ctx: PipelineContext) -> list[AnalysisResult]:
    """Run analysis function, catch errors, return failed result on exception."""
    try:
        return fn(ctx)
    except Exception as exc:
        logger.warning("{label} failed: {err}", label=label, err=exc)
        return [
            AnalysisResult(
                slide_id=label,
                title=label,
                success=False,
                error=str(exc),
            )
        ]


# -- Funnel renderer (same funnel language as the A3 eligibility funnel) ----


def _render_funnel(
    ax, stages: list[dict], title_text: str, subtitle_text: str, metrics_text: str
) -> None:
    """Render a proportional funnel in the DCTR funnel's visual language.

    Thin adapter over shared.charts.draw_box_funnel -- the single renderer
    behind the Reg E, DCTR, and eligibility funnels so they read as one family
    (light canvas, proportional rounded boxes in the brand palette, centered
    number-only labels, left-side stage names, between-stage conversion badges,
    final stage in the brand accent). Output is unchanged from when this drew
    the boxes inline.

    stages: list of dicts with keys: name, total.
    """
    draw_box_funnel(
        ax,
        [s["name"] for s in stages],
        [s["total"] for s in stages],
        title=title_text,
        subtitle=subtitle_text,
        callout=metrics_text,
    )


@register
class RegEDimensions(AnalysisModule):
    """Reg E dimensional analysis -- age, product, funnels."""

    module_id = "rege.dimensions"
    display_name = "Reg E Dimensional Analysis"
    section = "rege"
    required_columns = ("Date Opened", "Debit?", "Business?")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Reg E Dimensions for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        results += _safe(self._account_age, "A8.5", ctx)
        results += _safe(self._holder_age, "A8.6", ctx)
        results += _safe(self._product_code, "A8.7", ctx)
        results += _safe(self._funnel_alltime, "A8.10", ctx)
        results += _safe(self._funnel_l12m, "A8.11", ctx)
        return results

    # -- A8.5: By Account Age -----------------------------------------------

    def _account_age(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.5: Reg E by Account Age")
        base, _, col, opts = reg_e_base(ctx)

        df = base.copy()
        df["Date Opened"] = pd.to_datetime(df["Date Opened"], errors="coerce", format="mixed")
        df["Age Days"] = (pd.Timestamp.now() - df["Date Opened"]).dt.days
        df["Age Range"] = df["Age Days"].apply(categorize_account_age)

        rows = []
        for age in ACCT_AGE_ORDER:
            ad = df[df["Age Range"] == age]
            if len(ad) > 0:
                t, oi, r = rege(ad, col, opts)
                rows.append(
                    {
                        "Account Age": age,
                        "Total Accounts": t,
                        "Opted In": oi,
                        "Opted Out": t - oi,
                        "Opt-In Rate": r,
                    }
                )
        result = pd.DataFrame(rows)
        result = total_row(result, "Account Age")

        # Chart
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_5_reg_e_acct_age.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        chart = result[result["Account Age"] != "TOTAL"].copy()
        overall = result[result["Account Age"] == "TOTAL"]["Opt-In Rate"].iloc[0] * 100

        # Wider/shorter landscape aspect so the chart doesn't bleed over the
        # slide number when placed (mirrors the DCTR branch chart fix). No
        # legend on this single-series chart, so only the aspect is adjusted.
        with chart_figure(figsize=(16, 7.2), save_path=save_to) as (fig, ax):
            x = range(len(chart))
            rates = chart["Opt-In Rate"] * 100
            colors = [NEGATIVE if r < overall else POSITIVE for r in rates]

            bars = ax.bar(x, rates, color=colors, edgecolor="none")
            for bar, rate, vol in zip(bars, rates, chart["Total Accounts"]):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.3,
                    f"{rate:.1f}%",
                    ha="center",
                    fontsize=18,
                    fontweight="bold",
                )

            ax.axhline(y=overall, color=BRAND["accent"], linestyle="--", linewidth=2, alpha=0.8)
            ax.text(
                len(chart) - 0.5,
                overall + 0.3,
                f"Avg: {overall:.1f}%",
                ha="right",
                color=BRAND["accent"],
                fontweight="bold",
                fontsize=14,
            )
            ax.set_xticks(list(x))
            ax.set_xticklabels(chart["Account Age"].tolist(), rotation=30, ha="right", fontsize=16)
            ax.set_ylabel("Opt-In Rate (%)", fontsize=20)
            ax.set_title("Reg E Opt-In by Account Age", fontweight="bold", fontsize=24, pad=15)
            ax.tick_params(axis="y", labelsize=18)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
        chart_path = save_to

        newest = chart.iloc[0]["Opt-In Rate"] if not chart.empty else 0
        oldest = chart.iloc[-1]["Opt-In Rate"] if not chart.empty else 0
        trend = "increasing" if oldest > newest else "decreasing"
        notes = f"Rate {trend}s with age. Newest: {newest:.1%}, Oldest: {oldest:.1%}"

        ctx.results["reg_e_5"] = {"data": result}
        return [
            AnalysisResult(
                slide_id="A8.5",
                title="Reg E Opt-In Rate by Account Age (Eligible Personal w/Debit)",
                chart_path=chart_path,
                excel_data={"Account Age": result},
                notes=notes,
            )
        ]

    # -- A8.6: By Account Holder Age -----------------------------------------

    def _holder_age(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.6: Reg E by Holder Age")
        base, base_l12m, col, opts = reg_e_base(ctx)

        def by_holder_age(df: pd.DataFrame) -> pd.DataFrame:
            if df is None or df.empty:
                return pd.DataFrame()
            d = df.copy()
            if "Account Holder Age" in d.columns:
                d["Holder Age"] = pd.to_numeric(d["Account Holder Age"], errors="coerce")
            elif "Birth Date" in d.columns:
                d["Birth Date"] = pd.to_datetime(d["Birth Date"], errors="coerce", format="mixed")
                d["Holder Age"] = (pd.Timestamp.now() - d["Birth Date"]).dt.days / 365.25
            elif "Age" in d.columns:
                d["Holder Age"] = pd.to_numeric(d["Age"], errors="coerce")
            else:
                return pd.DataFrame()

            d["Age Group"] = d["Holder Age"].apply(categorize_holder_age)
            age_rows = []
            for ag in HOLDER_AGE_ORDER:
                seg = d[d["Age Group"] == ag]
                if len(seg) > 0:
                    t, oi, r = rege(seg, col, opts)
                    age_rows.append(
                        {
                            "Age Group": ag,
                            "Total Accounts": t,
                            "Opted In": oi,
                            "Opted Out": t - oi,
                            "Opt-In Rate": r,
                        }
                    )
            res = pd.DataFrame(age_rows)
            return total_row(res, "Age Group") if not res.empty else res

        hist = by_holder_age(base)
        l12m_df = by_holder_age(base_l12m)

        if hist.empty:
            return [
                AnalysisResult(
                    slide_id="A8.6",
                    title="Reg E Opt-In Rate by Holder Age (Eligible Personal w/Debit)",
                    success=False,
                    error="No holder age data (missing age column)",
                )
            ]

        # Chart
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_6_reg_e_holder_age.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        ch = hist[hist["Age Group"] != "TOTAL"].copy()
        cl = (
            l12m_df[l12m_df["Age Group"] != "TOTAL"].copy() if not l12m_df.empty else pd.DataFrame()
        )

        # Wider/shorter landscape aspect so the chart doesn't bleed over the
        # slide number, and the Historical/L12M legend goes below the plot (off
        # all data) -- the same fix applied to the DCTR branch chart.
        with chart_figure(figsize=(16, 7.2), save_path=save_to) as (fig, ax):
            x = np.arange(len(ch))
            w = 0.35
            hist_rates = ch["Opt-In Rate"] * 100
            bars_h = ax.bar(
                x - w / 2, hist_rates, w, label="Historical", color=HISTORICAL, edgecolor="none"
            )
            for bar, rate in zip(bars_h, hist_rates):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.3,
                    f"{rate:.1f}%",
                    ha="center",
                    fontsize=16,
                    fontweight="bold",
                )

            if not cl.empty:
                l12m_rates = []
                for ag in ch["Age Group"]:
                    match = cl[cl["Age Group"] == ag]
                    l12m_rates.append(match["Opt-In Rate"].iloc[0] * 100 if not match.empty else 0)
                bars_l = ax.bar(
                    x + w / 2, l12m_rates, w, label="L12M", color=ELIGIBLE, edgecolor="none"
                )
                for bar, rate, h_rate in zip(bars_l, l12m_rates, hist_rates):
                    if rate > 0:
                        ax.text(
                            bar.get_x() + bar.get_width() / 2,
                            bar.get_height() + 0.3,
                            f"{rate:.1f}%",
                            ha="center",
                            fontsize=16,
                            fontweight="bold",
                        )
                        # pp change annotation
                        pp = rate - h_rate
                        if abs(pp) > 0.1:
                            sign = "+" if pp > 0 else ""
                            color = POSITIVE if pp > 0 else NEGATIVE
                            ax.text(
                                bar.get_x() + bar.get_width() / 2,
                                bar.get_height() + 2.5,
                                f"{sign}{pp:.1f}pp",
                                ha="center",
                                fontsize=11,
                                fontweight="bold",
                                color=color,
                            )

            # Reference line for overall rate
            overall_row = ch if ch.empty else hist[hist["Age Group"] == "TOTAL"]
            if not overall_row.empty:
                ov = overall_row["Opt-In Rate"].iloc[0] * 100
                ax.axhline(y=ov, color=BRAND["accent"], linestyle="--", linewidth=2, alpha=0.8)
                ax.text(
                    len(ch) - 0.5,
                    ov + 0.3,
                    f"Avg: {ov:.1f}%",
                    ha="right",
                    color=BRAND["accent"],
                    fontweight="bold",
                    fontsize=14,
                )

            ax.set_xticks(x)
            ax.set_xticklabels(ch["Age Group"].tolist(), rotation=30, ha="right", fontsize=16)
            ax.set_ylabel("Opt-In Rate (%)", fontsize=20)
            ax.set_title(
                "Reg E Opt-In by Account Holder Age", fontweight="bold", fontsize=24, pad=15
            )
            ax.tick_params(axis="y", labelsize=18)
            # Legend below the plot (off all data) so it never overlaps the bars.
            ax.legend(
                loc="upper center", bbox_to_anchor=(0.5, -0.22),
                fontsize=16, frameon=False, ncol=3,
            )
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
        chart_path = save_to

        best = ch.loc[ch["Opt-In Rate"].idxmax()]
        worst = ch.loc[ch["Opt-In Rate"].idxmin()]
        notes = (
            f"Best: {best['Age Group']} ({best['Opt-In Rate']:.1%}). "
            f"Worst: {worst['Age Group']} ({worst['Opt-In Rate']:.1%})"
        )

        ctx.results["reg_e_6"] = {"historical": hist, "l12m": l12m_df}
        return [
            AnalysisResult(
                slide_id="A8.6",
                title="Reg E by Holder Age",
                chart_path=chart_path,
                excel_data={"Holder Age": hist},
                notes=notes,
            )
        ]

    # -- A8.7: By Product Code -----------------------------------------------

    def _product_code(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.7: Reg E by Product Code")
        base, _, col, opts = reg_e_base(ctx)

        pc_col = None
        for candidate in ("Product Code", "Prod Code"):
            if candidate in base.columns:
                pc_col = candidate
                break
        if pc_col is None:
            return [
                AnalysisResult(
                    slide_id="A8.7",
                    title="Reg E Opt-In Rate by Product Code (Eligible Personal w/Debit)",
                    success=False,
                    error="No Product Code column found",
                )
            ]

        rows = []
        for pc in sorted(base[pc_col].dropna().unique()):
            seg = base[base[pc_col] == pc]
            t, oi, r = rege(seg, col, opts)
            rows.append(
                {
                    "Product Code": pc,
                    "Total Accounts": t,
                    "Opted In": oi,
                    "Opted Out": t - oi,
                    "Opt-In Rate": r,
                }
            )
        result = pd.DataFrame(rows)
        if result.empty:
            return [
                AnalysisResult(
                    slide_id="A8.7",
                    title="Reg E by Product Code",
                    success=False,
                    error="No product code groups with Reg E data",
                )
            ]
        result = result.sort_values("Total Accounts", ascending=False)
        result = total_row(result, "Product Code")

        # Defensive: in 1745/2026.05 this hit pandas IndexError "single positional
        # indexer is out-of-bounds" because the TOTAL filter returned an empty
        # Series. Compute overall safely, fall back to a weighted average over the
        # real rows if total_row didn't add one, and emit a meaningful error
        # instead of a bare pandas traceback when neither is possible. (#125)
        _total_rows = result[result["Product Code"] == "TOTAL"]
        if not _total_rows.empty:
            overall = float(_total_rows["Opt-In Rate"].iloc[0]) * 100
        elif not result.empty and float(result["Total Accounts"].sum()) > 0:
            _ta = float(result["Total Accounts"].sum())
            _oi = float(result["Opted In"].sum()) if "Opted In" in result.columns else 0.0
            overall = (_oi / _ta) * 100
        else:
            return [
                AnalysisResult(
                    slide_id="A8.7",
                    title="Reg E Opt-In Rate by Product Code (Eligible Personal w/Debit)",
                    success=False,
                    error="Could not compute overall opt-in rate (no product code groups with accounts)",
                )
            ]

        # Chart -- top 15
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_7_reg_e_product.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        chart = result[result["Product Code"] != "TOTAL"].head(15).copy()
        if chart.empty:
            return [
                AnalysisResult(
                    slide_id="A8.7",
                    title="Reg E Opt-In Rate by Product Code (Eligible Personal w/Debit)",
                    success=False,
                    error="No product code rows to chart after filtering TOTAL row",
                )
            ]
        chart = chart.sort_values("Opt-In Rate", ascending=True)

        with chart_figure(figsize=(14, max(8, len(chart) * 0.6)), save_path=save_to) as (fig, ax):
            ax.barh(
                range(len(chart)), chart["Opt-In Rate"] * 100, color=HISTORICAL, edgecolor="none"
            )
            for i, (rate, vol) in enumerate(zip(chart["Opt-In Rate"], chart["Total Accounts"])):
                ax.text(
                    rate * 100 + 0.3,
                    i,
                    f"{rate:.1%} (n={int(vol):,})",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                )
            ax.axvline(x=overall, color=BRAND["accent"], linestyle="--", linewidth=2, alpha=0.8)
            ax.set_yticks(range(len(chart)))
            ax.set_yticklabels(chart["Product Code"].tolist(), fontsize=14)
            ax.set_xlabel("Opt-In Rate (%)", fontsize=20)
            ax.tick_params(axis="x", labelsize=18)
            ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
            ax.set_title(
                "Reg E Opt-In by Product Code (Top 15 by Volume)",
                fontweight="bold",
                fontsize=24,
                pad=15,
            )
        chart_path = save_to

        notes = f"{len(rows)} products. Overall: {overall:.1f}%"
        ctx.results["reg_e_7"] = {"data": result}

        return [
            AnalysisResult(
                slide_id="A8.7",
                title="Reg E by Product Code",
                chart_path=chart_path,
                excel_data={"Product Code": result},
                notes=notes,
            )
        ]

    # -- A8.10: All-Time Account Funnel with Reg E ---------------------------

    def _funnel_alltime(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.10: All-Time Funnel (with Reg E)")
        base, _, col, opts = reg_e_base(ctx)

        total_open = len(ctx.subsets.open_accounts) if ctx.subsets.open_accounts is not None else 0
        total_eligible = (
            len(ctx.subsets.eligible_data) if ctx.subsets.eligible_data is not None else 0
        )
        total_with_debit = (
            len(ctx.subsets.eligible_with_debit)
            if ctx.subsets.eligible_with_debit is not None
            else 0
        )
        personal_w_debit = len(base)
        personal_w_rege = len(base[base[col].isin(opts)])

        stages = [
            {"name": "Open Accounts", "total": total_open},
            {"name": "Eligible Accounts", "total": total_eligible},
            {"name": "Eligible w/Debit", "total": total_with_debit},
            {"name": "Personal w/Debit", "total": personal_w_debit},
            {"name": "Personal w/Reg E", "total": personal_w_rege},
        ]

        funnel_df = pd.DataFrame([{"Stage": s["name"], "Count": s["total"]} for s in stages])

        # Chart
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_10_reg_e_funnel.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        rege_rate = personal_w_rege / personal_w_debit * 100 if personal_w_debit > 0 else 0
        through_rate = personal_w_rege / total_open * 100 if total_open > 0 else 0

        with chart_figure(figsize=(12, 10), save_path=save_to) as (fig, ax):
            _render_funnel(
                ax,
                stages,
                title_text="All-Time Account Eligibility & Reg E Funnel",
                subtitle_text="All-Time Analysis",
                metrics_text=f"Reg E Opt-In: {rege_rate:.1f}% of eligible personal w/debit",
            )
        chart_path = save_to

        notes = (
            f"Open: {total_open:,} -> Reg E: {personal_w_rege:,} "
            f"({rege_rate:.1f}% of personal w/debit)"
        )

        ctx.results["reg_e_10"] = {"funnel": funnel_df}
        return [
            AnalysisResult(
                slide_id="A8.10",
                title="All-Time Funnel with Reg E",
                chart_path=chart_path,
                excel_data={"Funnel": funnel_df},
                notes=notes,
            )
        ]

    # -- A8.11: L12M Funnel with Reg E --------------------------------------

    def _funnel_l12m(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.11: L12M Funnel (with Reg E)")
        _, base_l12m, col, opts = reg_e_base(ctx)

        if base_l12m is None or base_l12m.empty:
            return [
                AnalysisResult(
                    slide_id="A8.11",
                    title="L12M Funnel with Reg E",
                    success=False,
                    error="No L12M data available",
                )
            ]

        # Anchor the funnel to OPEN accounts opened in L12M, matching the DCTR
        # funnel base (dctr/funnel.py uses filter_l12m(open_accounts)). Using
        # last_12_months here counts closed accounts too, inflating the
        # denominator (1,817 vs 1,751) and breaking denominator-law parity with
        # the DCTR funnel -- the eligible step then shows a different % for the
        # identical eligible count.
        oa = ctx.subsets.open_accounts
        if oa is not None and ctx.start_date and ctx.end_date:
            total_l12m = len(filter_l12m(oa, ctx.start_date, ctx.end_date))
        else:
            total_l12m = 0

        # Eligible L12M: filter eligible_data by L12M
        elig_l12m = 0
        el12m_df = pd.DataFrame()
        if ctx.subsets.eligible_data is not None and ctx.start_date and ctx.end_date:
            el12m_df = filter_l12m(ctx.subsets.eligible_data, ctx.start_date, ctx.end_date)
            elig_l12m = len(el12m_df)

        # With debit in L12M
        wd_l12m = 0
        if not el12m_df.empty:
            wd_l12m = int(debit_mask(el12m_df).sum())

        # Personal with debit in L12M
        p_wd_l12m = 0
        if not el12m_df.empty and "Business?" in el12m_df.columns:
            _dm = debit_mask(el12m_df)
            mask = _dm & (
                el12m_df["Business?"].astype(str).str.strip().str.upper().isin(("NO", "N"))
            )
            p_wd_l12m = int(mask.sum())

        # Reg E in L12M personal with debit
        rege_l12m = 0
        if col and p_wd_l12m > 0 and not el12m_df.empty:
            _dm = debit_mask(el12m_df)
            mask = _dm & (
                el12m_df["Business?"].astype(str).str.strip().str.upper().isin(("NO", "N"))
            )
            p_debit_df = el12m_df[mask]
            if col in p_debit_df.columns:
                rege_l12m = int(p_debit_df[col].astype(str).str.strip().isin(opts).sum())

        # Same stage labels as the all-time funnel (A8.10) so the two funnels
        # render at identical size in the 2x1 -- the period is already in the
        # title/subtitle, and differing label widths previously made the tight
        # bbox (and thus the scaled funnel) larger on one side (#208).
        stages = [
            {"name": "Open Accounts", "total": total_l12m},
            {"name": "Eligible Accounts", "total": elig_l12m},
            {"name": "Eligible w/Debit", "total": wd_l12m},
            {"name": "Personal w/Debit", "total": p_wd_l12m},
            {"name": "Personal w/Reg E", "total": rege_l12m},
        ]

        funnel_df = pd.DataFrame([{"Stage": s["name"], "Count": s["total"]} for s in stages])

        # Chart
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_11_reg_e_l12m_funnel.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        rege_rate = rege_l12m / p_wd_l12m * 100 if p_wd_l12m > 0 else 0
        through_rate = rege_l12m / total_l12m * 100 if total_l12m > 0 else 0

        subtitle = "L12M Analysis"
        if ctx.start_date and ctx.end_date:
            subtitle = f"{ctx.start_date.strftime('%B %Y')} - {ctx.end_date.strftime('%B %Y')}"

        with chart_figure(figsize=(12, 10), save_path=save_to) as (fig, ax):
            _render_funnel(
                ax,
                stages,
                title_text="L12M Account Eligibility & Reg E Funnel",
                subtitle_text=subtitle,
                metrics_text=f"Reg E Opt-In: {rege_rate:.1f}% of eligible personal w/debit",
            )
        chart_path = save_to

        notes = (
            f"L12M Opens: {total_l12m:,} -> Reg E: {rege_l12m:,} "
            f"({rege_rate:.1f}% of personal w/debit)"
        )

        ctx.results["reg_e_11"] = {"funnel": funnel_df}
        return [
            AnalysisResult(
                slide_id="A8.11",
                title="L12M Funnel with Reg E",
                chart_path=chart_path,
                excel_data={"Funnel": funnel_df},
                notes=notes,
            )
        ]
