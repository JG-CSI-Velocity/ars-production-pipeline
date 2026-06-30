"""Step: per-run denominator-law audit.

Writes rates_audit.csv next to run_manifest.json, one row per slide that ships
a rate, recording the denominator the rate was computed against. Validates each
row against the 4-layer framework (Eligible / Eligible Personal / Eligible Business
/ Open) and emits AnomalyFlag(WARN) on the run manifest for every violation.

Per project_denominator_framework.md (LAW):
- Eligible is the primary default.
- Eligible Personal / Eligible Business are sub-views for inherently personal-
  or business-only metrics.
- Eligible Personal w/Debit is the Reg E base (owner decision 2026-06-11):
  opt-in rate = personal w/ Reg E / eligible personal with a debit card.
- L12M Exposure is the attrition base (closures can't anchor to the
  open-only Eligible subset): opened on/before window end AND not closed
  before window start.
- Open is reference framing only. Allowed as primary denominator on the methodology
  slide DCTR-2 only; flagged anywhere else.
"""

from __future__ import annotations

import csv
from pathlib import Path

from loguru import logger

from ars_analysis.pipeline.context import PipelineContext

LAW_LABELS: frozenset[str] = frozenset((
    "Eligible",
    "Eligible Personal",
    "Eligible Personal w/Debit",
    "Eligible Business",
    "L12M Exposure",
    "Open",
))

# Slides explicitly permitted to use Open as primary denominator (reference framing).
OPEN_ALLOWLIST: frozenset[str] = frozenset((
    "dctr_2",       # Open vs Eligible methodology slide
    "DCTR-2",
))

# Default denominator label per slide_id prefix. Modules can override by stamping
# `denominator_label` on the AnalysisResult directly.
#
# Ordering matters: more specific prefixes are listed first so they win over
# more general ones (A11, A12, A13, A14 must beat A1). _default_label sorts
# the prefixes by descending length at lookup time to enforce this.
DEFAULT_BY_PREFIX: dict[str, str] = {
    # DCTR section
    "dctr_":     "Eligible",
    "DCTR-":     "Eligible",
    "A7":        "Eligible",            # A7.1, A7.2, A7.3, A7.6a, A7 combo

    # Reg E section -- personal-only by regulation, debit-holders only by
    # definition (the opt-in governs ATM / one-time debit overdraft coverage)
    "rege_":     "Eligible Personal w/Debit",
    "REGE-":     "Eligible Personal w/Debit",
    "reg_e_":    "Eligible Personal w/Debit",
    "A8":        "Eligible Personal w/Debit",   # A8.1, A8.2, A8.3, A8.12

    # Attrition section. Attrition CANNOT anchor to "Eligible" -- that subset
    # is built from open accounts only and excludes every closure by
    # construction. Rates anchor to the standardized L12M exposure base
    # (attrition/_helpers.l12m_attrition: opened<=end AND not closed before
    # start; closures within the window).
    "attrition_":   "L12M Exposure",
    "ATTRITION-":   "L12M Exposure",    # W3 spec slide IDs (ATTRITION-MAIN-1)
    "A9":           "L12M Exposure",    # A9.1, A9.2, A9.11

    # Value section
    "value_":  "Eligible",
    "VALUE-":  "Eligible",              # W3 spec slide IDs (VALUE-MAIN-1)
    "A11":     "Eligible",              # A11.1, A11.2

    # Mailer section -- response rates anchor to Eligible (mailable subset is
    # numerator framing, not denominator narrowing)
    "mailer_": "Eligible",
    "A12":     "Eligible",
    "A13":     "Eligible",
    "A14":     "Eligible",
    "A16":     "Eligible",           # cohort spend trajectories

    # Insights / S-slides
    "insights_": "Eligible",
    "INSIGHTS-": "Eligible",            # W3 spec slide IDs (INSIGHTS-MAIN-1)
    "S1":        "Eligible",         # revenue gap
    "S2":        "Eligible",         # uplift
    "S3":        "Eligible",
    "S4":        "Eligible",
    "S5":        "Eligible",
    "S6":        "Eligible",         # opportunity map
    "S7":        "Eligible",
    "S8":        "Eligible",         # action plan
    "impact_s":  "Eligible",         # ctx.results key style

    # Branch scorecard (insights/branch_scorecard.py)
    "branch_scorecard": "Eligible",
    "a19_":             "Eligible",

    # Overview / A1.x intro slides
    "overview_": "Eligible",
    "OVERVIEW-": "Eligible",            # W3 spec slide IDs (OVERVIEW-MAIN-1)
    "A1":        "Eligible",            # A1, A1.1, A1.2 (sort-by-length picks A11 first)

    # Mailer W3 spec IDs
    "MAILER-":   "Eligible",

    # TXN spec slide IDs from #169
    "TXN-":      "Eligible",
}


