"""Shared mailer constants and helpers used by insights, response, and impact.

Ported from mailer_common.py (144 lines).
"""

from __future__ import annotations

import re

import pandas as pd
from loguru import logger

from ars_analysis.analytics.base import AnalysisResult
from ars_analysis.pipeline.context import PipelineContext

# ---------------------------------------------------------------------------
# Segment constants
# ---------------------------------------------------------------------------

RESPONSE_SEGMENTS = ["NU 5+", "TH-10", "TH-15", "TH-20", "TH-25"]
MAILED_SEGMENTS = ["NU", "TH-10", "TH-15", "TH-20", "TH-25"]
TH_SEGMENTS = ["TH-10", "TH-15", "TH-20", "TH-25"]

# Column-name patterns
SPEND_PATTERN = re.compile(r"^[A-Z][a-z]{2}\d{2} Spend$")
SWIPE_PATTERN = re.compile(r"^[A-Z][a-z]{2}\d{2} Swipes$")

# Segment colors (shared across all mailer modules)
SEGMENT_COLORS: dict[str, str] = {
    "No-Mail": "#F5F5F5",
    "Non-Responders": "#404040",
    "NU 5+": "#E74C3C",
    "NU": "#E74C3C",
    "TH-10": "#3498DB",
    "TH-15": "#2ECC71",
    "TH-20": "#F39C12",
    "TH-25": "#9B59B6",
}

# Valid response mapping per mailed segment
VALID_RESPONSES: dict[str, list[str]] = {
    "NU": ["NU 5+"],
    "TH-10": ["TH-10"],
    "TH-15": ["TH-15"],
    "TH-20": ["TH-20"],
    "TH-25": ["TH-25"],
}

# Account-age buckets for A14.2
AGE_SEGMENTS: list[tuple[str, int, int]] = [
    ("< 2 years", 0, 2),
    ("2-5 years", 2, 5),
    ("5-10 years", 5, 10),
    ("10-20 years", 10, 20),
    ("> 20 years", 20, 999),
]

# ---------------------------------------------------------------------------
# A15 Ladder scoring
# ---------------------------------------------------------------------------

SCORE_MAP: dict[str, int] = {
    "NU 1-4": 1,  # tracked but NOT a success
    "NU 5+": 2,
    "TH-10": 3,
    "TH-15": 4,
    "TH-20": 5,
    "TH-25": 6,
}
SUCCESSFUL_TIERS = ["NU 5+", "TH-10", "TH-15", "TH-20", "TH-25"]

MOVEMENT_COLORS: dict[str, str] = {
    "First": "#2E7D32",
    "Up": "#1976D2",
    "Same": "#FBC02D",
    "Down": "#C62828",
}

# Member-age buckets (from DOB)
MEMBER_AGE_BUCKETS: list[tuple[str, int, int]] = [
    ("18-30", 18, 30),
    ("30-45", 30, 45),
    ("45-60", 45, 60),
    ("60+", 60, 200),
]


# ---------------------------------------------------------------------------
# A15 classification
# ---------------------------------------------------------------------------


def classify_responder(
    current_resp: str | None,
    prior_responses: list[str | None],
) -> dict:
    """Classify a responder vs their most recent prior success.

    Returns dict with keys:
      include  -- True only if current tier is successful (score >= 2)
      type     -- "First" (no prior success) or "Repeat"
      movement -- "Up" / "Same" / "Down" / None (only set for Repeat)
    """
    current_score = SCORE_MAP.get(current_resp or "", 0)
    if current_score < 2:
        return {"include": False}

    # Find most recent prior successful response (score >= 2)
    prior_score: int | None = None
    for resp in reversed(prior_responses):
        s = SCORE_MAP.get(resp or "", 0)
        if s >= 2:
            prior_score = s
            break

    if prior_score is None:
        return {"include": True, "type": "First", "movement": None}

    if current_score > prior_score:
        movement = "Up"
    elif current_score < prior_score:
        movement = "Down"
    else:
        movement = "Same"

    return {"include": True, "type": "Repeat", "movement": movement}


