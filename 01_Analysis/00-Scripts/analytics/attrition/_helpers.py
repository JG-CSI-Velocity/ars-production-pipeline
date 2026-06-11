"""Shared attrition constants, categorization helpers, and data prep.

Ported from attrition.py helpers/categorization sections (~170 lines).
"""

from __future__ import annotations

import pandas as pd
from loguru import logger

from ars_analysis.analytics.base import AnalysisResult
from ars_analysis.pipeline.context import PipelineContext

# ---------------------------------------------------------------------------
# Ordered category constants
# ---------------------------------------------------------------------------

DURATION_ORDER = [
    "0-1 Month",
    "1-3 Months",
    "3-6 Months",
    "6-12 Months",
    "1-2 Years",
    "2-5 Years",
    "5-10 Years",
    "10+ Years",
]

TENURE_ORDER = [
    "0-6 Months",
    "6-12 Months",
    "1-2 Years",
    "2-5 Years",
    "5-10 Years",
    "10+ Years",
]

BALANCE_ORDER = [
    "Negative",
    "$0",
    "$1-$499",
    "$500-$999",
    "$1K-$2.5K",
    "$2.5K-$5K",
    "$5K-$10K",
    "$10K+",
]


# ---------------------------------------------------------------------------
# Categorization functions
# ---------------------------------------------------------------------------


def categorize_duration(days: float) -> str | None:
    """Bucket account lifespan (days open -> close) into duration categories."""
    if pd.isna(days) or days < 0:
        return None
    months = days / 30.44
    if months <= 1:
        return "0-1 Month"
    if months <= 3:
        return "1-3 Months"
    if months <= 6:
        return "3-6 Months"
    if months <= 12:
        return "6-12 Months"
    years = days / 365.25
    if years <= 2:
        return "1-2 Years"
    if years <= 5:
        return "2-5 Years"
    if years <= 10:
        return "5-10 Years"
    return "10+ Years"


def categorize_tenure(days: float) -> str | None:
    """Bucket account tenure (days since opened) into categories."""
    if pd.isna(days) or days < 0:
        return None
    months = days / 30.44
    if months <= 6:
        return "0-6 Months"
    if months <= 12:
        return "6-12 Months"
    years = days / 365.25
    if years <= 2:
        return "1-2 Years"
    if years <= 5:
        return "2-5 Years"
    if years <= 10:
        return "5-10 Years"
    return "10+ Years"


def categorize_balance(bal: float) -> str | None:
    """Bucket average balance into tiers."""
    if pd.isna(bal):
        return None
    if bal < 0:
        return "Negative"
    if bal == 0:
        return "$0"
    if bal < 500:
        return "$1-$499"
    if bal < 1000:
        return "$500-$999"
    if bal < 2500:
        return "$1K-$2.5K"
    if bal < 5000:
        return "$2.5K-$5K"
    if bal < 10000:
        return "$5K-$10K"
    return "$10K+"


# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------


def product_col(df: pd.DataFrame) -> str | None:
    """Detect product code column ('Product Code' or legacy 'Prod Code')."""
    if "Product Code" in df.columns:
        return "Product Code"
    if "Prod Code" in df.columns:
        return "Prod Code"
    return None


# ---------------------------------------------------------------------------
# Standardized L12M attrition window (owner review cycle, 2026-06-11)
#
# Before this existed, A9.0 / A9.1 / A9.4 each used a different denominator
# for "L12M attrition rate" (open-at-window-start vs open-at-start+window-opens
# +partial-month-opens vs currently-open+window-closes) and printed three
# different numbers for the same metric in one deck. ONE definition now:
#
#   base      = every account exposed during the window
#             = opened on/before end_date AND (still open OR closed on/after
#               start_date)
#   closures  = base rows with Date Closed inside [start_date, end_date]
#   rate      = closures / base
# ---------------------------------------------------------------------------


def l12m_exposure_base(
    all_data: pd.DataFrame,
    start_date,
    end_date,
) -> pd.DataFrame:
    """The standardized L12M attrition denominator (see module comment)."""
    if all_data is None or all_data.empty:
        return pd.DataFrame()
    sd, ed = pd.Timestamp(start_date), pd.Timestamp(end_date)
    do = all_data["Date Opened"]
    dc = all_data["Date Closed"]
    mask = (do.isna() | (do <= ed)) & (dc.isna() | (dc >= sd))
    return all_data[mask]


def l12m_attrition(
    all_data: pd.DataFrame,
    start_date,
    end_date,
) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """Return (base, closures, rate) on the standardized L12M window.

    closures is a subset of base, so the rate can never exceed 100%.
    """
    base = l12m_exposure_base(all_data, start_date, end_date)
    if base.empty:
        return base, base, 0.0
    sd, ed = pd.Timestamp(start_date), pd.Timestamp(end_date)
    dc = base["Date Closed"]
    closures = base[(dc >= sd) & (dc <= ed)]
    return base, closures, len(closures) / len(base)


