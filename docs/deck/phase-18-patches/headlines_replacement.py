"""Dynamic headline generation from analysis results.

Phase 18.4: All _noop generators replaced with real implementations.

Each generator receives an insights dict (from ctx.results) and returns
a conclusion-based headline sentence. Falls back to the original title
if the generator is unavailable or the data is insufficient.

Headline rules (SLIDE_DESIGN.md §1.2):
1. Lead with the finding, not the metric name
2. Include the key metric number
3. Add comparative context where available
4. Imply the "so what"
5. Keep under 120 characters
6. Fall back gracefully on NaN/zero/missing denominator

File: 01_Analysis/00-Scripts/output/headlines.py
Action: REPLACE entire file contents with this version.
"""

from __future__ import annotations

import math
from typing import Any

from loguru import logger


# =============================================================================
# UTILITY HELPERS
# =============================================================================


def _is_valid(value: Any) -> bool:
    """Return True if value is a usable number (not None, NaN, or inf)."""
    if value is None:
        return False
    try:
        return not (math.isnan(value) or math.isinf(value))
    except (TypeError, ValueError):
        return False


def _fmt_pct(value: float) -> str:
    """Format a rate as a percentage string (e.g., 0.342 -> '34.2%')."""
    return f"{value:.1%}"


def _fmt_int(value: int | float) -> str:
    """Format a number with commas (e.g., 12400 -> '12,400')."""
    return f"{int(value):,}"


def _fmt_currency(value: float) -> str:
    """Format dollar amount (e.g., 142000 -> '$142K')."""
    abs_val = abs(value)
    if abs_val >= 1_000_000:
        return f"${value / 1_000_000:,.1f}M"
    if abs_val >= 1_000:
        return f"${value / 1_000:,.0f}K"
    return f"${value:,.0f}"


def _trend_word(current: float, baseline: float) -> str:
    """Return a trend descriptor comparing current to baseline."""
    if not _is_valid(current) or not _is_valid(baseline):
        return ""
    if current > baseline * 1.02:
        return "trending up"
    if current < baseline * 0.98:
        return "softening"
    return "holding steady"


def _try_adaptive(insights: dict[str, Any], metric_label: str = "") -> str:
    """Adaptive headline builder for modules with unknown data shapes.

    Scans the insights dict for common key patterns (rate, count, delta,
    trend, total, pct) and builds a headline from whatever is available.
    Returns empty string if nothing usable is found.
    """
    if not insights or not isinstance(insights, dict):
        return ""

    # Look for the most impactful number
    rate = None
    count = None
    delta = None

    for k, v in insights.items():
        if not _is_valid(v):
            continue
        kl = k.lower()
        if any(x in kl for x in ("rate", "pct", "percent", "share")):
            rate = (k, v)
        elif any(x in kl for x in ("delta", "diff", "change", "gap", "lift")):
            delta = (k, v)
        elif any(x in kl for x in ("total", "count", "n_", "num")):
            count = (k, v)

    parts = []
    if rate:
        label = rate[0].replace("_", " ").title()
        parts.append(f"{label} at {_fmt_pct(rate[1])}")
    if delta:
        label = delta[0].replace("_", " ").title()
        val = delta[1]
        if abs(val) < 1:
            parts.append(f"{label}: {_fmt_pct(val)}")
        else:
            parts.append(f"{label}: {_fmt_currency(val)}")
    if count and not parts:
        label = count[0].replace("_", " ").title()
        parts.append(f"{label}: {_fmt_int(count[1])}")

    if not parts:
        return ""

    headline = " — ".join(parts[:2])
    if metric_label:
        headline = f"{metric_label}: {headline}"
    return headline[:120]


# =============================================================================
# DCTR GENERATORS (DCTR-1 through DCTR-16, A7.x)
# =============================================================================


def _dctr_1(insights: dict[str, Any]) -> str:
    """DCTR-1: Historical Debit Card Take Rate."""
    rate = insights.get("overall_dctr")
    total = insights.get("total_accounts")
    recent = insights.get("recent_dctr")
    if not _is_valid(rate) or not _is_valid(total) or total == 0:
        return ""
    trend = _trend_word(recent, rate) if _is_valid(recent) else ""
    suffix = f", {trend} in recent cohorts" if trend else ""
    return f"Debit adoption at {_fmt_pct(rate)} across {_fmt_int(total)} accounts{suffix}"


def _dctr_2(insights: dict[str, Any]) -> str:
    """DCTR-2: Open vs Eligible comparison."""
    open_dctr = insights.get("open_dctr")
    elig_dctr = insights.get("eligible_dctr")
    diff = insights.get("difference")
    if not _is_valid(open_dctr) or not _is_valid(elig_dctr):
        return ""
    if _is_valid(diff) and abs(diff) > 0.01:
        pp = abs(diff) * 100
        return (
            f"Eligibility filters lift DCTR from {_fmt_pct(open_dctr)} to "
            f"{_fmt_pct(elig_dctr)} — {pp:.0f}pp gap from ineligible accounts"
        )
    return f"Open DCTR at {_fmt_pct(open_dctr)}, eligible at {_fmt_pct(elig_dctr)}"