def analyze_ladder(
    data: pd.DataFrame,
    pairs: list[tuple[str, str, str]],
    month_idx: int,
) -> dict | None:
    """Aggregate ladder stats for month at *month_idx*.

    Returns None when month_idx == 0 (no prior history).
    Otherwise returns dict with first_count, repeat_count,
    movement_up/same/down, total_successful.
    """
    if month_idx < 1:
        return None

    _, resp_col, _ = pairs[month_idx]
    prior_resp_cols = [rc for _, rc, _ in pairs[:month_idx]]

    result = {
        "first_count": 0,
        "repeat_count": 0,
        "movement_up": 0,
        "movement_same": 0,
        "movement_down": 0,
        "total_successful": 0,
        "distribution": {t: 0 for t in SUCCESSFUL_TIERS},
    }

    # Only rows with a response in THIS wave can become ladder entries; every
    # other row hits the NaN guard below and is skipped. Restricting iteration to
    # responded rows avoids a full member-table iterrows() on every wave -- the
    # O(rows x waves^2) cost that made mailer.response the run bottleneck (#208).
    # Output is unchanged: the excluded rows are exactly the ones the NaN guard
    # already dropped.
    responded = data[data[resp_col].notna()]
    for _, row in responded.iterrows():
        current = row.get(resp_col)
        if pd.isna(current):
            continue
        current = str(current).strip()

        priors = [
            str(row.get(c)).strip() if pd.notna(row.get(c)) else None
            for c in prior_resp_cols
        ]

        cls = classify_responder(current, priors)
        if not cls["include"]:
            continue

        result["total_successful"] += 1
        if current in result["distribution"]:
            result["distribution"][current] += 1

        if cls["type"] == "First":
            result["first_count"] += 1
        else:
            result["repeat_count"] += 1
            mv = cls["movement"]
            if mv == "Up":
                result["movement_up"] += 1
            elif mv == "Same":
                result["movement_same"] += 1
            elif mv == "Down":
                result["movement_down"] += 1

    return result


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def parse_month(col_name: str) -> pd.Timestamp:
    """Parse MmmYY from a column name like 'Aug25 Mail' -> Timestamp."""
    try:
        return pd.to_datetime(col_name.split(" ")[0], format="%b%y")
    except Exception:
        return pd.NaT


def format_title(month_str: str) -> str:
    """Convert 'Aug25' -> 'August 2025'."""
    try:
        dt = pd.to_datetime(month_str, format="%b%y")
        return dt.strftime("%B %Y")
    except Exception:
        return month_str


# ---------------------------------------------------------------------------
# Column discovery
# ---------------------------------------------------------------------------


def discover_pairs(ctx: PipelineContext) -> list[tuple[str, str, str]]:
    """Return sorted list of (month, resp_col, mail_col) tuples.

    Caches result in ctx.results['_mailer_pairs'].
    Tries exact pattern first, then case-insensitive fallback.
    """
    cached = ctx.results.get("_mailer_pairs")
    if cached:
        return cached

    if ctx.data is None:
        logger.warning("discover_pairs: no data loaded")
        return []

    cols = list(ctx.data.columns)
    logger.info("discover_pairs: {n} columns in ODD", n=len(cols))

    # Exact match: "Aug25 Mail" pattern
    mail_cols = sorted(
        [c for c in cols if re.match(r"^[A-Z][a-z]{2}\d{2} Mail$", c)],
        key=parse_month,
    )

    # Fallback: case-insensitive, flexible spacing
    if not mail_cols:
        mail_cols = sorted(
            [c for c in cols if re.match(r"^[A-Za-z]{3}\d{2}\s*Mail\s*$", c, re.IGNORECASE)],
            key=lambda c: parse_month(c.strip()),
        )
        if mail_cols:
            logger.info("discover_pairs: found {n} mail columns via fuzzy match", n=len(mail_cols))

    if not mail_cols:
        # Log near-matches for debugging
        near = [c for c in cols if "mail" in c.lower() or "resp" in c.lower()]
        if near:
            logger.warning(
                "discover_pairs: 0 mail columns matched. Near-matches: {cols}",
                cols=near,
            )
        else:
            logger.warning("discover_pairs: 0 mail columns. No mail-like columns found at all.")
        ctx.results["_mailer_pairs"] = []
        return []

    logger.info("discover_pairs: {n} mail columns found: {cols}", n=len(mail_cols), cols=mail_cols)

    pairs: list[tuple[str, str, str]] = []
    for mc in mail_cols:
        # Extract month portion (strip trailing " Mail" or " mail")
        month = re.sub(r"\s*[Mm]ail\s*$", "", mc).strip()
        # Try exact resp column, then case-insensitive
        rc = f"{month} Resp"
        if rc not in cols:
            # Fuzzy: look for case-insensitive resp match
            rc_matches = [
                c for c in cols if re.match(rf"^{re.escape(month)}\s*Resp\s*$", c, re.IGNORECASE)
            ]
            rc = rc_matches[0] if rc_matches else None
        if rc and rc in cols and ctx.data[rc].notna().any():
            pairs.append((month, rc, mc))
        elif rc and rc in cols:
            logger.info("discover_pairs: {mc} has Resp column but all NaN, skipping", mc=mc)
        else:
            logger.info("discover_pairs: {mc} has no matching Resp column", mc=mc)

    # Client-specific cutoff for client 1200
    if ctx.client.client_id == "1200" and pairs:
        cutoff = pd.to_datetime("Apr24", format="%b%y")
        pairs = [(m, r, ml) for m, r, ml in pairs if parse_month(m) >= cutoff]

    logger.info("discover_pairs: {n} valid pairs found", n=len(pairs))
    ctx.results["_mailer_pairs"] = pairs
    return pairs


