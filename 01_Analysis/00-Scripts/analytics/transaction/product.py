"""Transaction Product Analysis -- structured port of the exec ``product/`` cells.

Migrates ``analytics/product/01_product_data.py`` .. ``10_product_action_summary.py``
into a single ``AnalysisModule``. The arithmetic is preserved verbatim from the
cells (structure changes only); charts read theme cleanly from
``shared/txn_theme`` instead of the mutable exec namespace, and data comes from
``ctx.txn`` instead of ``combined_df`` / ``rewards_df`` globals.

This module is purely additive: the exec ``product/`` cells stay live and feed the
production deck. This module runs only via the equivalence-diff harness and the
unit test until the operator validates old-vs-new numbers on real data (Phase 2/3).

Slide IDs: TXN-PROD-01 .. TXN-PROD-NN (PROD = product's TXN_SECTIONS code).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import matplotlib

os.environ.setdefault("MPLBACKEND", "Agg")
matplotlib.use("Agg", force=True)
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.patheffects as pe  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from loguru import logger  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.gridspec import GridSpec  # noqa: E402

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult  # noqa: E402
from ars_analysis.analytics.registry import register  # noqa: E402
from ars_analysis.pipeline.context import PipelineContext  # noqa: E402
from ars_analysis.shared.txn_theme import (  # noqa: E402
    BRACKET_PALETTE,
    GEN_COLORS,
    GEN_SUBTITLE_Y,
    GEN_TITLE_Y,
    gen_clean_axes,
    gen_fmt_pct,
)

# Denominator framing: product rates are computed against the eligible-filtered
# transaction universe (ctx.txn is eligible-filtered by step_txn_load).
_DENOM_LABEL = "Eligible"


def _safe(fn, label: str, ctx: PipelineContext) -> list[AnalysisResult]:
    """Run a sub-analysis, isolate failures. Ported from dctr.penetration._safe.

    On failure: WARN log + AnomalyFlag(WARN) on the "transaction" manifest
    section so the silent path becomes noisy in the run scorecard / UI card.
    """
    try:
        return fn(ctx)
    except Exception as exc:
        logger.warning("{label} failed: {err}", label=label, err=exc)
        _mf = getattr(ctx, "manifest", None)
        if _mf is not None:
            try:
                from ars_analysis.pipeline.manifest import AnomalyFlag, FlagLevel
                for _sec in _mf.sections:
                    if _sec.name == "transaction":
                        _sec.anomaly_flags.append(AnomalyFlag(
                            level=FlagLevel.WARN,
                            message=f"{label}: {type(exc).__name__}: {exc}",
                        ))
                        break
            except Exception:
                pass
        return [AnalysisResult(slide_id=label, title=label, success=False, error=str(exc))]


@dataclass
class _ProductAgg:
    """Aggregation outputs shared across the chart methods (ported from cell 01)."""

    prod_df: pd.DataFrame
    prod_agg: pd.DataFrame
    prod_monthly: pd.DataFrame
    total_txns_prod: int
    total_accts_prod: int


@register
class ProductAnalysis(AnalysisModule):
    """Card-product transaction analysis (migrated from the exec product/ cells)."""

    module_id = "transaction.product"
    display_name = "Product Analysis"
    section = "transaction"
    section_code = "PROD"  # matches TXN_SECTIONS["product"]["code"]

    def validate(self, ctx: PipelineContext) -> list[str]:
        """Gate on ctx.txn. Returns errors (empty = OK).

        This is what keeps the module dormant on a normal ARS run (where
        ctx.txn is never populated) -- step_analyze skips modules that return
        validation errors.
        """
        if getattr(ctx, "txn", None) is None or ctx.txn.combined is None:
            return ["ctx.txn not populated (TXN data not loaded)"]
        if ctx.txn.rewards is None:
            return ["ctx.txn.rewards not available (product needs rewards Prod Code/Desc)"]
        return []

    # -- Orchestration -------------------------------------------------------

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Product Analysis for {client}", client=ctx.client.client_id)

        agg = self._aggregate(ctx)
        if agg is None or agg.prod_agg.empty:
            logger.warning("Product: no product data after aggregation -- skipping")
            return []

        # Single-writer handoff: publish numeric outputs to ctx.results so the
        # diff harness / downstream can bind to them (the exec path publishes
        # nothing here today).
        ctx.results["transaction.product"] = {
            "tables": {"prod_agg": agg.prod_agg, "prod_monthly": agg.prod_monthly},
            "insights": {
                "total_txns_prod": agg.total_txns_prod,
                "total_accts_prod": agg.total_accts_prod,
                "n_products": int(len(agg.prod_agg)),
                "dominant_product": str(agg.prod_agg.iloc[0]["product_label"]),
                "dominant_txn_pct": float(agg.prod_agg.iloc[0]["txn_pct"]),
            },
        }

        # Chart methods, in exec-cell order. Each is isolated by _safe.
        results: list[AnalysisResult] = []
        results += _safe(lambda c: self._kpi(c, agg), "TXN-PROD-kpi", ctx)
        results += _safe(lambda c: self._distribution(c, agg), "TXN-PROD-dist", ctx)
        results += _safe(lambda c: self._donut(c, agg), "TXN-PROD-donut", ctx)
        results += _safe(lambda c: self._spend_profile(c, agg), "TXN-PROD-spend", ctx)
        results += _safe(lambda c: self._monthly_trend(c, agg), "TXN-PROD-trend", ctx)
        results += _safe(lambda c: self._merchant_heatmap(c, agg), "TXN-PROD-heat", ctx)
        results += _safe(lambda c: self._biz_personal(c, agg), "TXN-PROD-bp", ctx)
        # cell 10 (findings/action summary) publishes data, not a slide.
        self._action_summary(ctx, agg)

        # Assign sequential TXN-PROD-NN slide ids over successful chart slides,
        # mirroring the exec path's sequential chart capture.
        ok = [r for r in results if r.success and r.chart_path is not None]
        for i, r in enumerate(ok, 1):
            r.slide_id = f"TXN-{self.section_code}-{i:02d}"
        # keep failed results (carry their diagnostic slide_id) for visibility
        return results

    # -- Cell 01: master aggregation (numbers -- this is what the diff covers) -

    def _aggregate(self, ctx: PipelineContext) -> _ProductAgg | None:
        rewards = ctx.txn.rewards
        combined = ctx.txn.combined
        needed = {"Acct Number", "Prod Code", "Prod Desc"}
        if rewards is None or not needed.issubset(set(rewards.columns)):
            logger.warning("Product: rewards missing {cols}", cols=needed)
            return None

        prod_subset = rewards[["Acct Number", "Prod Code", "Prod Desc"]].copy()
        prod_subset.columns = ["account_number", "prod_code", "prod_desc"]
        prod_subset["account_number"] = prod_subset["account_number"].astype(str).str.strip()

        # Copy so we never mutate ctx.txn.combined (exec cell 01 mutates in place).
        combined = combined.copy()
        for col in ["prod_code", "prod_desc"]:
            if col in combined.columns:
                combined.drop(columns=col, inplace=True)

        prod_merged = combined.merge(
            prod_subset,
            left_on="primary_account_num",
            right_on="account_number",
            how="left",
        ).drop(columns="account_number")

        prod_merged["product_label"] = prod_merged.apply(
            lambda r: f"{r['prod_code']} - {r['prod_desc']}"
            if pd.notna(r["prod_code"]) and pd.notna(r["prod_desc"])
            else str(r["prod_code"]) if pd.notna(r["prod_code"])
            else "Unknown",
            axis=1,
        )

        prod_df = prod_merged[prod_merged["product_label"] != "Unknown"].copy()
        if len(prod_df) == 0:
            return None

        prod_agg = prod_df.groupby("product_label").agg(
            txn_count=("transaction_date", "count"),
            unique_accounts=("primary_account_num", "nunique"),
            total_spend=("amount", "sum"),
            avg_spend=("amount", "mean"),
            median_spend=("amount", "median"),
        ).reset_index()

        total_txns_prod = len(prod_df)
        total_accts_prod = prod_df["primary_account_num"].nunique()

        prod_agg["txn_pct"] = prod_agg["txn_count"] / total_txns_prod * 100
        prod_agg["spend_pct"] = prod_agg["total_spend"] / prod_agg["total_spend"].sum() * 100
        prod_agg["acct_pct"] = prod_agg["unique_accounts"] / total_accts_prod * 100
        prod_agg["txn_per_account"] = prod_agg["txn_count"] / prod_agg["unique_accounts"]
        prod_agg = prod_agg.sort_values("txn_count", ascending=False).reset_index(drop=True)
        prod_agg["rank"] = range(1, len(prod_agg) + 1)

        top5_products = prod_agg.head(5)["product_label"].tolist()
        prod_monthly = prod_df[prod_df["product_label"].isin(top5_products)].groupby(
            ["year_month", "product_label"]
        ).agg(txn_count=("transaction_date", "count")).reset_index()
        prod_month_totals = prod_df.groupby("year_month").size().reset_index(name="month_total")
        prod_monthly = prod_monthly.merge(prod_month_totals, on="year_month")
        prod_monthly["share_pct"] = prod_monthly["txn_count"] / prod_monthly["month_total"] * 100

        logger.info(
            "Product: {n} products, {a:,} accounts, dominant {p} ({pct:.1f}%)",
            n=len(prod_agg), a=total_accts_prod,
            p=prod_agg.iloc[0]["product_label"][:30], pct=prod_agg.iloc[0]["txn_pct"],
        )
        return _ProductAgg(prod_df, prod_agg, prod_monthly, total_txns_prod, total_accts_prod)

    # -- chart helpers -------------------------------------------------------

    def _charts_dir(self, ctx: PipelineContext):
        d = ctx.paths.charts_dir / "product"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _result(self, slide_id, title, chart_path, agg, excel=None) -> AnalysisResult:
        return AnalysisResult(
            slide_id=slide_id,
            title=title,
            chart_path=chart_path,
            excel_data=excel,
            layout_index=8,
            slide_type="screenshot",
            denominator_label=_DENOM_LABEL,
            denominator_n=int(agg.total_accts_prod),
        )

    # -- Cell 02: KPI dashboard ---------------------------------------------

    def _kpi(self, ctx, agg) -> list[AnalysisResult]:
        pa = agg.prod_agg
        top_prod = pa.iloc[0]
        best_ticket = pa.loc[pa["avg_spend"].idxmax()]
        most_accts = pa.loc[pa["unique_accounts"].idxmax()]

        fig, axes = plt.subplots(1, 4, figsize=(18, 5))
        kpi_data = [
            {"label": "Total Products", "value": f"{len(pa)}",
             "sub": "distinct card products", "color": GEN_COLORS["primary"]},
            {"label": "Dominant Product", "value": f"{top_prod['txn_pct']:.1f}%",
             "sub": str(top_prod["product_label"])[:28], "color": GEN_COLORS["info"]},
            {"label": "Highest Avg Ticket", "value": f"${best_ticket['avg_spend']:.2f}",
             "sub": str(best_ticket["product_label"])[:28], "color": GEN_COLORS["success"]},
            {"label": "Most Accounts", "value": f"{int(most_accts['unique_accounts']):,}",
             "sub": str(most_accts["product_label"])[:28], "color": GEN_COLORS["accent"]},
        ]
        from matplotlib.patches import FancyBboxPatch
        for ax, kpi in zip(axes, kpi_data):
            ax.set_xlim(0, 10)
            ax.set_ylim(0, 10)
            ax.axis("off")
            ax.add_patch(FancyBboxPatch(
                (0.3, 0.3), 9.4, 9.4, boxstyle="round,pad=0.3",
                facecolor=kpi["color"], edgecolor="white", linewidth=3))
            ax.text(5, 6.8, kpi["label"], ha="center", va="center", fontsize=14,
                    fontweight="bold", color="white", alpha=0.85)
            ax.text(5, 4.5, kpi["value"], ha="center", va="center", fontsize=42,
                    fontweight="bold", color="white",
                    path_effects=[pe.withStroke(linewidth=2, foreground=kpi["color"])])
            ax.text(5, 2.3, kpi["sub"], ha="center", va="center", fontsize=12,
                    color="white", alpha=0.8, style="italic")
        fig.suptitle("Card Product Overview", fontsize=28, fontweight="bold",
                     color=GEN_COLORS["dark_text"], y=GEN_TITLE_Y)
        plt.tight_layout()
        path = self._charts_dir(ctx) / "product_kpi.png"
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return [self._result("TXN-PROD-kpi", "Card Product Overview", path, agg,
                             excel={"Products": pa})]

    # -- Cell 03: distribution ----------------------------------------------

    def _distribution(self, ctx, agg) -> list[AnalysisResult]:
        pa = agg.prod_agg
        fig, ax = plt.subplots(figsize=(14, 7))
        plot_data = pa.head(15).sort_values("txn_pct", ascending=True)
        names = [p[:30] for p in plot_data["product_label"]]
        y_pos = range(len(plot_data))
        n = len(plot_data)
        cmap = LinearSegmentedColormap.from_list("prod", [GEN_COLORS["info"], GEN_COLORS["primary"]])
        bar_colors = [plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, max(n - 1, 1))).to_rgba(i)
                      for i in range(n)]
        ax.barh(y_pos, plot_data["txn_pct"], color=bar_colors, edgecolor="white",
                linewidth=0.5, height=0.7)
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(names, fontsize=10, fontweight="bold")
        ax.set_xlabel("% of Transactions", fontsize=13, fontweight="bold", labelpad=8)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
        gen_clean_axes(ax)
        ax.xaxis.grid(True, color=GEN_COLORS["grid"], linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)
        max_val = plot_data["txn_pct"].max()
        for j, (_, row) in enumerate(plot_data.iterrows()):
            ax.text(row["txn_pct"] + max_val * 0.01, j, f"{row['txn_pct']:.1f}%",
                    va="center", fontsize=9, fontweight="bold", color=GEN_COLORS["primary"])
        ax.set_title("Card Product Distribution", fontsize=26, fontweight="bold",
                     color=GEN_COLORS["dark_text"], pad=35, loc="left")
        plt.tight_layout()
        path = self._charts_dir(ctx) / "product_distribution.png"
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return [self._result("TXN-PROD-dist", "Card Product Distribution", path, agg)]

    # -- Cell 04: donut ------------------------------------------------------

    def _donut(self, ctx, agg) -> list[AnalysisResult]:
        pa = agg.prod_agg
        top_n = min(8, len(pa))
        top = pa.head(top_n).copy()
        other_pct = 100 - top["txn_pct"].sum()
        fig = plt.figure(figsize=(14, 7))
        gs = GridSpec(1, 2, width_ratios=[1.2, 0.8], figure=fig)
        ax_donut = fig.add_subplot(gs[0])
        ax_stats = fig.add_subplot(gs[1])
        show_other = other_pct > 0.5
        sizes = list(top["txn_pct"]) + ([other_pct] if show_other else [])
        labels = [p[:20] for p in top["product_label"]] + (["Other"] if show_other else [])
        colors = BRACKET_PALETTE[:top_n] + ([GEN_COLORS["grid"]] if show_other else [])
        _, _, autotexts = ax_donut.pie(
            sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90,
            pctdistance=0.78, wedgeprops=dict(width=0.38, edgecolor="white", linewidth=2),
            textprops={"fontsize": 10, "fontweight": "bold"})
        for t in autotexts:
            t.set_fontsize(9)
            t.set_fontweight("bold")
            t.set_color("white")
        ax_donut.add_artist(plt.Circle((0, 0), 0.58, fc="white"))
        ax_donut.text(0, 0.05, f"{agg.total_txns_prod:,}", ha="center", va="center",
                      fontsize=18, fontweight="bold", color=GEN_COLORS["dark_text"])
        ax_donut.text(0, -0.10, "transactions", ha="center", va="center",
                      fontsize=10, color=GEN_COLORS["muted"])
        ax_stats.axis("off")
        stats_lines = [
            f"Top {top_n} products = {top['txn_pct'].sum():.1f}% of txns", "",
            f"#1: {pa.iloc[0]['product_label'][:30]}",
            f"     {pa.iloc[0]['txn_pct']:.1f}% share, {int(pa.iloc[0]['unique_accounts']):,} accounts", "",
            f"Total products: {len(pa)}",
            f"Total accounts: {agg.total_accts_prod:,}",
            f"Avg ticket range: ${pa['avg_spend'].min():.2f} - ${pa['avg_spend'].max():.2f}",
        ]
        for i, line in enumerate(stats_lines):
            weight = "bold" if i in (0, 2, 5) else "normal"
            color = GEN_COLORS["primary"] if i in (0, 2, 5) else GEN_COLORS["dark_text"]
            ax_stats.text(0.05, 0.92 - i * 0.1, line, fontsize=13, fontweight=weight,
                          color=color, transform=ax_stats.transAxes, va="top")
        fig.suptitle("Card Product Mix", fontsize=26, fontweight="bold",
                     color=GEN_COLORS["dark_text"], y=GEN_TITLE_Y)
        fig.text(0.5, GEN_SUBTITLE_Y, "How is transaction volume distributed across card products?",
                 ha="center", fontsize=13, color=GEN_COLORS["muted"], style="italic")
        plt.tight_layout()
        plt.subplots_adjust(top=0.88)
        path = self._charts_dir(ctx) / "product_donut.png"
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return [self._result("TXN-PROD-donut", "Card Product Mix", path, agg)]

    # -- Cell 05: spend & activity profile ----------------------------------

    def _spend_profile(self, ctx, agg) -> list[AnalysisResult]:
        pa = agg.prod_agg
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
        left = pa.head(10).sort_values("avg_spend", ascending=True)
        y_pos = range(len(left))
        ax1.barh(y_pos, left["avg_spend"], color=GEN_COLORS["primary"],
                 edgecolor="white", linewidth=0.5, height=0.65)
        ax1.set_yticks(list(y_pos))
        ax1.set_yticklabels([p[:22] for p in left["product_label"]], fontsize=10, fontweight="bold")
        ax1.set_xlabel("Avg Ticket ($)", fontsize=13, fontweight="bold", labelpad=8)
        gen_clean_axes(ax1)
        ax1.xaxis.grid(True, color=GEN_COLORS["grid"], linewidth=0.5, alpha=0.7)
        ax1.set_axisbelow(True)
        ax1.set_title("Average Transaction Size", fontsize=20, fontweight="bold",
                      color=GEN_COLORS["primary"], pad=12)
        for j, (_, row) in enumerate(left.iterrows()):
            ax1.text(row["avg_spend"] + 0.3, j, f"${row['avg_spend']:.2f}", va="center",
                     fontsize=9, fontweight="bold", color=GEN_COLORS["primary"])
        right = pa.head(10).sort_values("txn_per_account", ascending=True)
        ax2.barh(y_pos, right["txn_per_account"], color=GEN_COLORS["info"],
                 edgecolor="white", linewidth=0.5, height=0.65)
        ax2.set_yticks(list(y_pos))
        ax2.set_yticklabels([p[:22] for p in right["product_label"]], fontsize=10, fontweight="bold")
        ax2.set_xlabel("Txns per Account", fontsize=13, fontweight="bold", labelpad=8)
        gen_clean_axes(ax2)
        ax2.xaxis.grid(True, color=GEN_COLORS["grid"], linewidth=0.5, alpha=0.7)
        ax2.set_axisbelow(True)
        ax2.set_title("Activity per Account", fontsize=20, fontweight="bold",
                      color=GEN_COLORS["info"], pad=12)
        for j, (_, row) in enumerate(right.iterrows()):
            ax2.text(row["txn_per_account"] + 0.3, j, f"{row['txn_per_account']:.1f}", va="center",
                     fontsize=9, fontweight="bold", color=GEN_COLORS["info"])
        fig.suptitle("Product Spend & Activity Profile", fontsize=26, fontweight="bold",
                     color=GEN_COLORS["dark_text"], y=GEN_TITLE_Y)
        fig.text(0.5, GEN_SUBTITLE_Y,
                 "Which products generate the highest-value and most frequent usage?",
                 ha="center", fontsize=13, color=GEN_COLORS["muted"], style="italic")
        plt.tight_layout()
        plt.subplots_adjust(top=0.88)
        path = self._charts_dir(ctx) / "product_spend_profile.png"
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return [self._result("TXN-PROD-spend", "Product Spend & Activity Profile", path, agg)]

    # -- Cell 06: monthly trend ---------------------------------------------

    def _monthly_trend(self, ctx, agg) -> list[AnalysisResult]:
        pa, pm = agg.prod_agg, agg.prod_monthly
        fig, ax = plt.subplots(figsize=(14, 7))
        colors = [GEN_COLORS["primary"], GEN_COLORS["info"], GEN_COLORS["success"],
                  GEN_COLORS["warning"], GEN_COLORS["accent"]]
        for i, product in enumerate(pa.head(5)["product_label"].tolist()):
            p_data = pm[pm["product_label"] == product].sort_values("year_month")
            if len(p_data) == 0:
                continue
            ym = p_data["year_month"]
            dates = ym.dt.to_timestamp() if hasattr(ym.dtype, "freq") or str(ym.dtype).startswith("period") else pd.to_datetime(ym.astype(str))
            ax.plot(dates, p_data["share_pct"], color=colors[i], linewidth=2.5,
                    label=product[:25], marker="o", markersize=4, zorder=4)
            ax.text(list(dates)[-1], p_data["share_pct"].iloc[-1], f"  {product[:18]}",
                    fontsize=9, fontweight="bold", color=colors[i], va="center")
        ax.set_ylabel("% of Monthly Transactions", fontsize=16, fontweight="bold", labelpad=10)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
        gen_clean_axes(ax)
        ax.yaxis.grid(True, color=GEN_COLORS["grid"], linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.tick_params(axis="x", rotation=45)
        ax.set_title("Card Product Trends Over Time", fontsize=26, fontweight="bold",
                     color=GEN_COLORS["dark_text"], pad=35, loc="left")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, fontsize=10,
                  frameon=False, title="Product")
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.22)
        path = self._charts_dir(ctx) / "product_monthly_trend.png"
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return [self._result("TXN-PROD-trend", "Card Product Trends Over Time", path, agg,
                             excel={"Monthly": pm})]

    # -- Cell 07: product x merchant heatmap --------------------------------

    def _merchant_heatmap(self, ctx, agg) -> list[AnalysisResult]:
        pa, prod_df = agg.prod_agg, agg.prod_df
        if "merchant_consolidated" not in prod_df.columns:
            return []
        import seaborn as sns
        top_prods = pa.head(min(8, len(pa)))["product_label"].tolist()
        top10_merch = prod_df["merchant_consolidated"].value_counts().head(10).index.tolist()
        heat = prod_df[(prod_df["product_label"].isin(top_prods))
                       & (prod_df["merchant_consolidated"].isin(top10_merch))]
        if heat.empty:
            return []
        pivot = pd.crosstab(heat["product_label"], heat["merchant_consolidated"],
                            normalize="index") * 100
        pivot.index = [p[:25] for p in pivot.index]
        pivot.columns = [m[:20] for m in pivot.columns]
        fig, ax = plt.subplots(figsize=(14, 8))
        cmap = LinearSegmentedColormap.from_list(
            "prod_heat", ["#FFFFFF", GEN_COLORS["info"], GEN_COLORS["primary"]])
        sns.heatmap(pivot, annot=True, fmt=".1f", cmap=cmap, linewidths=1, linecolor="white",
                    cbar_kws={"label": "% of Product Txns"}, ax=ax,
                    annot_kws={"fontsize": 10, "fontweight": "bold"})
        ax.set_xlabel("Merchant", fontsize=13, fontweight="bold", labelpad=8)
        ax.set_ylabel("Product", fontsize=13, fontweight="bold", labelpad=8)
        ax.tick_params(axis="x", rotation=45, labelsize=10)
        ax.tick_params(axis="y", rotation=0, labelsize=10)
        ax.set_title("Product-Merchant Spending Patterns", fontsize=26, fontweight="bold",
                     color=GEN_COLORS["dark_text"], pad=35, loc="left")
        plt.tight_layout()
        path = self._charts_dir(ctx) / "product_merchant_heatmap.png"
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return [self._result("TXN-PROD-heat", "Product-Merchant Spending Patterns", path, agg)]

    # -- Cell 08: business vs personal --------------------------------------

    def _biz_personal(self, ctx, agg) -> list[AnalysisResult]:
        pa, prod_df = agg.prod_agg, agg.prod_df
        if "business_flag" not in prod_df.columns:
            return []
        top_prods = pa.head(min(10, len(pa)))["product_label"].tolist()
        bp = prod_df[prod_df["product_label"].isin(top_prods)]
        ct = pd.crosstab(bp["product_label"], bp["business_flag"], normalize="index") * 100
        if "No" in ct.columns:
            ct = ct.sort_values("No", ascending=True)
        fig, ax = plt.subplots(figsize=(14, 7))
        y_pos = range(len(ct))
        bottom = np.zeros(len(ct))
        bp_colors = {"No": GEN_COLORS["success"], "Yes": GEN_COLORS["primary"]}
        bp_labels = {"No": "Personal", "Yes": "Business"}
        for col in ["No", "Yes"]:
            if col in ct.columns:
                ax.barh(y_pos, ct[col], left=bottom, color=bp_colors.get(col, GEN_COLORS["muted"]),
                        label=bp_labels.get(col, col), edgecolor="white", linewidth=0.5, height=0.65)
                bottom += ct[col].values
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels([p[:25] for p in ct.index], fontsize=10, fontweight="bold")
        ax.set_xlabel("% of Product Transactions", fontsize=13, fontweight="bold", labelpad=8)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
        ax.set_xlim(0, 105)
        gen_clean_axes(ax)
        ax.xaxis.grid(True, color=GEN_COLORS["grid"], linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)
        ax.set_title("Business vs Personal by Product", fontsize=26, fontweight="bold",
                     color=GEN_COLORS["dark_text"], pad=35, loc="left")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=12,
                  frameon=False, title="Account Type")
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.12)
        path = self._charts_dir(ctx) / "product_biz_personal.png"
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return [self._result("TXN-PROD-bp", "Business vs Personal by Product", path, agg)]

    # -- Cell 10: findings + actions (data only, no slide -- matches exec) ----

    def _action_summary(self, ctx, agg) -> None:
        pa = agg.prod_agg
        top_prod = pa.iloc[0]
        n_prods = len(pa)
        top3_share = pa.head(3)["txn_pct"].sum()
        min_ticket, max_ticket = pa["avg_spend"].min(), pa["avg_spend"].max()
        min_tpa, max_tpa = pa["txn_per_account"].min(), pa["txn_per_account"].max()
        findings = [
            {"Category": "Dominance",
             "Finding": f"{top_prod['product_label'][:30]} = {top_prod['txn_pct']:.1f}% of txns, "
                        f"{int(top_prod['unique_accounts']):,} accounts",
             "Implication": "Single product dominates -- optimize rewards for this product first",
             "Priority": "High" if top_prod["txn_pct"] > 50 else "Medium"},
            {"Category": "Diversity",
             "Finding": f"{n_prods} products total; top 3 = {top3_share:.1f}% of transactions",
             "Implication": "Product portfolio is "
                            + ("concentrated" if top3_share > 80 else "diversified"),
             "Priority": "Medium"},
            {"Category": "Ticket Range",
             "Finding": f"Avg ticket ranges ${min_ticket:.2f} to ${max_ticket:.2f} across products",
             "Implication": "Different products serve different spending profiles",
             "Priority": "Medium"},
            {"Category": "Usage Intensity",
             "Finding": f"Txns/account range: {min_tpa:.1f} to {max_tpa:.1f} across products",
             "Implication": "Low-activity products may need activation campaigns",
             "Priority": "High" if max_tpa / max(min_tpa, 0.1) > 5 else "Medium"},
        ]
        bucket = ctx.results.setdefault("transaction.product", {})
        bucket.setdefault("tables", {})["findings"] = pd.DataFrame(findings)