def _dctr_3(insights: dict[str, Any]) -> str:
    """DCTR-3: L12M DCTR Snapshot."""
    dctr = insights.get("dctr")
    comparison = insights.get("comparison_to_overall")
    if not _is_valid(dctr):
        return ""
    if _is_valid(comparison) and abs(comparison) > 0.01:
        pp = comparison * 100
        direction = "+" if pp > 0 else ""
        return f"Recent adoption at {_fmt_pct(dctr)}, {direction}{pp:.0f}pp vs historical baseline"
    return f"TTM debit take rate at {_fmt_pct(dctr)}"


def _dctr_4(insights: dict[str, Any]) -> str:
    """DCTR-4: Personal DCTR."""
    rate = insights.get("overall_dctr")
    total = insights.get("total_accounts")
    recent = insights.get("recent_dctr")
    if not _is_valid(rate) or not _is_valid(total) or total == 0:
        return ""
    trend = _trend_word(recent, rate) if _is_valid(recent) else ""
    suffix = f", {trend} recently" if trend else ""
    return f"Personal debit adoption at {_fmt_pct(rate)} ({_fmt_int(total)} accounts){suffix}"


def _dctr_5(insights: dict[str, Any]) -> str:
    """DCTR-5: Business DCTR."""
    rate = insights.get("overall_dctr")
    total = insights.get("total_accounts")
    if not _is_valid(rate) or not _is_valid(total) or total == 0:
        return ""
    recent = insights.get("recent_dctr")
    trend = _trend_word(recent, rate) if _is_valid(recent) else ""
    suffix = f", {trend} recently" if trend else ""
    return f"Business debit adoption at {_fmt_pct(rate)} ({_fmt_int(total)} accounts){suffix}"


def _dctr_6(insights: dict[str, Any]) -> str:
    """DCTR-6: Personal L12M DCTR."""
    dctr = insights.get("dctr")
    total = insights.get("total_accounts")
    if not _is_valid(dctr):
        return ""
    accts = f" across {_fmt_int(total)} accounts" if _is_valid(total) and total > 0 else ""
    return f"Personal TTM take rate at {_fmt_pct(dctr)}{accts}"


def _dctr_7(insights: dict[str, Any]) -> str:
    """DCTR-7: Business L12M DCTR."""
    dctr = insights.get("dctr")
    total = insights.get("total_accounts")
    if not _is_valid(dctr):
        return ""
    accts = f" across {_fmt_int(total)} accounts" if _is_valid(total) and total > 0 else ""
    return f"Business TTM take rate at {_fmt_pct(dctr)}{accts}"


def _dctr_8(insights: dict[str, Any]) -> str:
    """DCTR-8: Comprehensive DCTR Summary."""
    return _try_adaptive(insights, "DCTR Summary")


def _dctr_9(insights: dict[str, Any]) -> str:
    """DCTR-9: Branch DCTR Overview."""
    best = insights.get("best_branch", "")
    best_dctr = insights.get("best_dctr")
    worst = insights.get("worst_branch", "")
    worst_dctr = insights.get("worst_dctr")
    total = insights.get("total_branches")
    if _is_valid(best_dctr) and _is_valid(worst_dctr) and best and worst:
        spread = abs(best_dctr - worst_dctr) * 100
        return f"{spread:.0f}pp DCTR spread across branches — {best} leads at {_fmt_pct(best_dctr)}, {worst} trails at {_fmt_pct(worst_dctr)}"
    if _is_valid(total) and total > 0:
        return f"DCTR performance varies across {_fmt_int(total)} branches"
    return _try_adaptive(insights, "Branch DCTR")


def _dctr_10(insights: dict[str, Any]) -> str:
    """DCTR-10: DCTR by Account Age."""
    return _try_adaptive(insights, "DCTR by account age")


def _dctr_11(insights: dict[str, Any]) -> str:
    """DCTR-11: DCTR by Balance Tier."""
    return _try_adaptive(insights, "DCTR by balance tier")


def _dctr_12(insights: dict[str, Any]) -> str:
    """DCTR-12: DCTR by Product Code."""
    return _try_adaptive(insights, "DCTR by product code")


def _dctr_13(insights: dict[str, Any]) -> str:
    """DCTR-13: Debit Card Activation Timeline."""
    return _try_adaptive(insights, "Activation timeline")


def _dctr_14(insights: dict[str, Any]) -> str:
    """DCTR-14: New Account DCTR."""
    return _try_adaptive(insights, "New account DCTR")


def _dctr_15(insights: dict[str, Any]) -> str:
    """DCTR-15: DCTR Opportunity Sizing."""
    return _try_adaptive(insights, "DCTR opportunity")


def _dctr_16(insights: dict[str, Any]) -> str:
    """DCTR-16: Extended DCTR View."""
    return _try_adaptive(insights, "DCTR detail")