def discover_metric_cols(
    ctx: PipelineContext,
) -> tuple[list[str], list[str]]:
    """Return (spend_cols, swipe_cols) sorted chronologically."""
    if ctx.data is None:
        return [], []

    cols = list(ctx.data.columns)
    spend_cols = sorted([c for c in cols if SPEND_PATTERN.match(c)], key=parse_month)
    swipe_cols = sorted([c for c in cols if SWIPE_PATTERN.match(c)], key=parse_month)

    if ctx.client.client_id == "1200":
        cutoff = pd.to_datetime("Apr24", format="%b%y")
        spend_cols = [c for c in spend_cols if parse_month(c) >= cutoff]
        swipe_cols = [c for c in swipe_cols if parse_month(c) >= cutoff]

    if not spend_cols and not swipe_cols:
        near = [c for c in cols if "spend" in c.lower() or "swipe" in c.lower()]
        if near:
            logger.warning("discover_metric_cols: 0 matches. Near-matches: {cols}", cols=near)
        else:
            logger.info("discover_metric_cols: no Spend/Swipes columns in ODD")
    else:
        logger.info(
            "discover_metric_cols: {s} spend, {w} swipe columns",
            s=len(spend_cols),
            w=len(swipe_cols),
        )

    return spend_cols, swipe_cols


# ---------------------------------------------------------------------------
# Mask builders
# ---------------------------------------------------------------------------


def build_responder_mask(data: pd.DataFrame, pairs: list[tuple[str, str, str]]) -> pd.Series:
    """Boolean Series: True for any account that responded in any month."""
    mask = pd.Series(False, index=data.index)
    for _, resp_col, _ in pairs:
        mask |= data[resp_col].isin(RESPONSE_SEGMENTS)
    return mask


def build_mailed_mask(data: pd.DataFrame, pairs: list[tuple[str, str, str]]) -> pd.Series:
    """Boolean Series: True for any account mailed in any month."""
    mask = pd.Series(False, index=data.index)
    for _, _, mail_col in pairs:
        mask |= data[mail_col].isin(MAILED_SEGMENTS)
    return mask


# ---------------------------------------------------------------------------
# Month-level segment analysis (used by response module)
# ---------------------------------------------------------------------------


def analyze_month(data: pd.DataFrame, resp_col: str, mail_col: str) -> tuple[dict, int, int, float]:
    """Compute response stats for one mail month.

    Returns (seg_details, total_mailed, total_resp, overall_rate).
    seg_details: dict keyed by display segment with {mailed, responders, rate}.
    """
    seg_details: dict = {}
    for seg in MAILED_SEGMENTS:
        seg_data = data[data[mail_col] == seg]
        n_mailed = len(seg_data)
        if n_mailed == 0:
            continue
        valid = VALID_RESPONSES[seg]
        n_resp = len(seg_data[seg_data[resp_col].isin(valid)])
        rate = n_resp / n_mailed * 100 if n_mailed > 0 else 0
        display = "NU 5+" if seg == "NU" else seg
        seg_details[display] = {
            "mailed": n_mailed,
            "responders": n_resp,
            "rate": rate,
        }

    total_mailed = sum(d["mailed"] for d in seg_details.values())
    total_resp = sum(d["responders"] for d in seg_details.values())
    overall_rate = total_resp / total_mailed * 100 if total_mailed > 0 else 0

    return seg_details, total_mailed, total_resp, overall_rate