def _default_label(slide_id: str) -> str:
    """Infer the default denominator label for a slide_id when modules haven't stamped one.

    Walks the registry in descending-prefix-length order so specific prefixes
    (e.g. 'A11') win over generic ones (e.g. 'A1').
    """
    sorted_prefixes = sorted(DEFAULT_BY_PREFIX.keys(), key=len, reverse=True)
    for prefix in sorted_prefixes:
        if slide_id.startswith(prefix):
            return DEFAULT_BY_PREFIX[prefix]
    return ""


def _looks_like_rate(result) -> bool:
    """True if the result surfaces a rate/ratio/share."""
    # Explicit stamp wins
    if getattr(result, "denominator_label", ""):
        return True
    # Heuristic: kpis containing a "%" or "rate" key
    kpis = getattr(result, "kpis", None) or {}
    for k, v in kpis.items():
        kl = str(k).lower()
        if "rate" in kl or "%" in kl or "share" in kl or "pct" in kl:
            return True
        vs = str(v)
        if vs.endswith("%") or "pp" in vs:
            return True
    return False


def write_rates_audit(ctx: PipelineContext) -> tuple[Path | None, int]:
    """Write rates_audit.csv and return (path, violation_count).

    Walks ctx.all_slides, emits one row per slide that ships a rate, defaults the
    denominator label from a per-section registry when modules haven't stamped one,
    and flags any row whose label is not in the 4-layer law.
    """
    out_dir = ctx.paths.base_dir
    if out_dir is None:
        return None, 0

    _product = (getattr(ctx, "product", None)
                or (getattr(ctx.settings, "product", "") if getattr(ctx, "settings", None) else "")
                or "")
    _suffix = "_txn" if str(_product).lower() == "txn" else ""
    path = out_dir / f"rates_audit{_suffix}.csv"
    rows: list[dict[str, object]] = []
    violations = 0

    for result in getattr(ctx, "all_slides", []) or []:
        if not _looks_like_rate(result):
            continue

        slide_id = getattr(result, "slide_id", "") or getattr(result, "name", "")
        label = getattr(result, "denominator_label", "") or _default_label(slide_id)
        denom_n = int(getattr(result, "denominator_n", 0) or 0)
        title = getattr(result, "title", "")
        kpis = getattr(result, "kpis", None) or {}

        # Compliance: must be in LAW_LABELS; Open only on the allowlist
        compliant = True
        violation_reason = ""
        if label not in LAW_LABELS:
            compliant = False
            violation_reason = f"label '{label}' not in 4-layer framework"
        elif label == "Open" and slide_id not in OPEN_ALLOWLIST:
            compliant = False
            violation_reason = "Open used as primary denominator outside reference allowlist"

        if not compliant:
            violations += 1

        # Pick a representative metric value to show in the CSV
        metric_name = ""
        metric_value = ""
        for k, v in kpis.items():
            kl = str(k).lower()
            if "rate" in kl or "%" in kl or "share" in kl:
                metric_name = str(k)
                metric_value = str(v)
                break

        rows.append({
            "slide_id": slide_id,
            "title": title,
            "metric": metric_name,
            "value": metric_value,
            "denominator_label": label,
            "denominator_n": denom_n,
            "framework_compliant": compliant,
            "violation_reason": violation_reason,
        })

    if not rows:
        logger.info("rates_audit: no rate-bearing slides found; skipping write")
        return None, 0

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        logger.info(
            "rates_audit.csv: {n} rates, {v} law violations",
            n=len(rows), v=violations,
        )
    except Exception as exc:
        logger.warning("rates_audit write failed: {err}", err=exc)
        return None, violations

    # Surface violations on the manifest as a run-level flag (scorecard renders it).
    _mf = getattr(ctx, "manifest", None)
    if _mf is not None and hasattr(_mf, "flag") and violations > 0:
        try:
            from ars_analysis.pipeline.manifest import FlagLevel
            _mf.flag(
                FlagLevel.WARN,
                f"Denominator law: {violations} violation(s) (see rates_audit.csv)",
            )
        except Exception as exc:
            logger.warning("manifest flag for rates_audit failed: {err}", err=exc)

    return path, violations


def step_audit(ctx: PipelineContext) -> None:
    """Pipeline step entrypoint. Never raises (audit failure cannot break the run)."""
    try:
        write_rates_audit(ctx)
    except Exception as exc:
        logger.warning("rates_audit step failed: {err}", err=exc)