def _a7_4(insights: dict[str, Any]) -> str:
    """A7.4: Segment DCTR Trends."""
    p = insights.get("personal_trend")
    b = insights.get("business_trend")
    has_biz = insights.get("has_business", False)
    if not _is_valid(p):
        return ""
    if has_biz and _is_valid(b):
        return f"Personal DCTR trend at {_fmt_pct(p)}, business at {_fmt_pct(b)}"
    return f"Personal DCTR trending at {_fmt_pct(p)}"


def _a7_5(insights: dict[str, Any]) -> str:
    """A7.5: DCTR by Open Month Cohort."""
    return _try_adaptive(insights, "DCTR by open month")


def _a7_6a(insights: dict[str, Any]) -> str:
    """A7.6a: Historical DCTR Trend Line."""
    rate = insights.get("latest_rate") or insights.get("rate") or insights.get("dctr")
    trend = insights.get("direction") or insights.get("trend", "")
    if _is_valid(rate):
        suffix = f", {trend}" if trend else ""
        return f"Historical DCTR at {_fmt_pct(rate)}{suffix}"
    return _try_adaptive(insights, "Historical DCTR trend")


def _a7_6b(insights: dict[str, Any]) -> str:
    """A7.6b: DCTR Trend Comparison (paired with A7.6a)."""
    return _try_adaptive(insights, "DCTR trend comparison")


def _a7_7(insights: dict[str, Any]) -> str:
    """A7.7: Historical Account & Debit Card Funnel."""
    through = insights.get("through_rate")
    dctr_e = insights.get("dctr_eligible")
    if not _is_valid(through):
        return ""
    suffix = f", eligible DCTR at {_fmt_pct(dctr_e)}" if _is_valid(dctr_e) else ""
    return f"Funnel through-rate at {_fmt_pct(through)}{suffix}"


def _a7_8(insights: dict[str, Any]) -> str:
    """A7.8: TTM Account & Debit Card Funnel."""
    through = insights.get("through")
    dctr = insights.get("dctr")
    if not _is_valid(through):
        return ""
    suffix = f", DCTR at {_fmt_pct(dctr)}" if _is_valid(dctr) else ""
    return f"TTM funnel through-rate at {_fmt_pct(through)}{suffix}"


def _a7_9(insights: dict[str, Any]) -> str:
    """A7.9: Eligible vs Non-Eligible DCTR."""
    elig = insights.get("eligible_dctr")
    non = insights.get("non_eligible_dctr")
    gap = insights.get("gap")
    if not _is_valid(elig):
        return ""
    if _is_valid(gap) and abs(gap) > 0.01:
        return f"Eligible DCTR at {_fmt_pct(elig)}, {abs(gap) * 100:.0f}pp above non-eligible"
    return f"Eligible DCTR at {_fmt_pct(elig)}"


def _a7_10a(insights: dict[str, Any]) -> str:
    """A7.10a: Branch DCTR Historical vs TTM."""
    improving = insights.get("improving")
    total = insights.get("total")
    if not _is_valid(improving) or not _is_valid(total) or total == 0:
        return ""
    return f"{_fmt_int(improving)} of {_fmt_int(total)} branches improving DCTR year-over-year"


def _a7_10b(insights: dict[str, Any]) -> str:
    """A7.10b: Branch DCTR detail (paired with A7.10a)."""
    return _try_adaptive(insights, "Branch DCTR detail")


def _a7_13(insights: dict[str, Any]) -> str:
    """A7.13: DCTR by Debit Card Type."""
    return _try_adaptive(insights, "DCTR by card type")


def _a7_14(insights: dict[str, Any]) -> str:
    """A7.14: DCTR by Account Type."""
    return _try_adaptive(insights, "DCTR by account type")


def _a7_15(insights: dict[str, Any]) -> str:
    """A7.15: Extended DCTR Analysis."""
    return _try_adaptive(insights, "Extended DCTR analysis")


# =============================================================================
# REG E GENERATORS (A8.x)
# =============================================================================


def _rege_1(insights: dict[str, Any]) -> str:
    """A8.1: Overall Reg E Status."""
    rate = insights.get("opt_in_rate")
    total = insights.get("total_base")
    if not _is_valid(rate):
        return ""
    accts = f" — {_fmt_int(total)} eligible accounts" if _is_valid(total) and total > 0 else ""
    return f"Reg E opt-in at {_fmt_pct(rate)}{accts}"


def _rege_2(insights: dict[str, Any]) -> str:
    """A8.2: Historical Reg E Opt-In Rate."""
    rate = insights.get("opt_in_rate") or insights.get("historical_rate") or insights.get("rate")
    l12m = insights.get("l12m_rate") or insights.get("recent_rate")
    if not _is_valid(rate):
        return _try_adaptive(insights, "Historical Reg E")
    if _is_valid(l12m):
        delta = (l12m - rate) * 100
        direction = "up" if delta > 0 else "down"
        return f"Historical Reg E opt-in at {_fmt_pct(rate)}, L12M {direction} {abs(delta):.0f}pp to {_fmt_pct(l12m)}"
    return f"Historical Reg E opt-in at {_fmt_pct(rate)}"


