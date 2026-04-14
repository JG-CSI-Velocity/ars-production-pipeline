"""Attrition Dimensional Analyses -- A9.4, A9.5, A9.6, A9.7, A9.8.

A9.4  Attrition by Branch
A9.5  Attrition by Product Code
A9.6  Personal vs Business Attrition
A9.7  Attrition by Account Tenure
A9.8  Attrition by Balance Tier

Ported from attrition.py run_attrition_4 through run_attrition_8.
"""

from __future__ import annotations

import pandas as pd
from loguru import logger

from ars_analysis.analytics.attrition._helpers import (
    BALANCE_ORDER,
    TENURE_ORDER,
    _safe,
    categorize_balance,
    categorize_tenure,
    prepare_attrition_data,
    product_col,
)
from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import (
    BAR_ALPHA,
    BAR_EDGE,
    BUSINESS,
    DATA_LABEL_SIZE,
    NEGATIVE,
    PCT_FORMATTER,
    PERSONAL,
    TEAL,
    TICK_SIZE,
)
from ars_analysis.pipeline.context import PipelineContext

# ---------------------------------------------------------------------------
# A9.4 -- Attrition by Branch
# ---------------------------------------------------------------------------


def _apply_branch_map(df: pd.DataFrame, bmap: dict) -> pd.DataFrame:
    """Apply branch mapping to a DataFrame with a Branch column."""
    if bmap and "Branch" in df.columns:
        df = df.copy()
        df["Branch"] = df["Branch"].astype(str).map(lambda b: bmap.get(b, b))
    return df