# ---------------------------------------------------------------------------
# "Inside the Numbers" -- responder characteristics
# ---------------------------------------------------------------------------


def _parsed_date_cols(ctx: PipelineContext, data: pd.DataFrame) -> dict[str, pd.Series]:
    """Parse wave-invariant member date columns once per run.

    ``compute_inside_numbers`` runs once per mail wave against the same full
    member table, so parsing Date Opened / DOB (format="mixed", pandas' slow
    per-element path) on every wave was pure waste. Cache the parsed datetime
    Series on the run context and reuse across waves. When called with a frame
    other than ctx.data, parse it directly without caching.
    """
    cols = ("Date Opened", "DOB")
    if data is getattr(ctx, "data", None):
        cache = ctx.results.setdefault("_mailer_parsed_dates", {})
        if "_built" not in cache:
            for col in cols:
                if col in data.columns:
                    cache[col] = pd.to_datetime(data[col], errors="coerce", format="mixed")
            cache["_built"] = True
        return cache
    return {
        col: pd.to_datetime(data[col], errors="coerce", format="mixed")
        for col in cols
        if col in data.columns
    }


def compute_inside_numbers(
    ctx: PipelineContext,
    data: pd.DataFrame,
    resp_col: str,
    *,
    ladder: dict | None = None,
) -> list[tuple[str, str]]:
    """Compute responder characteristic metrics for mailer summary slides.

    Returns list of (percentage_string, description) tuples, e.g.:
      ("42%", "of Responders were accounts opened fewer than 2 years ago")
      ("68%", "of Responders opted into Reg E")

    Optional *ladder* dict from analyze_ladder() enriches with first/repeat
    and movement stats.
    """
    metrics: list[tuple[str, str]] = []
    responders = data[data[resp_col].isin(RESPONSE_SEGMENTS)]
    n_resp = len(responders)
    if n_resp == 0:
        return metrics

    # Date Opened / DOB are wave-invariant, but were re-parsed with the slow
    # format="mixed" path on every wave. Parse once per run, then subset to this
    # wave's responders -- identical values, redundant re-parsing removed (#208).
    _parsed = _parsed_date_cols(ctx, data)
    do_full = _parsed.get("Date Opened")
    dob_full = _parsed.get("DOB")

    # 1. Account age <2yr (existing)
    if do_full is not None:
        do = do_full.loc[responders.index]
        age_years = (pd.Timestamp.now() - do).dt.days / 365.25
        under_2 = int((age_years < 2).sum())
        pct = under_2 / n_resp * 100
        metrics.append((f"{pct:.0f}%", "of Responders were accounts opened fewer than 2 years ago"))

    # 2. Member age dominant bucket (from DOB)
    if dob_full is not None:
        dob = dob_full.loc[responders.index]
        valid_dob = dob.notna()
        if valid_dob.sum() > 0:
            member_ages = (pd.Timestamp.now() - dob[valid_dob]).dt.days / 365.25
            best_label, best_pct = "", 0.0
            total_valid = len(member_ages)
            for label, lo, hi in MEMBER_AGE_BUCKETS:
                cnt = int(((member_ages >= lo) & (member_ages < hi)).sum())
                bucket_pct = cnt / total_valid * 100 if total_valid > 0 else 0
                if bucket_pct > best_pct:
                    best_pct = bucket_pct
                    best_label = label
            if best_pct > 0:
                metrics.append((f"{best_pct:.0f}%", f"of Responders aged {best_label}"))

    # 3. Reg E opt-in (existing)
    opt_list = ctx.client.reg_e_opt_in
    if opt_list:
        reg_e_col = ctx.client.reg_e_column
        if not reg_e_col and ctx.data is not None:
            from ars_analysis.analytics.rege._helpers import detect_reg_e_column

            reg_e_col = detect_reg_e_column(ctx.data)
        if reg_e_col and reg_e_col in data.columns:
            opted_in = responders[reg_e_col].astype(str).str.strip()
            n_opted = int(opted_in.isin(opt_list).sum())
            pct = n_opted / n_resp * 100
            metrics.append((f"{pct:.0f}%", "of Responders opted into Reg E"))

    # 4. First-time responders (from ladder)
    if ladder and ladder["total_successful"] > 0:
        first_pct = ladder["first_count"] / ladder["total_successful"] * 100
        metrics.append((f"{first_pct:.0f}%", "First-time responders"))

        # 5. Repeat movement up
        if ladder["repeat_count"] > 0:
            up_pct = ladder["movement_up"] / ladder["repeat_count"] * 100
            metrics.append(
                (f"{up_pct:.0f}%", "of repeat responders moved up the ladder")
            )

    return metrics