def _rege_3(insights: dict[str, Any]) -> str:
    """A8.3: L12M Monthly Reg E Trend."""
    rate = insights.get("latest_rate") or insights.get("l12m_rate") or insights.get("rate")
    trend = insights.get("direction") or insights.get("trend", "")
    if _is_valid(rate):
        suffix = f", {trend}" if trend else ""
        return f"L12M Reg E opt-in at {_fmt_pct(rate)}{suffix}"
    return _try_adaptive(insights, "L12M Reg E trend")


def _rege_4(insights: dict[str, Any]) -> str:
    """A8.4a: Reg E by Branch (Historical vs L12M)."""
    n = insights.get("n_branches") or insights.get("total_branches")
    best = insights.get("best_branch", "")
    best_rate = insights.get("best_rate")
    worst = insights.get("worst_branch", "")
    worst_rate = insights.get("worst_rate")
    if _is_valid(best_rate) and _is_valid(worst_rate) and best and worst:
        spread = abs(best_rate - worst_rate) * 100
        return f"{spread:.0f}pp Reg E spread — {best} leads at {_fmt_pct(best_rate)}, {worst} trails at {_fmt_pct(worst_rate)}"
    return _try_adaptive(insights, "Reg E by branch")


def _rege_4b(insights: dict[str, Any]) -> str:
    """A8.4b: Reg E Branch Detail (companion)."""
    return _try_adaptive(insights, "Reg E branch detail")


def _rege_4c(insights: dict[str, Any]) -> str:
    """A8.4c: Reg E Branch Comparison."""
    return _try_adaptive(insights, "Reg E branch comparison")


def _rege_5(insights: dict[str, Any]) -> str:
    """A8.5: Reg E by Account Age."""
    newest = insights.get("newest_rate") or insights.get("new_acct_rate")
    oldest = insights.get("oldest_rate") or insights.get("mature_rate")
    if _is_valid(newest) and _is_valid(oldest):
        if newest > oldest:
            return f"Newer accounts opt in at {_fmt_pct(newest)} vs {_fmt_pct(oldest)} for mature — onboarding is working"
        else:
            return f"Mature accounts opt in at {_fmt_pct(oldest)} vs {_fmt_pct(newest)} for new — onboarding gap"
    return _try_adaptive(insights, "Reg E by account age")


def _rege_6(insights: dict[str, Any]) -> str:
    """A8.6: Reg E by Balance Tier."""
    return _try_adaptive(insights, "Reg E by balance tier")


def _rege_7(insights: dict[str, Any]) -> str:
    """A8.7: Reg E by Product Code."""
    return _try_adaptive(insights, "Reg E by product")


def _rege_10(insights: dict[str, Any]) -> str:
    """A8.10: Reg E Dimensions — Personal vs Business."""
    personal = insights.get("personal_rate") or insights.get("personal")
    business = insights.get("business_rate") or insights.get("business")
    if _is_valid(personal) and _is_valid(business):
        return f"Personal Reg E at {_fmt_pct(personal)}, business at {_fmt_pct(business)}"
    if _is_valid(personal):
        return f"Personal Reg E opt-in at {_fmt_pct(personal)}"
    return _try_adaptive(insights, "Reg E by segment")


def _rege_11(insights: dict[str, Any]) -> str:
    """A8.11: Reg E Dimensions — Debit vs Non-Debit."""
    with_dc = insights.get("debit_rate") or insights.get("with_debit")
    without = insights.get("non_debit_rate") or insights.get("without_debit")
    if _is_valid(with_dc) and _is_valid(without):
        gap = abs(with_dc - without) * 100
        return f"Debit cardholders opt in {gap:.0f}pp higher ({_fmt_pct(with_dc)} vs {_fmt_pct(without)})"
    return _try_adaptive(insights, "Reg E debit vs non-debit")


def _rege_12(insights: dict[str, Any]) -> str:
    """A8.12: Reg E 24-Month Trend."""
    latest = insights.get("latest_rate") or insights.get("rate")
    trend = insights.get("direction") or insights.get("trend", "")
    if _is_valid(latest):
        suffix = f", {trend} over 24 months" if trend else ""
        return f"Reg E opt-in at {_fmt_pct(latest)}{suffix}"
    return _try_adaptive(insights, "Reg E 24-month trend")


def _rege_13(insights: dict[str, Any]) -> str:
    """A8.13: Reg E Revenue Impact."""
    revenue = insights.get("total_revenue") or insights.get("revenue")
    per_acct = insights.get("per_account") or insights.get("avg_revenue")
    if _is_valid(revenue):
        suffix = f" ({_fmt_currency(per_acct)}/account)" if _is_valid(per_acct) else ""
        return f"Reg E generating {_fmt_currency(revenue)} in overdraft revenue{suffix}"
    return _try_adaptive(insights, "Reg E revenue impact")


# =============================================================================
# ATTRITION GENERATORS (A9.x)
# =============================================================================