def _by_branch(ctx: PipelineContext) -> list[AnalysisResult]:
    """L12M attrition rates by branch (annual attrition rate)."""
    all_data, open_accts, closed = prepare_attrition_data(ctx)
    if closed.empty or "Branch" not in all_data.columns:
        return [
            AnalysisResult(
                slide_id="A9.4",
                title="L12M Attrition by Branch",
                success=False,
                error="No closed accounts or no Branch column",
            )
        ]

    bmap = getattr(ctx.settings, "branch_mapping", None) or {}

    # Use the system-wide L12M window
    ctx.compute_l12m_window()
    l12m_closed = closed[ctx.in_l12m(closed["Date Closed"])].copy()

    # Denominator: accounts open at start of L12M window
    # Approximation: currently open + closed in L12M
    l12m_base = pd.concat([open_accts, l12m_closed], ignore_index=True)

    l12m_base = _apply_branch_map(l12m_base, bmap)
    l12m_closed = _apply_branch_map(l12m_closed, bmap)

    total_by = l12m_base.groupby("Branch").size()
    closed_by = l12m_closed.groupby("Branch").size()
    branch_df = (
        pd.DataFrame(
            {"Total": total_by, "Closed": closed_by},
        )
        .fillna(0)
        .astype(int)
    )
    branch_df["Attrition Rate"] = branch_df["Closed"] / branch_df["Total"]
    branch_df = branch_df.sort_values("Attrition Rate").reset_index()

    # Filter to branches with 30+ accounts for plotting
    branch_plot = branch_df[branch_df["Total"] >= 30].copy()
    if branch_plot.empty:
        branch_plot = branch_df.copy()

    overall_rate = branch_df["Closed"].sum() / branch_df["Total"].sum()

    save_to = ctx.paths.charts_dir / "a9_4_branch_attrition.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        ax.barh(
            branch_plot["Branch"].astype(str),
            branch_plot["Attrition Rate"] * 100,
            color=TEAL,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
        )
        ax.axvline(
            overall_rate * 100,
            color=NEGATIVE,
            ls="--",
            lw=2,
            label=f"Average: {overall_rate:.1%}",
        )
        for i, (rate, ct) in enumerate(
            zip(branch_plot["Attrition Rate"], branch_plot["Total"]),
        ):
            ax.text(
                rate * 100 + 0.5,
                i,
                f"{rate:.1%} (n={ct:,})",
                va="center",
                fontsize=DATA_LABEL_SIZE - 4,
            )
        _l12m_label = f"{ctx.l12m_start.strftime('%b %Y')} - {ctx.l12m_end.strftime('%b %Y')}"
        ax.set_title(
            f"L12M Attrition Rate by Branch\n({_l12m_label})",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.set_xlabel("Attrition Rate (%)", fontsize=20)
        ax.xaxis.set_major_formatter(PCT_FORMATTER)
        ax.legend(fontsize=16)
        ax.tick_params(labelsize=TICK_SIZE - 2)
        ax.grid(axis="x", alpha=0.2, linestyle="--")
        ax.set_axisbelow(True)
        ax.text(
            0.98,
            0.95,
            f"L12M Overall: {overall_rate:.1%}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=14,
            fontweight="bold",
            color="#1E3D59",
            bbox={"boxstyle": "round,pad=0.4", "facecolor": "#E8F4FD", "edgecolor": TEAL},
        )
        fig.tight_layout()

    ctx.results["attrition_4"] = {
        "n_branches": len(branch_df),
        "l12m_overall_rate": overall_rate,
        "l12m_closed": len(l12m_closed),
    }

    results = [
        AnalysisResult(
            slide_id="A9.4",
            title="L12M Attrition by Branch",
            chart_path=save_to,
            notes=f"{len(branch_df)} branches, L12M avg {overall_rate:.1%}",
        )
    ]

    # --- A9.4b: First-Year Close Rate by Branch ---
    # Accounts opened in L12M that also closed in L12M
    l12m_opened = all_data[ctx.in_l12m(all_data["Date Opened"])].copy()
    l12m_opened = _apply_branch_map(l12m_opened, bmap)

    if not l12m_opened.empty:
        l12m_opened_and_closed = l12m_opened[l12m_opened["Date Closed"].notna()].copy()

        opened_by = l12m_opened.groupby("Branch").size()
        opened_closed_by = l12m_opened_and_closed.groupby("Branch").size() if not l12m_opened_and_closed.empty else pd.Series(dtype=int)

        fy_df = pd.DataFrame({"Opened": opened_by, "Closed": opened_closed_by}).fillna(0).astype(int)
        fy_df["First-Year Close Rate"] = fy_df["Closed"] / fy_df["Opened"].replace(0, 1)
        fy_df = fy_df.sort_values("First-Year Close Rate").reset_index()
        fy_plot = fy_df[fy_df["Opened"] >= 10].copy()
        if fy_plot.empty:
            fy_plot = fy_df.copy()

        fy_overall = fy_df["Closed"].sum() / max(fy_df["Opened"].sum(), 1)

        save_fy = ctx.paths.charts_dir / "a9_4b_first_year_close_rate.png"
        with chart_figure(figsize=(14, 7), save_path=save_fy) as (fig, ax):
            ax.barh(
                fy_plot["Branch"].astype(str),
                fy_plot["First-Year Close Rate"] * 100,
                color=NEGATIVE,
                edgecolor=BAR_EDGE,
                alpha=BAR_ALPHA,
            )
            ax.axvline(fy_overall * 100, color=TEAL, ls="--", lw=2, label=f"Average: {fy_overall:.1%}")
            for i, (rate, ct) in enumerate(zip(fy_plot["First-Year Close Rate"], fy_plot["Opened"])):
                ax.text(rate * 100 + 0.5, i, f"{rate:.1%} (n={ct:,})", va="center", fontsize=DATA_LABEL_SIZE - 4)
            ax.set_title(f"First-Year Close Rate by Branch\n(Opened & Closed in {_l12m_label})", fontsize=24, fontweight="bold", pad=15)
            ax.set_xlabel("Close Rate (%)", fontsize=20)
            ax.xaxis.set_major_formatter(PCT_FORMATTER)
            ax.legend(fontsize=16)
            ax.tick_params(labelsize=TICK_SIZE - 2)
            ax.grid(axis="x", alpha=0.2, linestyle="--")
            ax.set_axisbelow(True)
            fig.tight_layout()

        results.append(AnalysisResult(
            slide_id="A9.4b",
            title="First-Year Close Rate by Branch",
            chart_path=save_fy,
            notes=f"Overall: {fy_overall:.1%} ({fy_df['Closed'].sum():,} of {fy_df['Opened'].sum():,} new accounts closed)",
        ))

    # --- A9.4c: First-Year Share by Branch ---
    # What % of L12M closures are accounts opened in L12M?
    if not l12m_closed.empty and not l12m_opened.empty:
        l12m_opened_ids = set(l12m_opened.index)
        l12m_closed_new = l12m_closed[l12m_closed.index.isin(l12m_opened_ids)].copy()

        closed_by_branch = l12m_closed.groupby("Branch").size()
        new_closed_by = l12m_closed_new.groupby("Branch").size() if not l12m_closed_new.empty else pd.Series(dtype=int)

        share_df = pd.DataFrame({"All Closed": closed_by_branch, "First-Year Closed": new_closed_by}).fillna(0).astype(int)
        share_df["First-Year Share"] = share_df["First-Year Closed"] / share_df["All Closed"].replace(0, 1)
        share_df = share_df.sort_values("First-Year Share").reset_index()
        share_plot = share_df[share_df["All Closed"] >= 5].copy()
        if share_plot.empty:
            share_plot = share_df.copy()

        share_overall = share_df["First-Year Closed"].sum() / max(share_df["All Closed"].sum(), 1)

        save_share = ctx.paths.charts_dir / "a9_4c_first_year_share.png"
        with chart_figure(figsize=(14, 7), save_path=save_share) as (fig, ax):
            ax.barh(
                share_plot["Branch"].astype(str),
                share_plot["First-Year Share"] * 100,
                color="#FF9F1C",
                edgecolor=BAR_EDGE,
                alpha=BAR_ALPHA,
            )
            ax.axvline(share_overall * 100, color=TEAL, ls="--", lw=2, label=f"Average: {share_overall:.1%}")
            for i, (rate, ct) in enumerate(zip(share_plot["First-Year Share"], share_plot["All Closed"])):
                ax.text(rate * 100 + 0.5, i, f"{rate:.1%} (n={ct:,})", va="center", fontsize=DATA_LABEL_SIZE - 4)
            ax.set_title(f"First-Year Share of Closures by Branch\n(New accounts as % of all closures, {_l12m_label})", fontsize=22, fontweight="bold", pad=15)
            ax.set_xlabel("Share of Closures (%)", fontsize=20)
            ax.xaxis.set_major_formatter(PCT_FORMATTER)
            ax.legend(fontsize=16)
            ax.tick_params(labelsize=TICK_SIZE - 2)
            ax.grid(axis="x", alpha=0.2, linestyle="--")
            ax.set_axisbelow(True)
            fig.tight_layout()

        results.append(AnalysisResult(
            slide_id="A9.4c",
            title="First-Year Share of Closures",
            chart_path=save_share,
            notes=f"Overall: {share_overall:.1%} of closures are first-year accounts",
        ))

    return results


# ---------------------------------------------------------------------------
# A9.5 -- Attrition by Product Code
# ---------------------------------------------------------------------------


def _by_product(ctx: PipelineContext) -> list[AnalysisResult]:
    """Attrition rates by product code."""
    all_data, _, closed = prepare_attrition_data(ctx)
    pcol = product_col(all_data)
    if closed.empty or pcol is None:
        return [
            AnalysisResult(
                slide_id="A9.5",
                title="Attrition by Product",
                success=False,
                error="No closed accounts or no product column",
            )
        ]

    total_by = all_data.groupby(pcol).size()
    closed_by = closed.groupby(pcol).size()
    prod_df = (
        pd.DataFrame(
            {"Total": total_by, "Closed": closed_by},
        )
        .fillna(0)
        .astype(int)
    )
    prod_df["Attrition Rate"] = prod_df["Closed"] / prod_df["Total"]
    prod_df = prod_df.sort_values("Total", ascending=False).head(10).reset_index()

    save_to = ctx.paths.charts_dir / "a9_5_product_attrition.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        ax.bar(
            prod_df[pcol].astype(str),
            prod_df["Attrition Rate"] * 100,
            color=TEAL,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
        )
        for i, rate in enumerate(prod_df["Attrition Rate"]):
            ax.text(
                i,
                rate * 100 + 0.5,
                f"{rate:.1%}",
                ha="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )
        ax.set_title(
            f"Attrition Rate by Product Code (Top {len(prod_df)})",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.set_ylabel("Attrition Rate (%)", fontsize=20)
        ax.yaxis.set_major_formatter(PCT_FORMATTER)
        ax.tick_params(labelsize=TICK_SIZE - 2)
        for lbl in ax.xaxis.get_majorticklabels():
            lbl.set_rotation(45)
            lbl.set_ha("right")
        ax.grid(axis="y", alpha=0.2, linestyle="--")
        ax.set_axisbelow(True)
        overall_rate = prod_df["Closed"].sum() / prod_df["Total"].sum()
        ax.text(
            0.98,
            0.95,
            f"Overall: {overall_rate:.1%}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=14,
            fontweight="bold",
            color="#1E3D59",
            bbox={"boxstyle": "round,pad=0.4", "facecolor": "#E8F4FD", "edgecolor": TEAL},
        )
        fig.tight_layout()

    return [
        AnalysisResult(
            slide_id="A9.5",
            title="Attrition by Product Code",
            chart_path=save_to,
            notes=f"Top {len(prod_df)} products by volume",
        )
    ]


# ---------------------------------------------------------------------------
# A9.6 -- Personal vs Business
# ---------------------------------------------------------------------------


def _personal_vs_business(ctx: PipelineContext) -> list[AnalysisResult]:
    """Attrition split by personal vs business accounts."""
    all_data, _, closed = prepare_attrition_data(ctx)
    if closed.empty or "Business?" not in all_data.columns:
        return [
            AnalysisResult(
                slide_id="A9.6",
                title="Personal vs Business",
                success=False,
                error="No closed accounts or no Business? column",
            )
        ]

    rows = []
    for btype, label in [("No", "Personal"), ("Yes", "Business")]:
        total = len(all_data[all_data["Business?"] == btype])
        n_closed = len(closed[closed["Business?"] == btype])
        rate = n_closed / total if total > 0 else 0
        rows.append(
            {
                "Type": label,
                "Total": total,
                "Closed": n_closed,
                "Attrition Rate": rate,
            }
        )
    pb_df = pd.DataFrame(rows)

    save_to = ctx.paths.charts_dir / "a9_6_personal_business.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        colors = [PERSONAL, BUSINESS]
        bars = ax.bar(
            pb_df["Type"],
            pb_df["Attrition Rate"] * 100,
            color=colors,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
            width=0.5,
        )
        for bar, row in zip(bars, pb_df.itertuples()):
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.5,
                f"{row._4:.1%}\n({row.Closed:,} / {row.Total:,})",
                ha="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )
        ax.set_title(
            "Attrition: Personal vs Business",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.set_ylabel("Attrition Rate (%)", fontsize=20)
        ax.yaxis.set_major_formatter(PCT_FORMATTER)
        ax.tick_params(labelsize=TICK_SIZE)
        ax.grid(axis="y", alpha=0.2, linestyle="--")
        ax.set_axisbelow(True)
        overall_rate = pb_df["Closed"].sum() / pb_df["Total"].sum()
        ax.text(
            0.98,
            0.95,
            f"Overall: {overall_rate:.1%}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=14,
            fontweight="bold",
            color="#1E3D59",
            bbox={"boxstyle": "round,pad=0.4", "facecolor": "#E8F4FD", "edgecolor": TEAL},
        )
        fig.tight_layout()

    return [
        AnalysisResult(
            slide_id="A9.6",
            title="Personal vs Business Attrition",
            chart_path=save_to,
            notes=(
                f"Personal: {pb_df.iloc[0]['Attrition Rate']:.1%} | "
                f"Business: {pb_df.iloc[1]['Attrition Rate']:.1%}"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# A9.7 -- Attrition by Account Tenure
# ---------------------------------------------------------------------------


def _by_tenure(ctx: PipelineContext) -> list[AnalysisResult]:
    """Attrition rates by account tenure bucket."""
    all_data, _, closed = prepare_attrition_data(ctx)
    if closed.empty:
        return [
            AnalysisResult(
                slide_id="A9.7",
                title="Attrition by Tenure",
                success=False,
                error="No closed accounts",
            )
        ]

    now = pd.Timestamp.now()
    all_copy = all_data.copy()
    all_copy["_tenure_days"] = (now - all_copy["Date Opened"]).dt.days
    all_copy["_tenure_cat"] = all_copy["_tenure_days"].apply(categorize_tenure)

    closed_copy = closed.copy()
    closed_copy["_tenure_days"] = (closed_copy["Date Closed"] - closed_copy["Date Opened"]).dt.days
    closed_copy["_tenure_cat"] = closed_copy["_tenure_days"].apply(
        categorize_tenure,
    )

    total_by = all_copy.groupby("_tenure_cat").size()
    closed_by = closed_copy.groupby("_tenure_cat").size()
    tenure_df = (
        pd.DataFrame(
            {"Total": total_by, "Closed": closed_by},
        )
        .fillna(0)
        .astype(int)
    )
    tenure_df["Attrition Rate"] = tenure_df["Closed"] / tenure_df["Total"]
    tenure_df.index = pd.CategoricalIndex(
        tenure_df.index,
        categories=TENURE_ORDER,
        ordered=True,
    )
    tenure_df = tenure_df.sort_index().reset_index()
    tenure_df.columns = ["Tenure", "Total", "Closed", "Attrition Rate"]

    save_to = ctx.paths.charts_dir / "a9_7_tenure_attrition.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        ax.bar(
            tenure_df["Tenure"].astype(str),
            tenure_df["Attrition Rate"] * 100,
            color=TEAL,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
        )
        for i, rate in enumerate(tenure_df["Attrition Rate"]):
            ax.text(
                i,
                rate * 100 + 0.5,
                f"{rate:.1%}",
                ha="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )
        ax.set_title(
            "Attrition Rate by Account Tenure",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.set_ylabel("Attrition Rate (%)", fontsize=20)
        ax.yaxis.set_major_formatter(PCT_FORMATTER)
        ax.tick_params(labelsize=TICK_SIZE - 2)
        for lbl in ax.xaxis.get_majorticklabels():
            lbl.set_rotation(30)
            lbl.set_ha("right")
        ax.grid(axis="y", alpha=0.2, linestyle="--")
        ax.set_axisbelow(True)
        overall_rate = tenure_df["Closed"].sum() / tenure_df["Total"].sum()
        ax.text(
            0.98,
            0.95,
            f"Overall: {overall_rate:.1%}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=14,
            fontweight="bold",
            color="#1E3D59",
            bbox={"boxstyle": "round,pad=0.4", "facecolor": "#E8F4FD", "edgecolor": TEAL},
        )
        fig.tight_layout()

    return [
        AnalysisResult(
            slide_id="A9.7",
            title="Attrition by Account Tenure",
            chart_path=save_to,
        )
    ]


# ---------------------------------------------------------------------------
# A9.8 -- Attrition by Balance Tier
# ---------------------------------------------------------------------------


def _by_balance(ctx: PipelineContext) -> list[AnalysisResult]:
    """Attrition rates across balance tiers."""
    all_data, _, closed = prepare_attrition_data(ctx)
    if closed.empty or "Avg Bal" not in all_data.columns:
        return [
            AnalysisResult(
                slide_id="A9.8",
                title="Attrition by Balance",
                success=False,
                error="No closed accounts or no Avg Bal column",
            )
        ]

    all_copy = all_data.copy()
    all_copy["_bal_cat"] = all_copy["Avg Bal"].apply(categorize_balance)
    closed_copy = closed.copy()
    closed_copy["_bal_cat"] = closed_copy["Avg Bal"].apply(categorize_balance)

    total_by = all_copy.groupby("_bal_cat").size()
    closed_by = closed_copy.groupby("_bal_cat").size()
    bal_df = (
        pd.DataFrame(
            {"Total": total_by, "Closed": closed_by},
        )
        .fillna(0)
        .astype(int)
    )
    bal_df["Attrition Rate"] = bal_df["Closed"] / bal_df["Total"]
    bal_df.index = pd.CategoricalIndex(
        bal_df.index,
        categories=BALANCE_ORDER,
        ordered=True,
    )
    bal_df = bal_df.sort_index().reset_index()
    bal_df.columns = ["Balance Tier", "Total", "Closed", "Attrition Rate"]

    save_to = ctx.paths.charts_dir / "a9_8_balance_attrition.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        ax.bar(
            bal_df["Balance Tier"].astype(str),
            bal_df["Attrition Rate"] * 100,
            color=TEAL,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
        )
        for i, rate in enumerate(bal_df["Attrition Rate"]):
            ax.text(
                i,
                rate * 100 + 0.5,
                f"{rate:.1%}",
                ha="center",
                fontsize=DATA_LABEL_SIZE - 2,
                fontweight="bold",
            )
        ax.set_title(
            "Attrition Rate by Balance Tier",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.set_ylabel("Attrition Rate (%)", fontsize=20)
        ax.yaxis.set_major_formatter(PCT_FORMATTER)
        ax.tick_params(labelsize=TICK_SIZE - 4)
        for lbl in ax.xaxis.get_majorticklabels():
            lbl.set_rotation(30)
            lbl.set_ha("right")
        ax.grid(axis="y", alpha=0.2, linestyle="--")
        ax.set_axisbelow(True)
        overall_rate = bal_df["Closed"].sum() / bal_df["Total"].sum()
        ax.text(
            0.98,
            0.95,
            f"Overall: {overall_rate:.1%}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=14,
            fontweight="bold",
            color="#1E3D59",
            bbox={"boxstyle": "round,pad=0.4", "facecolor": "#E8F4FD", "edgecolor": TEAL},
        )
        fig.tight_layout()

    return [
        AnalysisResult(
            slide_id="A9.8",
            title="Attrition by Balance Tier",
            chart_path=save_to,
        )
    ]


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class AttritionDimensions(AnalysisModule):
    """Dimensional attrition analyses -- A9.4 through A9.8."""

    module_id = "attrition.dimensions"
    display_name = "Attrition Dimensions"
    section = "attrition"
    required_columns = ("Date Opened", "Date Closed")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info(
            "Attrition Dimensions for {client}",
            client=ctx.client.client_id,
        )
        results: list[AnalysisResult] = []
        results += _safe(lambda c: _by_branch(c), "A9.4", ctx)
        results += _safe(lambda c: _by_product(c), "A9.5", ctx)
        results += _safe(lambda c: _personal_vs_business(c), "A9.6", ctx)
        results += _safe(lambda c: _by_tenure(c), "A9.7", ctx)
        results += _safe(lambda c: _by_balance(c), "A9.8", ctx)
        return results