def _generate_mailer_commentary(
    seg_details: dict,
    total_mailed: int,
    total_resp: int,
    overall_rate: float,
    ladder: dict | None = None,
    prev_rate: float | None = None,
) -> list[str]:
    """Generate 2-4 insight sentences for the mailer summary slide commentary.

    Covers: best segment performance, segment gap, response concentration,
    and ladder movement. Returns a list of plain strings (one per sentence).
    """
    bullets: list[str] = []

    # 1. Best performing segment (minimum 50 mailed to be meaningful)
    meaningful = {
        s: d for s, d in seg_details.items()
        if d.get("mailed", 0) >= 50
    }

    if meaningful:
        sorted_by_rate = sorted(
            meaningful.items(),
            key=lambda x: x[1]["rate"],
            reverse=True,
        )
        best_seg, best_data = sorted_by_rate[0]
        bullets.append(
            f"{best_seg} led with a {best_data['rate']:.1f}% response rate "
            f"({best_data['responders']:,} of {best_data['mailed']:,} mailed)."
        )

        # 2. Segment gap -- only call it out if the spread is meaningful
        if len(sorted_by_rate) >= 2:
            worst_seg, worst_data = sorted_by_rate[-1]
            if worst_data["rate"] > 0:
                ratio = best_data["rate"] / worst_data["rate"]
                if ratio >= 2.0:
                    bullets.append(
                        f"{best_seg} responded at {ratio:.1f}x the rate of "
                        f"{worst_seg} ({worst_data['rate']:.1f}%) -- "
                        f"higher-challenge segments are driving disproportionate results."
                    )
                elif ratio >= 1.3:
                    bullets.append(
                        f"{worst_seg} trailed at {worst_data['rate']:.1f}% "
                        f"({worst_data['responders']:,} of {worst_data['mailed']:,} mailed)."
                    )

    # 3. Response concentration -- top 2 segments as share of all responses
    if seg_details and total_resp > 0:
        sorted_by_count = sorted(
            seg_details.items(),
            key=lambda x: x[1]["responders"],
            reverse=True,
        )
        top2_resp = sum(d["responders"] for _, d in sorted_by_count[:2])
        top2_pct = top2_resp / total_resp * 100
        top2_names = " and ".join(s for s, _ in sorted_by_count[:2])
        if top2_pct >= 55:
            bullets.append(
                f"{top2_names} accounted for {top2_pct:.0f}% of all responses this wave."
            )

    # 4. Ladder movement (only available from 2nd wave onward)
    if ladder and ladder.get("total_successful", 0) > 0:
        total_s = ladder["total_successful"]
        repeat_total = ladder.get("repeat_count", 0)
        first_pct = ladder["first_count"] / total_s * 100

        if repeat_total > 0:
            up_pct = ladder["movement_up"] / repeat_total * 100
            if up_pct >= 40:
                bullets.append(
                    f"{up_pct:.0f}% of repeat responders climbed to a higher challenge tier -- "
                    f"the program is building upward momentum."
                )
            else:
                bullets.append(
                    f"{first_pct:.0f}% of responders were new to the program this wave; "
                    f"{up_pct:.0f}% of repeat accounts moved up the challenge ladder."
                )
        elif first_pct >= 70:
            bullets.append(
                f"{first_pct:.0f}% of responders were engaging with the program "
                f"for the first time this wave."
            )

    # Fallback: plain summary if no bullets were generated
    if not bullets:
        bullets.append(
            f"{total_resp:,} accounts responded from {total_mailed:,} mailed "
            f"({overall_rate:.1f}% overall response rate)."
        )

    return bullets


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