def _attrition_1(insights: dict[str, Any]) -> str:
    """A9.1: Overall Attrition Rate."""
    rate = insights.get("overall_rate")
    closed = insights.get("closed")
    if not _is_valid(rate):
        return ""
    severity = "elevated" if rate > 0.10 else "moderate" if rate > 0.05 else "healthy"
    closed_str = f" ({_fmt_int(closed)} accounts closed)" if _is_valid(closed) and closed > 0 else ""
    return f"Attrition at {severity} {_fmt_pct(rate)}{closed_str}"


def _attrition_2(insights: dict[str, Any]) -> str:
    """A9.2: Closure Duration Analysis."""
    first_year = insights.get("first_year_pct")
    if not _is_valid(first_year):
        return ""
    return f"{_fmt_pct(first_year)} of closures occur within the first year"


def _attrition_3(insights: dict[str, Any]) -> str:
    """A9.3: Open vs Closed Comparison."""
    return _try_adaptive(insights, "Open vs closed accounts")


def _attrition_4(insights: dict[str, Any]) -> str:
    """A9.4: Attrition by Branch."""
    n = insights.get("n_branches")
    if not _is_valid(n) or n == 0:
        return _try_adaptive(insights, "Attrition by branch")
    return f"Attrition varies across {_fmt_int(n)} branches"


def _attrition_5(insights: dict[str, Any]) -> str:
    """A9.5: Attrition by Product Code."""
    return _try_adaptive(insights, "Attrition by product")


def _attrition_6(insights: dict[str, Any]) -> str:
    """A9.6: Personal vs Business Attrition."""
    return _try_adaptive(insights, "Attrition by segment")


def _attrition_7(insights: dict[str, Any]) -> str:
    """A9.7: Attrition by Account Tenure."""
    return _try_adaptive(insights, "Attrition by tenure")


def _attrition_8(insights: dict[str, Any]) -> str:
    """A9.8: Attrition by Balance Tier."""
    return _try_adaptive(insights, "Attrition by balance")


def _attrition_9(insights: dict[str, Any]) -> str:
    """A9.9: Debit Card Retention Effect."""
    lift = insights.get("retention_lift")
    if not _is_valid(lift):
        return ""
    return f"Debit cardholders close {_fmt_pct(abs(lift))} less often — cards drive retention"


def _attrition_10(insights: dict[str, Any]) -> str:
    """A9.10: Mailer Program Retention."""
    lift = insights.get("lift")
    if not _is_valid(lift):
        return ""
    return f"Mailed accounts close {_fmt_pct(abs(lift))} less often"


def _attrition_11(insights: dict[str, Any]) -> str:
    """A9.11: Revenue Impact of Attrition."""
    total_lost = insights.get("total_lost")
    if not _is_valid(total_lost):
        return ""
    return f"{_fmt_currency(total_lost)} in annual debit revenue at risk from attrition"


def _attrition_12(insights: dict[str, Any]) -> str:
    """A9.12: Attrition Velocity."""
    total = insights.get("total_l12m")
    trend = insights.get("trend", "")
    if not _is_valid(total):
        return ""
    trend_str = f", {trend}" if trend else ""
    return f"{_fmt_int(total)} accounts closed in last 12 months{trend_str}"


def _attrition_13(insights: dict[str, Any]) -> str:
    """A9.13: ARS vs Non-ARS Comparison."""
    diff = insights.get("diff")
    if not _is_valid(diff):
        return ""
    pp = abs(diff) * 100
    direction = "lower" if diff < 0 else "higher"
    return f"ARS accounts attrit {pp:.1f}pp {direction} than non-ARS accounts"


# =============================================================================
# VALUE GENERATORS (A11.x)
# =============================================================================


def _value_1(insights: dict[str, Any]) -> str:
    """A11.1: Value of a Debit Card."""
    delta = insights.get("delta")
    rev_with = insights.get("rev_per_with")
    rev_without = insights.get("rev_per_without")
    if not _is_valid(delta) or not _is_valid(rev_with):
        return ""
    return (
        f"Debit cardholders generate {_fmt_currency(delta)} more revenue per account "
        f"({_fmt_currency(rev_with)} vs {_fmt_currency(rev_without)})"
    )


def _value_2(insights: dict[str, Any]) -> str:
    """A11.2: Value of Reg E Opt-In."""
    delta = insights.get("delta")
    rev_with = insights.get("rev_per_with")
    if not _is_valid(delta) or not _is_valid(rev_with):
        return ""
    return f"Reg E opt-in accounts generate {_fmt_currency(delta)} more revenue per account"


# =============================================================================
# OVERVIEW GENERATORS (A1, A1b, A3)
# =============================================================================


def _overview_a1(insights: dict[str, Any]) -> str:
    """A1: Account Composition."""
    insight_text = insights.get("insight", "")
    if insight_text:
        return insight_text[:120]
    return ""


