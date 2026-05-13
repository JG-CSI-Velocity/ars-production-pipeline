"""Reg E Branch Analysis -- per-branch opt-in rates, comparison, scatter, pivot.

Slide IDs: A8.4a, A8.4b, A8.4c, A8.13.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.dctr._helpers import l12m_month_labels
from ars_analysis.analytics.rege._helpers import reg_e_base, rege, total_row
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import (
    HISTORICAL,
    NEGATIVE,
    NEUTRAL,
    POSITIVE,
    SILVER,
    TEAL,
)
from ars_analysis.pipeline.context import PipelineContext


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


def _branch_rates(
    df: pd.DataFrame,
    col: str,
    opts: list[str],
    branch_mapping: dict | None = None,
) -> pd.DataFrame:
    """Calculate Reg E rates by branch for a DataFrame."""
    if df is None or df.empty or "Branch" not in df.columns:
        return pd.DataFrame()
    bm = branch_mapping or {}
    rows = []
    for br in sorted(df["Branch"].dropna().unique()):
        bd = df[df["Branch"] == br]
        t, oi, r = rege(bd, col, opts)
        rows.append(
            {
                "Branch": bm.get(str(br), br),
                "Total Accounts": t,
                "Opted In": oi,
                "Opted Out": t - oi,
                "Opt-In Rate": r,
            }
        )
    result = pd.DataFrame(rows)
    return total_row(result, "Branch") if not result.empty else result


@register
class RegEBranches(AnalysisModule):
    """Reg E opt-in by Branch -- horizontal bars, vertical bars, scatter, pivot."""

    module_id = "rege.branches"
    display_name = "Reg E Branch Analysis"
    section = "rege"
    required_columns = ("Date Opened", "Debit?", "Business?", "Branch")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Reg E Branches for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        # A8.4a eliminated -- data already visible in A8.4b combo chart
        # Still call _branch_comparison to populate ctx.results["reg_e_4"]
        # which A8.4b and A8.4c depend on, but don't include its slide
        _safe(self._branch_comparison, "A8.4a", ctx)
        results += _safe(self._branch_scatter, "A8.4c", ctx)
        results += _safe(self._branch_vertical, "A8.4b", ctx)
        results += _safe(self._branch_pivot, "A8.13", ctx)
        return results

    # -- A8.4a: Branch Historical vs L12M (horizontal bars) ------------------

    def _branch_comparison(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.4a: Reg E by Branch (horizontal)")
        base, base_l12m, col, opts = reg_e_base(ctx)
        bm = getattr(ctx.settings, "branch_mapping", None) if ctx.settings else None

        hist = _branch_rates(base, col, opts, bm)
        l12m = _branch_rates(base_l12m, col, opts, bm) if base_l12m is not None else pd.DataFrame()

        # Build comparison table
        comparison = []
        if not hist.empty:
            branches = hist[hist["Branch"] != "TOTAL"]["Branch"].unique()
            for br in branches:
                h = hist[hist["Branch"] == br]
                l_df = l12m[l12m["Branch"] == br] if not l12m.empty else pd.DataFrame()
                if not h.empty:
                    hr = h["Opt-In Rate"].iloc[0]
                    hv = h["Total Accounts"].iloc[0]
                    lr = l_df["Opt-In Rate"].iloc[0] if not l_df.empty else 0
                    lv = l_df["Total Accounts"].iloc[0] if not l_df.empty else 0
                    comparison.append(
                        {
                            "Branch": br,
                            "Historical Rate": hr,
                            "L12M Rate": lr,
                            "Change": lr - hr,
                            "Historical Volume": hv,
                            "L12M Volume": lv,
                        }
                    )
        comp_df = pd.DataFrame(comparison)
        if not comp_df.empty:
            comp_df = comp_df.sort_values("Historical Rate", ascending=False)

        # Store for A8.4b to reuse
        ctx.results["reg_e_4"] = {"comparison": comp_df, "historical": hist, "l12m": l12m}

        # Chart -- horizontal bar
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_4a_reg_e_branch.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        if not comp_df.empty:
            n = len(comp_df)
            fig_h = max(10, n * 0.6 + 2)
            with chart_figure(
                figsize=(14, fig_h),
                save_path=save_to,
            ) as (fig, ax):
                y = np.arange(n)
                h = 0.35

                ax.barh(
                    y + h / 2,
                    comp_df["Historical Rate"] * 100,
                    h,
                    label="Historical",
                    color=SILVER,
                    edgecolor="black",
                    linewidth=1.5,
                )
                ax.barh(
                    y - h / 2,
                    comp_df["L12M Rate"] * 100,
                    h,
                    label="TTM",
                    color=TEAL,
                    edgecolor="black",
                    linewidth=1.5,
                )

                ax.set_yticks(y)
                ax.set_yticklabels(comp_df["Branch"].values, fontsize=18, fontweight="bold")
                ax.set_xlabel("Opt-In Rate (%)", fontsize=20, fontweight="bold")
                ax.set_title(
                    "Reg E Opt-In by Branch: Historical vs TTM",
                    fontsize=24,
                    fontweight="bold",
                    pad=20,
                )
                ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
                ax.tick_params(axis="x", labelsize=18)
                ax.legend(loc="lower right", fontsize=18)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                ax.set_axisbelow(True)

                # Change indicators (+/- pp)
                for i, (_, row) in enumerate(comp_df.iterrows()):
                    chg = row["Change"] * 100
                    color = POSITIVE if chg > 0 else NEGATIVE if chg < 0 else NEUTRAL
                    marker = "+" if chg > 0 else ""
                    ax.text(
                        max(row["Historical Rate"] * 100, row["L12M Rate"] * 100) + 1,
                        i,
                        f"{marker}{chg:.1f}pp",
                        va="center",
                        fontsize=18,
                        color=color,
                        fontweight="bold",
                    )
            chart_path = save_to

        improving = len(comp_df[comp_df["Change"] > 0]) if not comp_df.empty else 0
        notes = f"{len(comparison)} branches. {improving} improving (L12M > Historical)"

        return [
            AnalysisResult(
                slide_id="A8.4a",
                title="Reg E by Branch (Historical vs L12M)",
                chart_path=chart_path,
                excel_data={"Comparison": comp_df if not comp_df.empty else hist},
                notes=notes,
            )
        ]

    # -- A8.4c: Branch Scatter (volume vs rate) ------------------------------

    def _branch_scatter(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.4c: Reg E Branch Scatter")
        hist = ctx.results.get("reg_e_4", {}).get("historical")
        if hist is None or hist.empty:
            base, _, col, opts = reg_e_base(ctx)
            bm = getattr(ctx.settings, "branch_mapping", None) if ctx.settings else None
            hist = _branch_rates(base, col, opts, bm)

        scatter = hist[hist["Branch"] != "TOTAL"].copy() if not hist.empty else pd.DataFrame()
        if scatter.empty or len(scatter) < 2:
            return [
                AnalysisResult(
                    slide_id="A8.4c",
                    title="Reg E Branch Scatter",
                    success=False,
                    error="Not enough branches for scatter plot",
                )
            ]

        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_4c_reg_e_scatter.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        avg_vol = scatter["Total Accounts"].mean()
        avg_rate = (scatter["Opted In"].sum() / scatter["Total Accounts"].sum()) * 100

        with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
            # Size circles proportional to total accounts
            min_accts = scatter["Total Accounts"].min()
            max_accts = scatter["Total Accounts"].max()
            acct_range = max_accts - min_accts if max_accts > min_accts else 1
            sizes = 100 + (scatter["Total Accounts"] - min_accts) / acct_range * 600
            ax.scatter(
                scatter["Total Accounts"],
                scatter["Opt-In Rate"] * 100,
                s=sizes,
                alpha=0.6,
                color=HISTORICAL,
                edgecolor="black",
                linewidth=2,
            )
            for _, row in scatter.iterrows():
                ax.annotate(
                    row["Branch"],
                    (row["Total Accounts"], row["Opt-In Rate"] * 100),
                    xytext=(6, 6),
                    textcoords="offset points",
                )
            ax.axhline(y=avg_rate, color="red", linestyle="--", alpha=0.5, linewidth=1.5)
            ax.axvline(x=avg_vol, color="red", linestyle="--", alpha=0.5, linewidth=1.5)
            ax.set_xlabel("Total Accounts")
            ax.set_ylabel("Opt-In Rate (%)")
            ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
            ax.set_title("Branch Volume vs Opt-In Rate", fontweight="bold")
            ax.set_axisbelow(True)
        chart_path = save_to

        hv_lr = len(
            scatter[
                (scatter["Total Accounts"] > avg_vol) & (scatter["Opt-In Rate"] * 100 <= avg_rate)
            ]
        )
        notes = f"Avg volume: {avg_vol:,.0f}. Avg rate: {avg_rate:.1f}%. Priority branches: {hv_lr}"

        return [
            AnalysisResult(
                slide_id="A8.4c",
                title="Reg E Branch Scatter",
                chart_path=chart_path,
                notes=notes,
            )
        ]

    # -- A8.4b: Branch L12M Opens vs Opt-In Rate (single-story chart) --------
    # Streamlined per stakeholder feedback: the old version stacked volume
    # bars + historical-rate dashed line + TTM-rate solid line + +/- pp
    # labels above every bar. With many branches it was unreadable.
    # Single story now: how many eligible accounts did each branch OPEN
    # in L12M, and what was their opt-in rate? One bar, one dot, one
    # portfolio-average reference line.

    def _branch_vertical(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.4b: Reg E by Branch (L12M only)")
        comp_df = ctx.results.get("reg_e_4", {}).get("comparison")
        if comp_df is None or comp_df.empty:
            return [
                AnalysisResult(
                    slide_id="A8.4b",
                    title="Reg E Opt-In by Branch (L12M)",
                    success=False,
                    error="No branch comparison data",
                )
            ]

        # Sort by L12M volume (biggest contributor of new opens first).
        chart_data = (
            comp_df.sort_values("L12M Volume", ascending=False)
                   .reset_index(drop=True)
        )
        branches = chart_data["Branch"].tolist()
        n = len(branches)

        l12m_rates = chart_data["L12M Rate"].values * 100
        l12m_vols = chart_data["L12M Volume"].values

        # Portfolio L12M opt-in rate = volume-weighted average across branches
        total_vol = l12m_vols.sum()
        portfolio_rate = (
            (chart_data["L12M Rate"] * chart_data["L12M Volume"]).sum() / total_vol * 100
            if total_vol > 0
            else 0.0
        )

        save_to = ctx.paths.charts_dir / "a8_4b_reg_e_branch_vert.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        fig_w = max(14, n * 1.0 + 2)
        x = np.arange(n)

        with chart_figure(figsize=(fig_w, 9), save_path=save_to) as (fig, ax):
            # Volume bars (L12M eligible accounts opened, by branch)
            ax.bar(
                x,
                l12m_vols,
                color=TEAL,
                edgecolor="white",
                linewidth=1.5,
                width=0.62,
                label="Eligible Accounts Opened (L12M)",
                zorder=2,
            )

            # Value labels on top of each bar (the volume number)
            vol_max = l12m_vols.max() if len(l12m_vols) > 0 else 1
            for i, v in enumerate(l12m_vols):
                ax.text(
                    i, v + vol_max * 0.015, f"{int(v):,}",
                    ha="center", va="bottom",
                    fontsize=13, fontweight="bold", color=_DARK if False else "#1B2A4A",
                )

            ax.set_xticks(x)
            ax.set_xticklabels(branches, fontsize=15, fontweight="bold",
                               rotation=35, ha="right")
            ax.set_ylabel("Eligible Accounts Opened (L12M)",
                          fontsize=18, fontweight="bold")
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
            ax.tick_params(axis="y", labelsize=14)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.set_ylim(0, vol_max * 1.20)
            ax.yaxis.grid(True, color="#E9ECEF", linewidth=0.5, alpha=0.7)
            ax.set_axisbelow(True)

            # Right axis: single L12M opt-in rate dot per branch
            ax2 = ax.twinx()
            ax2.plot(
                x, l12m_rates,
                "o-", color="#1B2A4A",
                linewidth=2.5, markersize=12,
                markerfacecolor="#1B2A4A",
                markeredgecolor="white", markeredgewidth=2,
                label="Opt-In Rate (L12M)",
                zorder=5,
            )

            # Rate label next to each dot
            for i, r in enumerate(l12m_rates):
                ax2.text(
                    i, r + 1.5, f"{r:.1f}%",
                    ha="center", va="bottom",
                    fontsize=12, fontweight="bold",
                    color="#1B2A4A",
                )

            # Portfolio-average reference line (single dashed line)
            ax2.axhline(
                portfolio_rate, color="#E63946",
                linewidth=1.8, linestyle="--",
                alpha=0.85, zorder=3,
                label=f"Portfolio L12M Avg ({portfolio_rate:.1f}%)",
            )

            ax2.set_ylabel("Opt-In Rate", fontsize=18, fontweight="bold")
            ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
            ax2.tick_params(axis="y", labelsize=14)
            # Tight rate axis around the dots
            r_min = max(0, l12m_rates.min() - 5) if len(l12m_rates) > 0 else 0
            r_max = min(100, max(l12m_rates.max(), portfolio_rate) + 8) if len(l12m_rates) > 0 else 100
            ax2.set_ylim(r_min, r_max)
            ax2.spines["top"].set_visible(False)

            # Title + subtitle with safe spacing
            fig.suptitle("Reg E Opt-In by Branch (L12M)",
                         fontsize=22, fontweight="bold",
                         color="#1B2A4A", y=1.00)
            fig.text(0.5, 0.945,
                     "Bars: eligible accounts opened in last 12 completed months  |  "
                     "Dots: opt-in rate of those accounts  |  "
                     f"Red line: portfolio avg ({portfolio_rate:.1f}%)",
                     ha="center", fontsize=12, color="#6C757D", style="italic")

            # Compact two-entry legend (no third change-pp line)
            h1, l1 = ax.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            ax.legend(h1 + h2, l1 + l2,
                      loc="upper right", fontsize=12,
                      frameon=False, ncol=1)

        improving = int((chart_data["L12M Rate"] > chart_data["Historical Rate"]).sum())
        notes = (
            f"{n} branches | Portfolio L12M opt-in: {portfolio_rate:.1f}% | "
            f"{improving} of {n} branches above their historical rate"
        )

        return [
            AnalysisResult(
                slide_id="A8.4b",
                title="Reg E Opt-In by Branch (L12M)",
                chart_path=save_to,
                notes=notes,
            )
        ]

    # -- A8.13: Branch x Month Pivot Table -----------------------------------

    def _branch_pivot(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.13: Branch x Month Pivot")
        base, base_l12m, col, opts = reg_e_base(ctx)
        bm = getattr(ctx.settings, "branch_mapping", None) if ctx.settings else None

        if base_l12m is None or base_l12m.empty:
            return [
                AnalysisResult(
                    slide_id="A8.13",
                    title="Branch x Month Pivot",
                    success=False,
                    error="No L12M data for pivot",
                )
            ]

        l12m_labels = l12m_month_labels(ctx.end_date)
        df = base_l12m.copy()
        df["Month_Year"] = pd.to_datetime(
            df["Date Opened"], errors="coerce", format="mixed"
        ).dt.strftime("%b%y")

        # Apply branch mapping
        if bm:
            df["Branch"] = df["Branch"].astype(str).map(lambda b, _bm=bm: _bm.get(b, b))

        branches = sorted(df["Branch"].dropna().unique())
        pivot_rows = []

        for br in branches:
            row: dict = {"Branch": br}
            br_total = 0
            br_opted = 0
            for my in l12m_labels:
                seg = df[(df["Branch"] == br) & (df["Month_Year"] == my)]
                t = len(seg)
                oi = len(seg[seg[col].astype(str).str.strip().isin(opts)]) if t > 0 else 0
                row[f"{my} Opens"] = t
                row[f"{my} Opt-In"] = oi
                row[f"{my} Rate"] = oi / t if t > 0 else 0
                br_total += t
                br_opted += oi
            row["Total Opens"] = br_total
            row["Total Opt-In"] = br_opted
            row["Overall Rate"] = br_opted / br_total if br_total > 0 else 0
            pivot_rows.append(row)

        pivot = pd.DataFrame(pivot_rows)
        if not pivot.empty:
            pivot = pivot.sort_values("Overall Rate", ascending=False)

            # Grand total row
            totals: dict = {"Branch": "TOTAL"}
            for my in l12m_labels:
                totals[f"{my} Opens"] = pivot[f"{my} Opens"].sum()
                totals[f"{my} Opt-In"] = pivot[f"{my} Opt-In"].sum()
                t_sum = pivot[f"{my} Opens"].sum()
                oi_sum = pivot[f"{my} Opt-In"].sum()
                totals[f"{my} Rate"] = oi_sum / t_sum if t_sum > 0 else 0
            totals["Total Opens"] = pivot["Total Opens"].sum()
            totals["Total Opt-In"] = pivot["Total Opt-In"].sum()
            totals["Overall Rate"] = (
                pivot["Total Opt-In"].sum() / pivot["Total Opens"].sum()
                if pivot["Total Opens"].sum() > 0
                else 0
            )
            pivot = pd.concat([pivot, pd.DataFrame([totals])], ignore_index=True)

        notes = f"{len(branches)} branches x {len(l12m_labels)} months"
        ctx.results["reg_e_13"] = {"pivot": pivot}

        return [
            AnalysisResult(
                slide_id="A8.13",
                title="Branch x Month Pivot",
                excel_data={"Pivot": pivot},
                notes=notes,
            )
        ]