# Audit-framework label for the standardized base. Attrition rates cannot
# anchor to "Eligible" (an open-accounts-only subset that excludes every
# closure by construction); they anchor here instead.
L12M_EXPOSURE_LABEL = "L12M Exposure"


# ---------------------------------------------------------------------------
# Data preparation (cached)
# ---------------------------------------------------------------------------


def _norm_codes(s: pd.Series) -> pd.Series:
    """subsets.py-style normalization: str, strip, drop trailing .0, upper."""
    return s.astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.upper()


def attrition_universe(ctx: PipelineContext) -> pd.DataFrame:
    """The population attrition metrics are computed on (owner decision
    2026-06-11: 'ensure the proper open vs eligible subsets').

    ctx.subsets.eligible_data is OPEN accounts with eligible stat + product
    codes -- it cannot contain a closure, so attrition can't anchor to it
    directly. The comparable population is:

      open rows   -> exactly ctx.subsets.eligible_data (same stat + product
                     filters the rest of the deck uses)
      closed rows -> eligible PRODUCT code only. Closure rewrites the stat
                     code, so applying the stat test to closed rows would
                     exclude every closure by construction (the A9.13
                     circularity bug).

    Falls back to the full dataset (with a warning) when eligibility config
    or columns are missing, preserving behavior for unconfigured clients.
    """
    data = ctx.data
    if data is None or data.empty:
        return pd.DataFrame()

    subsets = getattr(ctx, "subsets", None)
    elig = getattr(subsets, "eligible_data", None) if subsets is not None else None
    epc = getattr(ctx.client, "eligible_prod_codes", None) or []
    pcol = product_col(data)

    if elig is None or len(elig) == 0 or not epc or pcol is None:
        logger.warning(
            "Attrition universe: eligibility config/subsets unavailable -- "
            "falling back to ALL accounts (rates will include non-eligible products)"
        )
        return data

    epc_norm = {str(c).strip().upper().removesuffix(".0") for c in epc}
    is_closed = data["Date Closed"].notna()
    closed_eligible = is_closed & _norm_codes(data[pcol]).isin(epc_norm)
    open_eligible = (~is_closed) & data.index.isin(elig.index)
    return data[closed_eligible | open_eligible]


def prepare_attrition_data(
    ctx: PipelineContext,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (universe, open_accts, closed_accts), cached in ctx.results.

    `universe` is the attrition population from attrition_universe() --
    the eligible-comparable book, NOT the raw ODD. A9.13 (eligible vs
    other products) intentionally reads ctx.data directly instead.
    """
    cached = ctx.results.get("_attrition_data")
    if cached is not None:
        return cached

    if ctx.data is None:
        empty = pd.DataFrame()
        return empty, empty, empty

    # Full book by default. The eligible-products scoping (attrition_universe)
    # collapsed closure counts to implausible levels on real data (owner
    # report: ~100 L12M closures) -- the configured eligible products cover
    # only part of the closing book. Opt in explicitly when wanted:
    #   ARS_ATTRITION_ELIGIBLE_ONLY=1
    import os as _os
    if _os.environ.get("ARS_ATTRITION_ELIGIBLE_ONLY") == "1":
        data = attrition_universe(ctx)
    else:
        data = ctx.data

    open_accts = data[data["Date Closed"].isna()].copy()
    closed_accts = data[data["Date Closed"].notna()].copy()

    # Closed-detection sanity check. Attrition defines closed purely as
    # "Date Closed parsed", so an account with an open-looking Stat Code but
    # a Date Closed is CLOSED here while ctx.subsets.open_accounts may call
    # it open. Surface the disagreement instead of hiding it. (The reverse --
    # non-"O" stat codes without a date -- is normal for institutions with
    # numeric stat codes, so it can't be warned on reliably.)
    if "Stat Code" in data.columns:
        stat_open = data["Stat Code"].astype(str).str.strip().str.upper().str.startswith("O")
        conflicting = int((stat_open & data["Date Closed"].notna()).sum())
        if conflicting > 0:
            logger.warning(
                "Attrition: {n} account(s) have an open Stat Code AND a Date Closed -- "
                "attrition treats them as CLOSED (by date)",
                n=conflicting,
            )

    if not closed_accts.empty:
        closed_accts["_duration_days"] = (
            closed_accts["Date Closed"] - closed_accts["Date Opened"]
        ).dt.days
        closed_accts["_duration_cat"] = closed_accts["_duration_days"].apply(categorize_duration)

    result = (data, open_accts, closed_accts)
    ctx.results["_attrition_data"] = result
    return result


# ---------------------------------------------------------------------------
# Safe wrapper
# ---------------------------------------------------------------------------


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