def _overview_a1b(insights: dict[str, Any]) -> str:
    """A1b: Account Composition Detail."""
    personal = insights.get("personal_pct") or insights.get("personal_count")
    business = insights.get("business_pct") or insights.get("business_count")
    if _is_valid(personal) and _is_valid(business):
        if personal > 1:
            # Counts, not rates
            return f"{_fmt_int(personal)} personal vs {_fmt_int(business)} business accounts"
        else:
            return f"Portfolio split: {_fmt_pct(personal)} personal, {_fmt_pct(business)} business"
    return _try_adaptive(insights, "Account composition")


def _overview_a3(insights: dict[str, Any]) -> str:
    """A3: Eligibility Funnel."""
    inner = insights.get("insights", insights)
    elig = inner.get("eligible_accounts")
    rate = inner.get("eligibility_rate")
    if not _is_valid(elig) or not _is_valid(rate):
        return ""
    return f"{_fmt_int(elig)} accounts eligible ({_fmt_pct(rate / 100 if rate > 1 else rate)} eligibility rate)"


# =============================================================================
# INSIGHTS GENERATORS (S1-S8)
# =============================================================================


def _insight_s1(insights: dict[str, Any]) -> str:
    """S1: The Revenue Gap."""
    total_gap = insights.get("total_gap")
    realistic = insights.get("realistic_capture")
    if not _is_valid(total_gap):
        return ""
    suffix = f", {_fmt_currency(realistic)} realistically capturable" if _is_valid(realistic) else ""
    return f"{_fmt_currency(total_gap)} total revenue gap identified{suffix}"


def _insight_s2(insights: dict[str, Any]) -> str:
    """S2: The Cost of Walking Away."""
    destroyed = insights.get("revenue_destroyed")
    preventable = insights.get("preventable_revenue")
    if not _is_valid(destroyed):
        return ""
    suffix = f", {_fmt_currency(preventable)} preventable" if _is_valid(preventable) else ""
    return f"{_fmt_currency(destroyed)} in revenue destroyed by attrition{suffix}"


def _insight_s3(insights: dict[str, Any]) -> str:
    """S3: Program ROI."""
    roi = insights.get("total_program_roi")
    annual = insights.get("annual_program_value")
    if not _is_valid(annual):
        return ""
    suffix = f" ({roi:.1f}x ROI)" if _is_valid(roi) else ""
    return f"ARS program delivering {_fmt_currency(annual)} in annual value{suffix}"


def _insight_s4(insights: dict[str, Any]) -> str:
    """S4: Branch Performance Gap."""
    gap_rev = insights.get("branch_gap_revenue")
    spread = insights.get("spread")
    if not _is_valid(gap_rev):
        return ""
    suffix = f" ({_fmt_pct(spread)} spread)" if _is_valid(spread) else ""
    return f"{_fmt_currency(gap_rev)} in revenue at stake from branch performance gap{suffix}"


def _insight_s5(insights: dict[str, Any]) -> str:
    """S5: Revenue Cascade."""
    total = insights.get("total_cascade")
    if not _is_valid(total):
        return ""
    return f"{_fmt_currency(total)} total revenue opportunity across all streams"


def _insight_s6(insights: dict[str, Any]) -> str:
    """S6: Combined Opportunity Map."""
    addressable = insights.get("total_addressable")
    realistic = insights.get("total_realistic")
    if not _is_valid(addressable):
        return ""
    suffix = f", {_fmt_currency(realistic)} realistically achievable" if _is_valid(realistic) else ""
    return f"{_fmt_currency(addressable)} total addressable opportunity{suffix}"


def _insight_s7(insights: dict[str, Any]) -> str:
    """S7: What If +5 Points of DCTR."""
    new_accounts = insights.get("new_debit_accounts")
    total_gain = insights.get("total_annual_gain")
    if not _is_valid(total_gain):
        return ""
    accts = f"{_fmt_int(new_accounts)} new debit accounts, " if _is_valid(new_accounts) else ""
    return f"+5pp DCTR would yield {accts}{_fmt_currency(total_gain)} annually"


def _insight_s8(insights: dict[str, Any]) -> str:
    """S8: Action Plan."""
    combined = insights.get("combined")
    if not _is_valid(combined):
        return ""
    return f"Three-action plan targeting {_fmt_currency(combined)} in combined value"


# =============================================================================
# INSIGHTS EXTRAS GENERATORS (A18, A19, A20)
# =============================================================================


def _insight_a18(insights: dict[str, Any]) -> str:
    """A18: Branch Scorecard Overview."""
    n = insights.get("n_branches") or insights.get("total_branches")
    top = insights.get("top_branch", "")
    if _is_valid(n) and top:
        return f"Branch scorecard across {_fmt_int(n)} branches — {top} leads overall"
    if _is_valid(n):
        return f"Performance scorecard across {_fmt_int(n)} branches"
    return _try_adaptive(insights, "Branch scorecard")


def _insight_a18_1(insights: dict[str, Any]) -> str:
    """A18.1: Branch Scorecard — DCTR Dimension."""
    return _try_adaptive(insights, "Branch DCTR scorecard")


