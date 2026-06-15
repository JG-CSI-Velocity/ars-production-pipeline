"""Attrition Cohort Headline -- A9.0.

Single comprehensive KPI slide answering the questions that the
per-dimension slides (A9.1-A9.8) don't headline cleanly:

  - How many accounts opened in the last 12 completed months?
  - How many accounts closed in the last 12 completed months?
  - Net New = L12M opens - L12M closes
  - First-Year Close Rate (overall): of accounts opened in L12M,
    what fraction have already closed within their first 12 months?
  - L12M Attrition Rate: closes / L12M exposure base (the standardized
    attrition denominator -- see _helpers.l12m_attrition)
  - Active vs. closed-lifetime headcount

Plus a monthly trend showing opens vs. closes by month with a net-new
line overlay -- so the reader can see whether the portfolio is growing,
flat, or contracting and where the inflection points are.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.attrition._helpers import (
    _safe,
    attrition_universe,
    l12m_attrition,
    prepare_attrition_data,
    product_col,
)
from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import (
    BAR_ALPHA,
    BAR_EDGE,
    DATA_LABEL_SIZE,
    NEGATIVE,
    POSITIVE,
    TEAL,
    TICK_SIZE,
)
from ars_analysis.pipeline.context import PipelineContext


# ---------------------------------------------------------------------------
# Color palette for the KPI tiles (matches general theme)
# ---------------------------------------------------------------------------

_DARK = "#1B2A4A"
_MUTED = "#6C757D"
_GROWTH = "#2EC4B6"   # teal -- growth signals
_DECAY = "#E63946"    # red  -- decay signals
_INFO = "#457B9D"     # steel blue -- neutral count


def _fmt_count(n: float | int) -> str:
    n = int(round(n))
    if abs(n) >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if abs(n) >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{n:,}"


def _fmt_pct(p: float) -> str:
    return f"{p * 100:.1f}%" if pd.notna(p) else "n/a"


# ---------------------------------------------------------------------------
# A9.0 -- L12M Cohort Headline
# ---------------------------------------------------------------------------


def _l12m_cohort(ctx: PipelineContext) -> list[AnalysisResult]:
    """Top-line attrition KPI panel + monthly opens-vs-closes trend."""
    all_data, open_accts, closed = prepare_attrition_data(ctx)
    if all_data.empty:
        return [
            AnalysisResult(
                slide_id="A9.0",
                title="Account Attrition & Churn (L12M)",
                success=False,
                error="No account data",
            )
        ]

    if "Date Opened" not in all_data.columns or "Date Closed" not in all_data.columns:
        return [
            AnalysisResult(
                slide_id="A9.0",
                title="Account Attrition & Churn (L12M)",
                success=False,
                error="Missing Date Opened / Date Closed",
            )
        ]

    # Anchor the L12M window. Prefer the ctx-provided range (matches the rest
    # of the report); fall back to a 12-month window ending at the latest
    # Date Closed or today.
    if ctx.start_date and ctx.end_date:
        l12m_start = pd.Timestamp(ctx.start_date)
        l12m_end = pd.Timestamp(ctx.end_date)
    else:
        max_close = pd.to_datetime(all_data["Date Closed"], errors="coerce").max()
        l12m_end = pd.Timestamp(max_close if pd.notna(max_close) else pd.Timestamp.today())
        # 12 months inclusive of the end month (months=12 spanned 13 buckets)
        l12m_start = (l12m_end - pd.DateOffset(months=11)).normalize().replace(day=1)

    do = pd.to_datetime(all_data["Date Opened"], errors="coerce")
    dc = pd.to_datetime(all_data["Date Closed"], errors="coerce")

    # ---- Headline counts -------------------------------------------------
    total_accts = len(all_data)
    total_closed_lifetime = int(dc.notna().sum())
    total_active = int(dc.isna().sum())

    l12m_opens_mask = (do >= l12m_start) & (do <= l12m_end)
    l12m_closes_mask = (dc >= l12m_start) & (dc <= l12m_end)
    n_opens = int(l12m_opens_mask.sum())
    n_closes = int(l12m_closes_mask.sum())
    net_new = n_opens - n_closes

    # Accounts open at the START of the L12M window (growth-rate basis only)
    open_at_start = int(((do < l12m_start) & ((dc.isna()) | (dc >= l12m_start))).sum())

    # L12M attrition on the standardized exposure base. The old denominator
    # (open-at-start) excluded window opens whose closures sat in the
    # numerator, overstating the rate -- and disagreed with A9.1 and A9.4.
    l12m_base_df, _, l12m_attrition_rate = l12m_attrition(all_data, l12m_start, l12m_end)
    l12m_base_n = len(l12m_base_df)

    # Eligible-scoped attrition (#208 A2). The same L12M window applied to the
    # eligible-comparable book (open-eligible + closed-eligible-by-product), so
    # the deck shows BOTH denominators instead of leaving the reader to guess
    # which one the single rate used. Falls back to the all-accounts figures
    # when eligibility config is unavailable.
    try:
        elig_universe = attrition_universe(ctx)
        elig_base_df, elig_closures_df, elig_rate = l12m_attrition(
            elig_universe, l12m_start, l12m_end
        )
        elig_base_n = len(elig_base_df)
        elig_closures_n = len(elig_closures_df)
    except Exception as exc:
        logger.warning("A9.0 eligible attrition failed: {e}", e=exc)
        elig_base_n, elig_closures_n, elig_rate = l12m_base_n, n_closes, l12m_attrition_rate

    # First-Year Close Rate (overall): of accounts opened in L12M,
    # how many have already closed within their first 12 months?
    # Closures are capped at l12m_end so the current partial month doesn't
    # leak in (the "L12M Closes" tile next to this one excludes it).
    l12m_opens = all_data[l12m_opens_mask]
    if not l12m_opens.empty:
        opens_dc = pd.to_datetime(l12m_opens["Date Closed"], errors="coerce")
        opens_do = pd.to_datetime(l12m_opens["Date Opened"], errors="coerce")
        days_open = (opens_dc - opens_do).dt.days
        fy_closed = int(
            ((days_open >= 0) & (days_open <= 365) & (opens_dc <= l12m_end)).sum()
        )
        first_year_close_rate = fy_closed / n_opens
    else:
        fy_closed = 0
        first_year_close_rate = float("nan")

    # Growth rate: net new as a % of open_at_start
    growth_rate = (net_new / open_at_start) if open_at_start > 0 else float("nan")

    # ---- Monthly trend ---------------------------------------------------
    do_l12m = do[l12m_opens_mask]
    dc_l12m = dc[l12m_closes_mask]

    month_index = pd.date_range(
        l12m_start.normalize().replace(day=1),
        l12m_end.normalize().replace(day=1),
        freq="MS",
    )

    opens_by_month = (
        do_l12m.dt.to_period("M")
        .value_counts()
        .reindex([p.to_period("M") for p in month_index], fill_value=0)
        .sort_index()
    )
    closes_by_month = (
        dc_l12m.dt.to_period("M")
        .value_counts()
        .reindex([p.to_period("M") for p in month_index], fill_value=0)
        .sort_index()
    )
    net_by_month = opens_by_month - closes_by_month

    # ---- Render ----------------------------------------------------------
    save_to = ctx.paths.charts_dir / "a9_0_cohort_headline.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    with chart_figure(figsize=(20, 11), save_path=save_to) as (fig, _ax_unused):
        _ax_unused.axis("off")
        gs = fig.add_gridspec(
            2, 4,
            height_ratios=[1.0, 1.4],
            hspace=0.55, wspace=0.18,
            left=0.04, right=0.97, top=0.88, bottom=0.10,
        )

        # ----- KPI tiles (top row spans all 4 cols, 2 sub-rows of 4) -----
        # 8 tiles (#208 A2): added the Eligible count and Eligible Closures,
        # folded both attrition denominators (all vs eligible) into one tile, and
        # dropped the redundant growth-rate and the meaningless lifetime-closed
        # count the owner flagged as garbage.
        tiles = [
            (_fmt_count(n_opens),           "L12M Opens",                        _GROWTH),
            (_fmt_count(n_closes),          "L12M Closes",                       _DECAY),
            (("+" if net_new >= 0 else "") + _fmt_count(net_new),
                                            "Net New (L12M)",
                                            _GROWTH if net_new >= 0 else _DECAY),
            (_fmt_count(total_active),      "Open Accounts\n(current, all)",     _INFO),
            (_fmt_count(elig_base_n),       "Eligible Accounts\n(L12M exposure)", _INFO),
            (_fmt_pct(first_year_close_rate),
                                            f"First-Year Close Rate\n({fy_closed:,} of {n_opens:,} new)",
                                            _DECAY),
            (f"{_fmt_pct(l12m_attrition_rate)} / {_fmt_pct(elig_rate)}",
                                            "L12M Attrition\n(All / Eligible)",
                                            _DECAY),
            (_fmt_count(elig_closures_n),   "Eligible Closures\n(L12M)",         _DECAY),
        ]

        # Place the 8 tiles in a 2x4 grid in the TOP gridspec row
        # gs[0,:] is the top row; carve it into a 2x4 nested grid.
        from matplotlib.gridspec import GridSpecFromSubplotSpec
        sub = GridSpecFromSubplotSpec(2, 4, subplot_spec=gs[0, :],
                                      hspace=0.45, wspace=0.18)
        for i, (value, label, color) in enumerate(tiles):
            r, c = divmod(i, 4)
            ax = fig.add_subplot(sub[r, c])
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            card = FancyBboxPatch(
                (0.03, 0.06), 0.94, 0.88,
                boxstyle="round,pad=0.04",
                facecolor=color, alpha=0.10,
                edgecolor=color, linewidth=2.5,
            )
            ax.add_patch(card)
            ax.text(0.5, 0.66, value, transform=ax.transAxes,
                    fontsize=32, fontweight="bold", color=color,
                    ha="center", va="center")
            ax.text(0.5, 0.18, label, transform=ax.transAxes,
                    fontsize=12, fontweight="bold", color=_DARK,
                    ha="center", va="center", linespacing=1.4)

        # ----- Monthly trend (bottom row, spans all 4 cols) -----
        ax = fig.add_subplot(gs[1, :])
        x = np.arange(len(month_index))
        width = 0.4
        ax.bar(x - width / 2, opens_by_month.values, width,
               label="Opens", color=_GROWTH, edgecolor=BAR_EDGE,
               alpha=BAR_ALPHA, zorder=3)
        ax.bar(x + width / 2, closes_by_month.values, width,
               label="Closes", color=_DECAY, edgecolor=BAR_EDGE,
               alpha=BAR_ALPHA, zorder=3)

        ax2 = ax.twinx()
        ax2.plot(x, net_by_month.values, color=_DARK, linewidth=3,
                 marker="o", markersize=8, label="Net New", zorder=5)
        # Net-new value labels at each point (#208 A2: "at least net numbers").
        for xi, nv in zip(x, net_by_month.values):
            ax2.annotate(
                f"{int(nv):+,}", (xi, nv), textcoords="offset points",
                xytext=(0, 9), ha="center", fontsize=10, fontweight="bold",
                color=_DARK, zorder=6,
            )
        ax2.axhline(0, color=_MUTED, linewidth=1, linestyle="--", zorder=2)
        ax2.set_ylabel("Net New", fontsize=14, fontweight="bold", color=_DARK)
        ax2.tick_params(axis="y", labelsize=TICK_SIZE - 4, colors=_DARK)

        ax.set_xticks(x)
        ax.set_xticklabels([d.strftime("%b %y") for d in month_index],
                           fontsize=TICK_SIZE - 4, rotation=0)
        ax.set_ylabel("Accounts", fontsize=14, fontweight="bold")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{int(v):,}"))
        ax.tick_params(axis="y", labelsize=TICK_SIZE - 4)
        ax.set_title("Monthly Opens vs Closes (L12M)",
                     fontsize=18, fontweight="bold", color=_DARK,
                     pad=10, loc="left")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax2.spines["top"].set_visible(False)
        ax.yaxis.grid(True, color="#E9ECEF", linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)

        # Combined legend -- seated above the plot, top-right, so it never runs
        # through the bars or the net-new line (#208 A2: "spacing of legend").
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc="upper right", bbox_to_anchor=(1.0, 1.16),
                  fontsize=12, frameon=False, ncol=3)

        # Suptitle + subtitle with safe spacing
        fig.suptitle("Account Attrition & Churn — Last 12 Months",
                     fontsize=24, fontweight="bold", color=_DARK, y=0.97)
        fig.text(0.5, 0.925,
                 f"Window: {l12m_start.strftime('%b %Y')} – {l12m_end.strftime('%b %Y')}  |  "
                 f"Exposure basis: {l12m_base_n:,} accounts",
                 ha="center", fontsize=13, color=_MUTED, style="italic")

    notes = (
        f"L12M Opens: {n_opens:,} | Closes: {n_closes:,} | Net New: {net_new:+,} "
        f"({_fmt_pct(growth_rate)} growth) | First-Year Close: {_fmt_pct(first_year_close_rate)} "
        f"| L12M Attrition: {_fmt_pct(l12m_attrition_rate)} | "
        f"Active: {total_active:,} | Closed Lifetime: {total_closed_lifetime:,}"
    )

    # Stash structured numbers for downstream slides/Excel tabs
    ctx.results["attrition_cohort"] = {
        "l12m_start": str(l12m_start.date()),
        "l12m_end": str(l12m_end.date()),
        "l12m_opens": n_opens,
        "l12m_closes": n_closes,
        "net_new": net_new,
        "growth_rate": growth_rate,
        "first_year_close_rate": first_year_close_rate,
        "first_year_closed_count": fy_closed,
        "l12m_attrition_rate": l12m_attrition_rate,
        "l12m_exposure_base": l12m_base_n,
        "eligible_exposure_base": elig_base_n,
        "eligible_closures": elig_closures_n,
        "eligible_attrition_rate": elig_rate,
        "open_at_start": open_at_start,
        "active": total_active,
        "closed_lifetime": total_closed_lifetime,
        "total_accounts": total_accts,
        "monthly_opens": opens_by_month.astype(int).tolist(),
        "monthly_closes": closes_by_month.astype(int).tolist(),
        "monthly_net": net_by_month.astype(int).tolist(),
        "month_labels": [d.strftime("%Y-%m") for d in month_index],
    }

    return [
        AnalysisResult(
            slide_id="A9.0",
            title="Account Attrition & Churn — Last 12 Months",
            chart_path=save_to,
            notes=notes,
        )
    ]


# ---------------------------------------------------------------------------
# A9.0b -- Monthly New-Account Cohort Survival
# ---------------------------------------------------------------------------
# Per-month cohort table: for accounts opened in each of the last 12
# completed months, how many are still open vs. already closed -- and
# the % survival rate. Anchors L12M totals at the bottom.


def _l12m_monthly_cohort(ctx: PipelineContext) -> list[AnalysisResult]:
    """Per open-month cohort: Opens, Still Open, Closed, Survival %."""
    all_data, _open, _closed = prepare_attrition_data(ctx)
    if all_data.empty:
        return [
            AnalysisResult(
                slide_id="A9.0b",
                title="Monthly Cohort Survival",
                success=False,
                error="No account data",
            )
        ]
    if "Date Opened" not in all_data.columns or "Date Closed" not in all_data.columns:
        return [
            AnalysisResult(
                slide_id="A9.0b",
                title="Monthly Cohort Survival",
                success=False,
                error="Missing Date Opened / Date Closed",
            )
        ]

    if ctx.start_date and ctx.end_date:
        l12m_start = pd.Timestamp(ctx.start_date)
        l12m_end = pd.Timestamp(ctx.end_date)
    else:
        max_close = pd.to_datetime(all_data["Date Closed"], errors="coerce").max()
        l12m_end = pd.Timestamp(max_close if pd.notna(max_close) else pd.Timestamp.today())
        # 12 months inclusive of the end month (months=12 spanned 13 buckets)
        l12m_start = (l12m_end - pd.DateOffset(months=11)).normalize().replace(day=1)

    do = pd.to_datetime(all_data["Date Opened"], errors="coerce")
    dc = pd.to_datetime(all_data["Date Closed"], errors="coerce")

    # Restrict to L12M opens
    in_window = (do >= l12m_start) & (do <= l12m_end)
    open_period = do[in_window].dt.to_period("M")
    closed_at_obs = dc[in_window].notna()

    # Build per-month rows
    months = pd.period_range(
        l12m_start.to_period("M"),
        l12m_end.to_period("M"),
        freq="M",
    )

    rows = []
    for m in months:
        sel = open_period == m
        opens = int(sel.sum())
        closed = int((sel & closed_at_obs).sum())
        still_open = opens - closed
        survival = (still_open / opens) if opens > 0 else float("nan")
        rows.append({
            "Month Opened": m.strftime("%b %Y"),
            "Opens": opens,
            "Still Open": still_open,
            "Closed": closed,
            "Survival %": survival,
        })

    df = pd.DataFrame(rows)

    # Totals
    tot_opens = int(df["Opens"].sum())
    tot_closed = int(df["Closed"].sum())
    tot_still = int(df["Still Open"].sum())
    tot_survival = (tot_still / tot_opens) if tot_opens > 0 else float("nan")

    # Window closures beyond the new-account cohort (#208 A3). The table above
    # only counts accounts that BOTH opened and closed inside the window; the
    # owner also wants the seasoned closures (opened before the window, closed
    # inside it) and an eligible-vs-other product split of all window closures.
    window_close = (dc >= l12m_start) & (dc <= l12m_end)
    total_window_closes = int(window_close.sum())
    noncohort_closes = int((window_close & (do < l12m_start)).sum())
    # In-window closures from in-window opens. Kept window-consistent with
    # noncohort_closes (the two sum to total_window_closes) -- distinct from the
    # survival table's "Closed" column, which is closed-as-of-now.
    cohort_window_closes = total_window_closes - noncohort_closes
    epc = {
        str(c).strip().upper().removesuffix(".0")
        for c in (getattr(ctx.client, "eligible_prod_codes", None) or [])
    }
    pcol = product_col(all_data)
    if pcol and epc:
        codes = (
            all_data[pcol].astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.upper()
        )
        elig_close = int((window_close & codes.isin(epc)).sum())
        other_close = total_window_closes - elig_close
    else:
        elig_close = other_close = None

    # ----- Render as a styled table figure -----
    save_to = ctx.paths.charts_dir / "a9_0b_monthly_cohort_survival.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    n_rows = len(df) + 4  # header + data + totals + 2 summary lines
    row_h = 0.50
    fig_h = max(8.0, 2.0 + n_rows * row_h)

    with chart_figure(figsize=(15, fig_h), save_path=save_to) as (fig, ax):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, n_rows + 1)
        ax.axis("off")
        ax.invert_yaxis()

        # Title + subtitle (safe spacing)
        fig.suptitle("New-Account Monthly Cohort Survival",
                     fontsize=22, fontweight="bold", color=_DARK, y=0.98)
        fig.text(0.5, 0.935,
                 f"Of accounts opened each month in {l12m_start.strftime('%b %Y')}–"
                 f"{l12m_end.strftime('%b %Y')}, how many are still open?",
                 ha="center", fontsize=13, color=_MUTED, style="italic")

        col_x = [0.06, 0.40, 0.55, 0.70, 0.85]
        headers = ["Month Opened", "Opens", "Still Open", "Closed", "% Survived"]
        for x, h in zip(col_x, headers):
            ax.text(x, 0.6, h, fontsize=13, fontweight="bold",
                    color=_MUTED, ha="left", va="center")
        # Header rule in DATA coords (between the header at y=0.6 and the first
        # row at y=1.5). It was previously drawn in axes coords, so it cut
        # straight through the first data row (#208 A3).
        ax.plot([0.05, 0.95], [1.0, 1.0], color="#E9ECEF", linewidth=1.4)

        for i, row in df.iterrows():
            y = i + 1.5
            ax.text(col_x[0], y, row["Month Opened"], fontsize=14,
                    fontweight="bold", color=_DARK, ha="left", va="center")
            ax.text(col_x[1], y, f"{row['Opens']:,}", fontsize=14,
                    color=_INFO, fontweight="bold", ha="left", va="center")
            ax.text(col_x[2], y, f"{row['Still Open']:,}", fontsize=14,
                    color=_GROWTH, fontweight="bold", ha="left", va="center")
            ax.text(col_x[3], y, f"{row['Closed']:,}", fontsize=14,
                    color=_DECAY, fontweight="bold", ha="left", va="center")
            survival_txt = _fmt_pct(row["Survival %"]) if pd.notna(row["Survival %"]) else "n/a"
            ax.text(col_x[4], y, survival_txt, fontsize=14,
                    fontweight="bold", color=_DARK, ha="left", va="center")
            # Faint divider
            ax.plot([0.05, 0.95], [y + 0.5, y + 0.5], color="#F1F3F5",
                    linewidth=0.5)

        # Totals row
        ty = len(df) + 1.7
        ax.plot([0.05, 0.95], [ty - 0.4, ty - 0.4], color=_DARK, linewidth=1.6)
        ax.text(col_x[0], ty, "L12M TOTAL", fontsize=14, fontweight="bold",
                color=_DARK, ha="left", va="center")
        ax.text(col_x[1], ty, f"{tot_opens:,}", fontsize=14,
                color=_INFO, fontweight="bold", ha="left", va="center")
        ax.text(col_x[2], ty, f"{tot_still:,}", fontsize=14,
                color=_GROWTH, fontweight="bold", ha="left", va="center")
        ax.text(col_x[3], ty, f"{tot_closed:,}", fontsize=14,
                color=_DECAY, fontweight="bold", ha="left", va="center")
        ax.text(col_x[4], ty, _fmt_pct(tot_survival), fontsize=14,
                fontweight="bold", color=_DARK, ha="left", va="center")

        # Window-closure context (#208 A3): seasoned vs cohort, eligible vs other.
        sy = len(df) + 2.9
        ax.text(
            col_x[0], sy,
            f"Closures dated in this window: {total_window_closes:,}  "
            f"= {cohort_window_closes:,} from in-window opens + {noncohort_closes:,} "
            f"seasoned (opened before the window)",
            fontsize=12, color=_DARK, ha="left", va="center",
        )
        if elig_close is not None:
            ax.text(
                col_x[0], sy + 0.75,
                f"By product: {elig_close:,} eligible · {other_close:,} other",
                fontsize=12, color=_MUTED, ha="left", va="center",
            )

    notes = (
        f"L12M new opens: {tot_opens:,} | still open: {tot_still:,} | "
        f"cohort closed: {tot_closed:,} | survival: {_fmt_pct(tot_survival)} | "
        f"window closures: {total_window_closes:,} ({noncohort_closes:,} seasoned)"
    )

    # Stash structured data
    ctx.results["attrition_cohort_monthly"] = df.assign(
        survival_pct=df["Survival %"].astype(float)
    ).drop(columns="Survival %").to_dict(orient="records")

    return [
        AnalysisResult(
            slide_id="A9.0b",
            title="Monthly Cohort Survival",
            chart_path=save_to,
            notes=notes,
        )
    ]


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class AttritionCohortHeadline(AnalysisModule):
    """L12M cohort attrition KPIs (A9.0) + monthly cohort survival (A9.0b)."""

    module_id = "attrition.cohort"
    display_name = "Attrition Cohort Headline"
    section = "attrition"
    required_columns = ("Date Opened", "Date Closed")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        results: list[AnalysisResult] = []
        results += _safe(lambda c: _l12m_cohort(c), "A9.0", ctx)
        results += _safe(lambda c: _l12m_monthly_cohort(c), "A9.0b", ctx)
        return results
