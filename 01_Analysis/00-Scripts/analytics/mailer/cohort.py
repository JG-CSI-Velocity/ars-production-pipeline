"""Responder Cohort Trajectory Analysis -- A16 series.

Proves that ARS mailer responders reverse downward interchange trends.
Slide IDs: A16.1-A16.6 (5-6 slides depending on data depth).
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from loguru import logger

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.mailer._helpers import (
    RESPONSE_SEGMENTS,
    SEGMENT_COLORS,
    build_responder_mask,
    discover_metric_cols,
    discover_pairs,
    parse_month,
)
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import NEGATIVE, POSITIVE, SILVER
from ars_analysis.pipeline.context import PipelineContext

NON_RESP_COLOR = "#404040"
from ars_analysis.shared.brand import BRAND as _BRAND
NAVY = _BRAND["navy"]


# ---------------------------------------------------------------------------
# Cohort construction helpers
# ---------------------------------------------------------------------------


def _find_first_response_month(
    row: pd.Series,
    pairs: list[tuple[str, str, str]],
) -> str | None:
    """Return the first month string where this account responded, or None."""
    for month, resp_col, _mail_col in pairs:
        val = row.get(resp_col)
        if pd.notna(val) and val in RESPONSE_SEGMENTS:
            return month
    return None


def _find_first_response_segment(
    row: pd.Series,
    pairs: list[tuple[str, str, str]],
) -> str | None:
    """Return the response segment from the first response month, or None."""
    for _month, resp_col, _mail_col in pairs:
        val = row.get(resp_col)
        if pd.notna(val) and val in RESPONSE_SEGMENTS:
            return val
    return None


def _month_offset(metric_ts: pd.Timestamp, anchor_ts: pd.Timestamp) -> int:
    """Compute month offset between two timestamps."""
    return (metric_ts.year - anchor_ts.year) * 12 + (metric_ts.month - anchor_ts.month)


def build_cohort_trajectory(
    ctx: PipelineContext,
    metric_type: str,
    by_segment: bool = False,
) -> pd.DataFrame:
    """Build offset-aligned trajectory DataFrame.

    Returns DataFrame with columns: offset, group, avg_value, n_accounts.
    """
    pairs = discover_pairs(ctx)
    spend_cols, swipe_cols = discover_metric_cols(ctx)
    metric_cols = spend_cols if metric_type == "Spend" else swipe_cols

    if not pairs or not metric_cols:
        return pd.DataFrame(columns=["offset", "group", "avg_value", "n_accounts"])

    # Map metric columns to timestamps
    metric_ts_map = {col: parse_month(col) for col in metric_cols}
    metric_ts_map = {k: v for k, v in metric_ts_map.items() if pd.notna(v)}

    if not metric_ts_map:
        return pd.DataFrame(columns=["offset", "group", "avg_value", "n_accounts"])

    data = ctx.data
    resp_mask = build_responder_mask(data, pairs)

    # Find anchor month per account
    earliest_mail_ts = parse_month(pairs[0][0])
    anchors = data.apply(lambda row: _find_first_response_month(row, pairs), axis=1)
    anchor_timestamps = anchors.map(lambda m: parse_month(m) if m else earliest_mail_ts)

    # Segment labels
    if by_segment:
        segments = data.apply(lambda row: _find_first_response_segment(row, pairs), axis=1)
        groups = segments.where(resp_mask, "Non-Responders")
    else:
        groups = pd.Series("Responders", index=data.index)
        groups = groups.where(resp_mask, "Non-Responders")

    # Build long-form records
    records = []
    for col, ts in metric_ts_map.items():
        for idx in data.index:
            offset = _month_offset(ts, anchor_timestamps[idx])
            val = data.at[idx, col]
            if pd.notna(val):
                records.append(
                    {
                        "offset": offset,
                        "group": groups[idx],
                        "value": float(val),
                    }
                )

    if not records:
        return pd.DataFrame(columns=["offset", "group", "avg_value", "n_accounts"])

    long_df = pd.DataFrame(records)
    result = (
        long_df.groupby(["group", "offset"])
        .agg(avg_value=("value", "mean"), n_accounts=("value", "count"))
        .reset_index()
    )
    return result.sort_values(["group", "offset"])


def _compute_slopes(traj_df: pd.DataFrame, group: str) -> tuple[float, float]:
    """Compute pre-M0 and post-M0 average monthly slope for a group."""
    grp = traj_df[traj_df["group"] == group].sort_values("offset")
    pre = grp[grp["offset"] < 0]
    post = grp[grp["offset"] > 0]

    pre_slope = 0.0
    if len(pre) >= 2:
        vals = pre["avg_value"].values
        pre_slope = float(np.mean(np.diff(vals)))

    post_slope = 0.0
    if len(post) >= 2:
        vals = post["avg_value"].values
        post_slope = float(np.mean(np.diff(vals)))

    return pre_slope, post_slope


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------


def _draw_trajectory(
    ax,
    traj_df: pd.DataFrame,
    metric_type: str,
    by_segment: bool = False,
) -> str:
    """Draw offset-aligned trajectory lines. Returns insight text."""
    import matplotlib.ticker as mticker

    groups_in_data = traj_df["group"].unique()

    for group in sorted(groups_in_data):
        grp = traj_df[traj_df["group"] == group].sort_values("offset")
        if group == "Non-Responders":
            color = NON_RESP_COLOR
            ls = "--"
            lw = 2
            ms = 6
        elif group == "Responders":
            color = POSITIVE
            ls = "-"
            lw = 2.5
            ms = 8
        else:
            color = SEGMENT_COLORS.get(group, POSITIVE)
            ls = "-"
            lw = 2.5
            ms = 8

        ax.plot(
            grp["offset"],
            grp["avg_value"],
            marker="o",
            color=color,
            linestyle=ls,
            linewidth=lw,
            markersize=ms,
            label=group,
        )

        # Endpoint label
        if len(grp) > 0:
            last = grp.iloc[-1]
            if metric_type == "Spend":
                lbl = f"${last['avg_value']:,.0f}"
            else:
                lbl = f"{last['avg_value']:,.0f}"
            ax.annotate(
                lbl,
                xy=(last["offset"], last["avg_value"]),
                xytext=(8, 6),
                textcoords="offset points",
                fontsize=12,
                fontweight="bold",
                color=color,
            )

    # Vertical line at M0
    ax.axvline(0, color="#888888", linestyle=":", linewidth=1.5, alpha=0.7)
    ax.text(
        0.02,
        0.97,
        "Response\nMonth",
        transform=ax.transAxes,
        fontsize=11,
        color="#888888",
        va="top",
    )

    title_scope = "Per-Segment" if by_segment else "Responder vs Non-Responder"
    ax.set_title(
        f"{title_scope} {metric_type} Trajectory",
        fontsize=20,
        fontweight="bold",
    )
    ax.set_xlabel("Months Relative to First Response", fontsize=14)
    ylabel = f"Avg {metric_type} per Account"
    if metric_type == "Spend":
        ylabel = f"Avg {metric_type} per Account ($)"
    ax.set_ylabel(ylabel, fontsize=14)

    if metric_type == "Spend":
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:,.0f}"))

    ax.legend(fontsize=14, loc="upper left", frameon=True, fancybox=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)

    # Compute insight
    resp_label = "Responders" if not by_segment else "NU 5+"
    resp_grp = traj_df[traj_df["group"] == resp_label]
    non_grp = traj_df[traj_df["group"] == "Non-Responders"]

    if not resp_grp.empty and not non_grp.empty:
        r_post = resp_grp[resp_grp["offset"] > 0]["avg_value"]
        r_pre = resp_grp[resp_grp["offset"] < 0]["avg_value"]
        n_post = non_grp[non_grp["offset"] > 0]["avg_value"]
        n_pre = non_grp[non_grp["offset"] < 0]["avg_value"]

        r_delta = r_post.mean() - r_pre.mean() if len(r_post) > 0 and len(r_pre) > 0 else 0
        n_delta = n_post.mean() - n_pre.mean() if len(n_post) > 0 and len(n_pre) > 0 else 0

        if metric_type == "Spend":
            return (
                f"Responders: {'+' if r_delta >= 0 else ''}${r_delta:,.0f}/mo | "
                f"Non-Resp: {'+' if n_delta >= 0 else ''}${n_delta:,.0f}/mo"
            )
        return (
            f"Responders: {'+' if r_delta >= 0 else ''}{r_delta:,.0f}/mo | "
            f"Non-Resp: {'+' if n_delta >= 0 else ''}{n_delta:,.0f}/mo"
        )
    return ""


def _draw_direction_bars(
    ax,
    traj_df: pd.DataFrame,
    metric_type: str,
) -> str:
    """Draw grouped bar chart of before/after slopes. Returns insight."""
    groups_to_check = ["Responders", "Non-Responders"]
    # Add segments if present
    for seg in RESPONSE_SEGMENTS:
        if seg in traj_df["group"].values:
            groups_to_check.append(seg)

    labels = []
    before_slopes = []
    after_slopes = []

    for group in groups_to_check:
        if group not in traj_df["group"].values:
            continue
        pre_s, post_s = _compute_slopes(traj_df, group)
        short = group.replace("Non-Responders", "Non-Resp")
        labels.append(short)
        before_slopes.append(pre_s)
        after_slopes.append(post_s)

    if not labels:
        return "No data for direction chart"

    x = np.arange(len(labels))
    width = 0.35

    after_colors = [POSITIVE if s > 0 else NEGATIVE for s in after_slopes]

    ax.bar(x - width / 2, before_slopes, width, label="Before Response", color=SILVER)
    for xi, (val, color) in enumerate(zip(after_slopes, after_colors)):
        ax.bar(xi + width / 2, val, width, color=color, label="After Response" if xi == 0 else None)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=14)
    ax.set_ylabel(f"Avg Monthly {metric_type} Change", fontsize=14)
    ax.set_title(
        f"{metric_type} Direction: Before vs After Response",
        fontsize=20,
        fontweight="bold",
    )
    ax.axhline(0, color="black", linewidth=0.8)
    ax.legend(fontsize=14, loc="upper right", frameon=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)

    # Data labels on bars
    for xi, (bv, av) in enumerate(zip(before_slopes, after_slopes)):
        fmt = "${:+,.0f}" if metric_type == "Spend" else "{:+,.0f}"
        ax.text(
            xi - width / 2,
            bv,
            fmt.format(bv),
            ha="center",
            va="bottom" if bv >= 0 else "top",
            fontsize=12,
            fontweight="bold",
            color="#555",
        )
        ax.text(
            xi + width / 2,
            av,
            fmt.format(av),
            ha="center",
            va="bottom" if av >= 0 else "top",
            fontsize=12,
            fontweight="bold",
            color=POSITIVE if av > 0 else NEGATIVE,
        )

    # Insight
    if "Responders" in labels:
        ri = labels.index("Responders")
        pre_v, post_v = before_slopes[ri], after_slopes[ri]
        if metric_type == "Spend":
            return f"Responders reversed from ${pre_v:+,.0f}/mo to ${post_v:+,.0f}/mo"
        return f"Responders reversed from {pre_v:+,.0f}/mo to {post_v:+,.0f}/mo"
    return ""


def _draw_cohort_size(
    ax,
    traj_df: pd.DataFrame,
) -> str:
    """Draw stacked bar of cohort size at each offset. Returns insight."""
    resp = traj_df[traj_df["group"] != "Non-Responders"]
    non_resp = traj_df[traj_df["group"] == "Non-Responders"]

    resp_agg = resp.groupby("offset")["n_accounts"].sum().sort_index()
    non_agg = non_resp.groupby("offset")["n_accounts"].sum().sort_index()

    offsets = sorted(set(resp_agg.index) | set(non_agg.index))
    r_vals = [resp_agg.get(o, 0) for o in offsets]
    n_vals = [non_agg.get(o, 0) for o in offsets]

    ax.bar(offsets, r_vals, label="Responders", color=POSITIVE, alpha=0.8)
    ax.bar(offsets, n_vals, bottom=r_vals, label="Non-Responders", color=SILVER, alpha=0.8)

    ax.axvline(0, color="#888888", linestyle=":", linewidth=1.5, alpha=0.7)
    ax.set_title("Cohort Size by Month Offset", fontsize=20, fontweight="bold")
    ax.set_xlabel("Months Relative to First Response", fontsize=14)
    ax.set_ylabel("Account Observations", fontsize=14)
    ax.legend(fontsize=14, loc="upper right", frameon=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)

    total_resp = sum(r_vals)
    total_non = sum(n_vals)
    return f"Responders: {total_resp:,} obs | Non-Resp: {total_non:,} obs"


# ---------------------------------------------------------------------------
# A16.7 -- Combo Spend + Swipe lines (per wave)
# ---------------------------------------------------------------------------


def build_combo_lines(
    ctx: PipelineContext,
    pairs: list[tuple[str, str, str]],
    spend_cols: list[str],
    swipe_cols: list[str],
) -> list[AnalysisResult]:
    import os as _os
    import time as _time
    from pathlib import Path as _Path

    # Kill switch that needs NO restart: set env ARS_SKIP_COMBO=1, or drop a
    # file named SKIP_COMBO.flag at the ARS root (M:\ARS). Escape hatch for
    # mid-deadline recovery after this cell hung a production run.
    _flag = _Path(__file__).resolve().parents[4] / "SKIP_COMBO.flag"
    if _os.environ.get("ARS_SKIP_COMBO") == "1" or _flag.exists():
        logger.warning("A16.7 combo lines SKIPPED (kill switch active)")
        return []
    """Per-wave combo chart: 2 rows (Spend top, Swipes bottom) x N segment panels.

    Each panel shows Responder vs Non-Responder avg monthly value, with a
    vertical dashed line at M0 (mail month). One AnalysisResult per wave.
    Slide ID pattern: A16.7.{month}

    Ported from campaign/28_segment_combo_lines.py.
    """
    from ars_analysis.analytics.mailer._helpers import (
        RESPONSE_SEGMENTS,
        parse_month,
    )

    SEG_ORDER = ["NU", "TH-10", "TH-15", "TH-20", "TH-25"]
    SEG_COLORS = {
        "NU": "#457B9D",
        "TH-10": "#2A9D8F",
        "TH-15": "#E9C46A",
        "TH-20": "#F4A261",
        "TH-25": "#E76F51",
    }
    RESP_COLOR = "#2A9D8F"    # teal -- responder line
    NONRESP_COLOR = "#E9C46A"  # amber -- non-responder line
    DARK = _BRAND["navy"]
    MUTED = "#6C757D"
    GRID = "#E8E8E8"

    data = ctx.data
    results: list[AnalysisResult] = []
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    # Build metric column lookups
    spend_lookup = {c.replace(" Spend", ""): c for c in spend_cols}
    swipe_lookup = {c.replace(" Swipes", ""): c for c in swipe_cols}

    # Every wave gets a combo slide: it is each mailer's second slide and
    # replaces the separate swipes/spend slides. NOTE: each figure is expensive
    # -- a full-history run rendered ~3 min/wave (~67 min for ~22 waves). For an
    # emergency fast run, use the kill switch above (ARS_SKIP_COMBO=1 or
    # SKIP_COMBO.flag). Reducing per-wave cost is a separate optimization.
    dated_pairs = sorted(
        (p for p in pairs if not pd.isna(parse_month(p[0]))),
        key=lambda p: parse_month(p[0]),
        reverse=True,
    )

    # Combos are expensive (~min/wave) and only the most-recent waves lead the
    # main deck (deck_builder.MAIN_MAILER_MONTHS = 6); older waves go to the
    # ancillary deck. Render combos only for that recent window so a full-history
    # client doesn't pay ~3 min x ~22 waves (~67 min) -- the regression that
    # pushed runs well past 30 min. Override with ARS_COMBO_MONTHS; 0 = no cap.
    _cap = int(_os.environ.get("ARS_COMBO_MONTHS", "6") or 0)
    if _cap and len(dated_pairs) > _cap:
        # Keep the recent window for the main deck, plus the OLDEST wave -- the
        # "ARS Mailer Revisit" preamble slide features the furthest-back campaign
        # (#208), so its combo must be rendered even though it's outside the
        # recent window. dated_pairs is most-recent-first, so [-1] is the oldest.
        _kept = dated_pairs[:_cap]
        if dated_pairs[-1] not in _kept:
            _kept = _kept + [dated_pairs[-1]]
        logger.info(
            "A16.7: rendering {k} combos ({n} recent + oldest for the revisit); "
            "skipping {s} mid waves. Set ARS_COMBO_MONTHS=0 for all.",
            k=len(_kept), n=_cap, s=len(dated_pairs) - len(_kept),
        )
        dated_pairs = _kept

    for month, resp_col, mail_col in dated_pairs:
        _wave_t0 = _time.monotonic()
        logger.info("A16.7 {month}: starting combo render", month=month)
        mail_date = parse_month(month)

        # Classify accounts for this wave
        was_mailed = data[mail_col].isin(["NU", "TH-10", "TH-15", "TH-20", "TH-25"])
        if was_mailed.sum() == 0:
            continue

        is_resp = data[resp_col].isin(RESPONSE_SEGMENTS)

        # Build segment column: use mail value for everyone mailed
        seg_series = pd.Series("Unknown", index=data.index)
        for seg in ["NU", "TH-10", "TH-15", "TH-20", "TH-25"]:
            seg_series[data[mail_col] == seg] = seg
        # Responders get their actual response tier label
        for resp_val, seg_label in [
            ("NU 5+", "NU"), ("TH-10", "TH-10"), ("TH-15", "TH-15"),
            ("TH-20", "TH-20"), ("TH-25", "TH-25"),
        ]:
            seg_series[(data[resp_col] == resp_val) & is_resp] = seg_label

        # Available segments with enough data (>= 5 accounts in both groups)
        available_segs = []
        for seg in SEG_ORDER:
            seg_mask = was_mailed & (seg_series == seg)
            resp_mask = seg_mask & is_resp
            nonresp_mask = seg_mask & ~is_resp
            if resp_mask.sum() >= 5 and nonresp_mask.sum() >= 5:
                available_segs.append(seg)
        # SEG_ORDER only. The old code added a panel for EVERY distinct
        # non-standard value in the mail column (dates/codes/typos), and the
        # figure is 4in wide per panel -- a polluted column produced a
        # multi-hundred-inch figure that matplotlib ground on for an hour.
        all_segs = available_segs

        if not all_segs:
            continue

        # Identify spend/swipe offset columns relative to mail_date (-6 to +12)
        def get_offset_col(lookup: dict, offset_months: int) -> str | None:
            target = (mail_date + pd.DateOffset(months=offset_months)).strftime("%b%y")
            return lookup.get(target)

        offsets = list(range(-6, 13))
        spend_offset_cols = {o: get_offset_col(spend_lookup, o) for o in offsets}
        swipe_offset_cols = {o: get_offset_col(swipe_lookup, o) for o in offsets}

        # Only keep offsets that have actual columns
        valid_offsets = [
            o for o in offsets
            if spend_offset_cols.get(o) or swipe_offset_cols.get(o)
        ]
        if len(valid_offsets) < 4:
            continue

        has_spend = any(spend_offset_cols.get(o) for o in valid_offsets)
        has_swipes = any(swipe_offset_cols.get(o) for o in valid_offsets)
        n_rows = sum([has_spend, has_swipes])
        if n_rows == 0:
            continue

        n_panels = len(all_segs)
        fig, axes = plt.subplots(
            n_rows, n_panels,
            figsize=(4 * n_panels, 4.5 * n_rows),
            squeeze=False,
        )

        # Row configs: (offset_col_dict, ylabel, y_formatter)
        row_configs = []
        if has_spend:
            row_configs.append((
                spend_offset_cols,
                "Avg Monthly Spend ($)",
                lambda v, _: f"${v:,.0f}",
            ))
        if has_swipes:
            row_configs.append((
                swipe_offset_cols,
                "Avg Monthly Swipes",
                lambda v, _: f"{v:,.0f}",
            ))

        # Sync y-axis per row across segments
        for r_idx, (offset_col_map, ylabel, y_fmt) in enumerate(row_configs):
            row_min, row_max = float("inf"), float("-inf")

            # First pass: compute y range
            for seg in all_segs:
                seg_mask = was_mailed & (seg_series == seg)
                for status_mask in [seg_mask & is_resp, seg_mask & ~is_resp]:
                    if status_mask.sum() < 5:
                        continue
                    for o in valid_offsets:
                        col = offset_col_map.get(o)
                        if col and col in data.columns:
                            vals = pd.to_numeric(
                                data.loc[status_mask, col], errors="coerce"
                            ).dropna()
                            if len(vals) > 0:
                                row_min = min(row_min, vals.mean())
                                row_max = max(row_max, vals.mean())

            if row_min == float("inf"):
                continue
            y_pad = (row_max - row_min) * 0.15 if row_max > row_min else 1
            row_ylim = (max(0, row_min - y_pad), row_max + y_pad)

            # Second pass: draw
            for s_idx, seg in enumerate(all_segs):
                ax = axes[r_idx][s_idx]
                seg_mask = was_mailed & (seg_series == seg)

                plotted = False
                for status, color, lw, marker in [
                    ("Responder", RESP_COLOR, 2.5, "o"),
                    ("Non-Responder", NONRESP_COLOR, 2.0, "s"),
                ]:
                    if status == "Responder":
                        status_mask = seg_mask & is_resp
                    else:
                        status_mask = seg_mask & ~is_resp

                    n = status_mask.sum()
                    if n < 5:
                        continue

                    means = []
                    plot_offsets = []
                    for o in valid_offsets:
                        col = offset_col_map.get(o)
                        if col and col in data.columns:
                            val = pd.to_numeric(
                                data.loc[status_mask, col], errors="coerce"
                            ).mean()
                            if pd.notna(val):
                                means.append(val)
                                plot_offsets.append(o)

                    if len(means) >= 3:
                        ax.plot(
                            plot_offsets, means,
                            color=color, linewidth=lw,
                            marker=marker, markersize=4, markevery=3,
                            label=f"{status} ({n:,})",
                            zorder=3,
                        )
                        plotted = True

                # Mail date vertical line
                ax.axvline(x=0, color=DARK, linewidth=1.2,
                           linestyle="--", alpha=0.5, zorder=2)

                # Segment title -- top row only
                if r_idx == 0:
                    ax.set_title(
                        seg,
                        fontsize=16, fontweight="bold",
                        color=SEG_COLORS.get(seg, DARK), pad=8,
                    )

                # X label -- bottom row only
                if r_idx == n_rows - 1:
                    ax.set_xlabel(
                        "Months from Mail", fontsize=14,
                        fontweight="bold", labelpad=4,
                    )

                # Y label and formatter -- leftmost panel only
                if s_idx == 0:
                    ax.set_ylabel(
                        ylabel, fontsize=14,
                        fontweight="bold", color=DARK, labelpad=6,
                    )
                    import matplotlib.ticker as mticker
                    ax.yaxis.set_major_formatter(mticker.FuncFormatter(y_fmt))

                ax.set_ylim(row_ylim)

                # Legend -- top-left panel only
                if r_idx == 0 and s_idx == 0 and plotted:
                    ax.legend(fontsize=11, loc="upper left", framealpha=0.85)

                # Style
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                ax.yaxis.grid(True, color=GRID, linewidth=0.5, alpha=0.5)
                ax.set_axisbelow(True)
                ax.tick_params(axis="both", labelsize=11)

                if not plotted:
                    ax.text(
                        0.5, 0.5, "No Data",
                        ha="center", va="center",
                        fontsize=12, color=MUTED,
                        transform=ax.transAxes,
                    )

        # Build suptitle with wave stats
        wave_resp = int((was_mailed & is_resp).sum())
        wave_mailed = int(was_mailed.sum())
        wave_rate = wave_resp / wave_mailed * 100 if wave_mailed > 0 else 0
        suptitle = (
            f"Spend + Swipe Trajectory: {month}   |   "
            f"{wave_mailed:,} Mailed   |   "
            f"{wave_resp:,} Responded   |   "
            f"{wave_rate:.1f}% Rate"
        )
        fig.suptitle(suptitle, fontsize=16, fontweight="bold", color=DARK, y=1.02)
        plt.tight_layout()
        plt.subplots_adjust(hspace=0.30)

        save_to = ctx.paths.charts_dir / f"a16_7_{month.lower()}_combo.png"
        fig.savefig(save_to, dpi=150, bbox_inches="tight")
        plt.close(fig)

        logger.info(
            "A16.7 {month}: {n} panels rendered in {secs:.1f}s",
            month=month, n=len(all_segs), secs=_time.monotonic() - _wave_t0,
        )
        results.append(
            AnalysisResult(
                slide_id=f"A16.7.{month}",
                title=(
                    f"Spend + Swipe Trajectory -- {month}: "
                    f"higher-challenge segments show stronger post-mail lift"
                ),
                title_color=NAVY,
                chart_path=save_to,
                notes=(
                    f"Mailed: {wave_mailed:,} | Responded: {wave_resp:,} | "
                    f"Rate: {wave_rate:.1f}% | Segments: {', '.join(all_segs)}"
                ),
            )
        )

    return results


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class ResponderCohort(AnalysisModule):
    """Responder Cohort Trajectory Analysis -- A16 series."""

    module_id = "mailer.cohort"
    display_name = "Responder Cohort Trajectories"
    section = "mailer"
    required_columns = ()

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Cohort trajectories for {client}", client=ctx.client.client_id)
        pairs = discover_pairs(ctx)
        spend_cols, swipe_cols = discover_metric_cols(ctx)

        if not pairs:
            return [
                AnalysisResult(
                    slide_id="A16",
                    title="Cohort Trajectories",
                    success=False,
                    error="No mail/response pairs found",
                )
            ]
        if not spend_cols and not swipe_cols:
            return [
                AnalysisResult(
                    slide_id="A16",
                    title="Cohort Trajectories",
                    success=False,
                    error="No Spend or Swipes columns found",
                )
            ]

        results: list[AnalysisResult] = []
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        # A16.1-A16.6 (trajectory / direction / cohort-size) are dropped from the
        # deck (#208 -- owner flagged them worthless) and have no downstream
        # consumers, yet each build_cohort_trajectory + render is costly (~min).
        # Skip by default; re-enable with ARS_RENDER_DROPPED_MAILER=1. The A16.7
        # combo below is the only cohort slide the deck keeps.
        import os as _os
        _render_dropped = _os.environ.get("ARS_RENDER_DROPPED_MAILER") == "1"

        # A16.1 -- Responder vs Non-Resp Spend Trajectory
        if _render_dropped and spend_cols:
            traj = build_cohort_trajectory(ctx, "Spend", by_segment=False)
            if not traj.empty:
                save_to = ctx.paths.charts_dir / "a16_1_spend_trajectory.png"
                with chart_figure(figsize=(14, 8), save_path=save_to) as (_fig, ax):
                    insight = _draw_trajectory(ax, traj, "Spend")
                results.append(
                    AnalysisResult(
                        slide_id="A16.1",
                        title="Responder Spend Trajectory",
                        chart_path=save_to,
                        notes=insight,
                    )
                )
                ctx.results["a16_spend_traj"] = traj

        # A16.2 -- Responder vs Non-Resp Swipe Trajectory
        if _render_dropped and swipe_cols:
            traj = build_cohort_trajectory(ctx, "Swipes", by_segment=False)
            if not traj.empty:
                save_to = ctx.paths.charts_dir / "a16_2_swipe_trajectory.png"
                with chart_figure(figsize=(14, 8), save_path=save_to) as (_fig, ax):
                    insight = _draw_trajectory(ax, traj, "Swipes")
                results.append(
                    AnalysisResult(
                        slide_id="A16.2",
                        title="Responder Swipe Trajectory",
                        chart_path=save_to,
                        notes=insight,
                    )
                )

        # A16.3 -- Per-Segment Spend Trajectory
        if _render_dropped and spend_cols:
            traj = build_cohort_trajectory(ctx, "Spend", by_segment=True)
            if not traj.empty:
                save_to = ctx.paths.charts_dir / "a16_3_segment_spend.png"
                with chart_figure(figsize=(16, 8), save_path=save_to) as (_fig, ax):
                    insight = _draw_trajectory(ax, traj, "Spend", by_segment=True)
                results.append(
                    AnalysisResult(
                        slide_id="A16.3",
                        title="Per-Segment Spend Trajectory",
                        chart_path=save_to,
                        notes=insight,
                    )
                )

        # A16.4 -- Per-Segment Swipe Trajectory
        if _render_dropped and swipe_cols:
            traj = build_cohort_trajectory(ctx, "Swipes", by_segment=True)
            if not traj.empty:
                save_to = ctx.paths.charts_dir / "a16_4_segment_swipes.png"
                with chart_figure(figsize=(16, 8), save_path=save_to) as (_fig, ax):
                    insight = _draw_trajectory(ax, traj, "Swipes", by_segment=True)
                results.append(
                    AnalysisResult(
                        slide_id="A16.4",
                        title="Per-Segment Swipe Trajectory",
                        chart_path=save_to,
                        notes=insight,
                    )
                )

        # A16.5 -- Direction Change Proof
        if _render_dropped and spend_cols:
            traj_resp = build_cohort_trajectory(ctx, "Spend", by_segment=False)
            if not traj_resp.empty:
                save_to = ctx.paths.charts_dir / "a16_5_direction_change.png"
                with chart_figure(figsize=(14, 8), save_path=save_to) as (_fig, ax):
                    insight = _draw_direction_bars(ax, traj_resp, "Spend")
                results.append(
                    AnalysisResult(
                        slide_id="A16.5",
                        title="Spend Direction Change",
                        chart_path=save_to,
                        notes=insight,
                    )
                )

        # A16.6 -- Cohort Size (optional, only if 8+ metric months)
        metric_count = max(len(spend_cols), len(swipe_cols))
        if _render_dropped and metric_count >= 8:
            traj = build_cohort_trajectory(ctx, "Spend", by_segment=False)
            if not traj.empty:
                save_to = ctx.paths.charts_dir / "a16_6_cohort_size.png"
                with chart_figure(figsize=(14, 8), save_path=save_to) as (_fig, ax):
                    insight = _draw_cohort_size(ax, traj)
                results.append(
                    AnalysisResult(
                        slide_id="A16.6",
                        title="Cohort Size & Retention",
                        chart_path=save_to,
                        notes=insight,
                    )
                )

        # A16.7 -- Combo Spend + Swipe Lines (per wave, paired with A13 mailer summary)
        if spend_cols and swipe_cols:
            try:
                combo_results = build_combo_lines(ctx, pairs, spend_cols, swipe_cols)
                results += combo_results
                logger.info(
                    "A16.7: built {n} combo line slides",
                    n=len(combo_results),
                )
            except Exception as exc:
                logger.warning("A16.7 combo lines failed: {err}", err=exc)

        if not results:
            return [
                AnalysisResult(
                    slide_id="A16",
                    title="Cohort Trajectories",
                    success=False,
                    error="Insufficient data for trajectory analysis",
                )
            ]

        return results