def _insight_a18_2(insights: dict[str, Any]) -> str:
    """A18.2: Branch Scorecard — Reg E Dimension."""
    return _try_adaptive(insights, "Branch Reg E scorecard")


def _insight_a18_3(insights: dict[str, Any]) -> str:
    """A18.3: Branch Scorecard — Attrition Dimension."""
    return _try_adaptive(insights, "Branch attrition scorecard")


def _insight_a19(insights: dict[str, Any]) -> str:
    """A19: Dormant Account Opportunity."""
    n = insights.get("n_dormant") or insights.get("total_dormant")
    revenue = insights.get("revenue_opportunity") or insights.get("total_revenue")
    if _is_valid(n) and _is_valid(revenue):
        return f"{_fmt_int(n)} dormant accounts represent {_fmt_currency(revenue)} in activation opportunity"
    if _is_valid(n):
        return f"{_fmt_int(n)} dormant accounts identified for activation outreach"
    return _try_adaptive(insights, "Dormant accounts")


def _insight_a19_1(insights: dict[str, Any]) -> str:
    """A19.1: Dormant Account Detail."""
    return _try_adaptive(insights, "Dormant account detail")


def _insight_a19_2(insights: dict[str, Any]) -> str:
    """A19.2: Dormant Account Segments."""
    return _try_adaptive(insights, "Dormant segments")


def _insight_a20(insights: dict[str, Any]) -> str:
    """A20: High-Balance Dormant Opportunity."""
    n = insights.get("n_high_balance") or insights.get("count")
    avg_bal = insights.get("avg_balance")
    if _is_valid(n) and _is_valid(avg_bal):
        return f"{_fmt_int(n)} high-balance dormant accounts averaging {_fmt_currency(avg_bal)} — prime activation targets"
    return _try_adaptive(insights, "High-balance dormant")


def _insight_a20_1(insights: dict[str, Any]) -> str:
    """A20.1: High-Balance Dormant Detail."""
    return _try_adaptive(insights, "High-balance dormant detail")


def _insight_a20_2(insights: dict[str, Any]) -> str:
    """A20.2: High-Balance Dormant by Branch."""
    return _try_adaptive(insights, "High-balance dormant by branch")


def _insight_a20_3(insights: dict[str, Any]) -> str:
    """A20.3: High-Balance Dormant Trend."""
    return _try_adaptive(insights, "High-balance dormant trend")


# =============================================================================
# REGISTRY
# =============================================================================

HEADLINE_GENERATORS: dict[str, Any] = {
    # DCTR core (Phase 1a)
    "DCTR-1": _dctr_1,
    "DCTR-2": _dctr_2,
    "DCTR-3": _dctr_3,
    "DCTR-4": _dctr_4,
    "DCTR-5": _dctr_5,
    "DCTR-6": _dctr_6,
    "DCTR-7": _dctr_7,
    "DCTR-8": _dctr_8,
    # DCTR detail (Phase 1d/1g)
    "DCTR-9": _dctr_9,
    "DCTR-10": _dctr_10,
    "DCTR-11": _dctr_11,
    "DCTR-12": _dctr_12,
    "DCTR-13": _dctr_13,
    "DCTR-14": _dctr_14,
    "DCTR-15": _dctr_15,
    "DCTR-16": _dctr_16,
    "A7.4": _a7_4,
    "A7.5": _a7_5,
    "A7.6a": _a7_6a,
    "A7.6b": _a7_6b,
    "A7.7": _a7_7,
    "A7.8": _a7_8,
    "A7.9": _a7_9,
    "A7.10a": _a7_10a,
    "A7.10b": _a7_10b,
    "A7.13": _a7_13,
    "A7.14": _a7_14,
    "A7.15": _a7_15,
    # Attrition (Phase 1b)
    "A9.1": _attrition_1,
    "A9.2": _attrition_2,
    "A9.3": _attrition_3,
    "A9.4": _attrition_4,
    "A9.5": _attrition_5,
    "A9.6": _attrition_6,
    "A9.7": _attrition_7,
    "A9.8": _attrition_8,
    "A9.9": _attrition_9,
    "A9.10": _attrition_10,
    "A9.11": _attrition_11,
    "A9.12": _attrition_12,
    "A9.13": _attrition_13,
    # Reg E (Phase 1e) — ALL WIRED
    "A8.1": _rege_1,
    "A8.2": _rege_2,
    "A8.3": _rege_3,
    "A8.4a": _rege_4,
    "A8.4b": _rege_4b,
    "A8.4c": _rege_4c,
    "A8.5": _rege_5,
    "A8.6": _rege_6,
    "A8.7": _rege_7,
    "A8.10": _rege_10,
    "A8.11": _rege_11,
    "A8.12": _rege_12,
    "A8.13": _rege_13,
    # Value (Phase 1e)
    "A11.1": _value_1,
    "A11.2": _value_2,
    # Overview (Phase 1g) — A1b WIRED
    "A1": _overview_a1,
    "A1b": _overview_a1b,
    "A3": _overview_a3,
    # Insights (Phase 1f)
    "S1": _insight_s1,
    "S2": _insight_s2,
    "S3": _insight_s3,
    "S4": _insight_s4,
    "S5": _insight_s5,
    "S6": _insight_s6,
    "S7": _insight_s7,
    "S8": _insight_s8,
    # Insights extras — ALL WIRED
    "A18": _insight_a18,
    "A18.1": _insight_a18_1,
    "A18.2": _insight_a18_2,
    "A18.3": _insight_a18_3,
    "A19": _insight_a19,
    "A19.1": _insight_a19_1,
    "A19.2": _insight_a19_2,
    "A20": _insight_a20,
    "A20.1": _insight_a20_1,
    "A20.2": _insight_a20_2,
    "A20.3": _insight_a20_3,
}


# =============================================================================
# INSIGHTS KEY MAP
# =============================================================================
# Maps slide_id -> ctx.results key where insights are stored.
# Used by generate_headline() to look up the right data.

_INSIGHTS_KEY_MAP: dict[str, str] = {
    "DCTR-1": "dctr_1",
    "DCTR-2": "dctr_2",
    "DCTR-3": "dctr_3",
    "DCTR-4": "dctr_4",
    "DCTR-5": "dctr_5",
    "DCTR-6": "dctr_6",
    "DCTR-7": "dctr_7",
    "DCTR-8": "dctr_8",
    "DCTR-9": "dctr_9",
    "DCTR-10": "dctr_10",
    "DCTR-11": "dctr_11",
    "DCTR-12": "dctr_12",
    "DCTR-13": "dctr_13",
    "DCTR-14": "dctr_14",
    "DCTR-15": "dctr_15",
    "DCTR-16": "dctr_16",
    "A7.4": "dctr_segment_trends",
    "A7.5": "dctr_cohort",
    "A7.6a": "dctr_trend_hist",
    "A7.6b": "dctr_trend_compare",
    "A7.7": "dctr_funnel",
    "A7.8": "dctr_l12m_funnel",
    "A7.9": "dctr_elig_vs_non",
    "A7.10a": "dctr_branch_trend",
    "A7.10b": "dctr_branch_detail",
    "A7.13": "dctr_card_type",
    "A7.14": "dctr_acct_type",
    "A7.15": "dctr_extended",
    "A9.1": "attrition_1",
    "A9.2": "attrition_2",
    "A9.3": "attrition_3",
    "A9.4": "attrition_4",
    "A9.5": "attrition_5",
    "A9.6": "attrition_6",
    "A9.7": "attrition_7",
    "A9.8": "attrition_8",
    "A9.9": "attrition_9",
    "A9.10": "attrition_10",
    "A9.11": "attrition_11",
    "A9.12": "attrition_12",
    "A9.13": "attrition_13",
    "A8.1": "reg_e_1",
    "A8.2": "reg_e_2",
    "A8.3": "reg_e_3",
    "A8.4a": "reg_e_4",
    "A8.4b": "reg_e_4b",
    "A8.4c": "reg_e_4c",
    "A8.5": "reg_e_5",
    "A8.6": "reg_e_6",
    "A8.7": "reg_e_7",
    "A8.10": "reg_e_10",
    "A8.11": "reg_e_11",
    "A8.12": "reg_e_12",
    "A8.13": "reg_e_13",
    "A11.1": "value_1",
    "A11.2": "value_2",
    "A1": "a1",
    "A1b": "a1b",
    "A3": "a3",
    "S1": "impact_s1",
    "S2": "impact_s2",
    "S3": "impact_s3",
    "S4": "impact_s4",
    "S5": "impact_s5",
    "S6": "impact_s6",
    "S7": "impact_s7",
    "S8": "impact_s8",
    "A18": "branch_scorecard",
    "A18.1": "branch_scorecard_dctr",
    "A18.2": "branch_scorecard_rege",
    "A18.3": "branch_scorecard_attrition",
    "A19": "dormant",
    "A19.1": "dormant_detail",
    "A19.2": "dormant_segments",
    "A20": "dormant_high_balance",
    "A20.1": "dormant_high_balance_detail",
    "A20.2": "dormant_high_balance_branch",
    "A20.3": "dormant_high_balance_trend",
}


def insights_key(slide_id: str) -> str | None:
    """Map a slide_id to its ctx.results key, or None if unmapped."""
    return _INSIGHTS_KEY_MAP.get(slide_id)


def generate_headline(
    slide_id: str,
    insights: dict[str, Any],
    fallback_title: str = "",
) -> str:
    """Generate a conclusion headline for a slide.

    Returns the generated headline, or fallback_title if the generator
    is not registered, fails, or returns empty string.
    """
    gen = HEADLINE_GENERATORS.get(slide_id)
    if gen is None:
        return fallback_title
    try:
        # Some modules store insights nested under an "insights" key
        inner = insights.get("insights", insights)
        result = gen(inner)
        return result if result else fallback_title
    except Exception:
        logger.warning("Headline generator failed for {sid}", sid=slide_id)
        return fallback_title
