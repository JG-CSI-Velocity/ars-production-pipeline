"""Step: per-run denominator-law audit.

Writes rates_audit.csv next to run_manifest.json, one row per slide that ships
a rate, recording the denominator the rate was computed against. Validates each
row against the 4-layer framework (Eligible / Eligible Personal / Eligible Business
/ Open) and emits AnomalyFlag(WARN) on the run manifest for every violation.

Per project_denominator_framework.md (LAW):
- Eligible is the primary default.
- Eligible Personal / Eligible Business are sub-views for inherently personal-
  or business-only metrics.
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
    "Eligible Business",
    "Open",
))

# Slides explicitly permitted to use Open as primary denominator (reference framing).
OPEN_ALLOWLIST: frozenset[str] = frozenset((
    "dctr_2",       # Open vs Eligible methodology slide
    "DCTR-2",
))

# Default denominator label per slide_id prefix. Modules can override by stamping
# `denominator_label` on the AnalysisResult directly.
DEFAULT_BY_PREFIX: dict[str, str] = {
    "dctr_": "Eligible",
    "DCTR-": "Eligible",
    "rege_": "Eligible Personal",
    "REGE-": "Eligible Personal",
    "reg_e_": "Eligible Personal",
    "attrition_": "Eligible",
    "A9": "Eligible",
    "mailer_": "Eligible",
    "value_": "Eligible",
    "A11": "Eligible",
    "insights_": "Eligible",
    "S1": "Eligible",
    "S6": "Eligible",
    "S8": "Eligible",
    "branch_scorecard": "Eligible",
    "a19_": "Eligible",
    "overview_": "Eligible",
    "A1": "Eligible",
}


def _default_label(slide_id: str) -> str:
    """Infer the default denominator label for a slide_id when modules haven't stamped one."""
    for prefix, label in DEFAULT_BY_PREFIX.items():
        if slide_id.startswith(prefix):
            return label
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

    path = out_dir / "rates_audit.csv"
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

    # Surface violations on the manifest
    _mf = getattr(ctx, "manifest", None)
    if _mf is not None and violations > 0:
        try:
            from ars_analysis.pipeline.manifest import AnomalyFlag, FlagLevel
            # Attach to the first section as a run-wide flag; scorecard surfaces it.
            target = _mf.sections[0] if _mf.sections else None
            if target is not None:
                target.anomaly_flags.append(AnomalyFlag(
                    level=FlagLevel.WARN,
                    message=f"Denominator law: {violations} violation(s) (see rates_audit.csv)",
                ))
        except Exception as exc:
            logger.warning("manifest flag for rates_audit failed: {err}", err=exc)

    return path, violations


def step_audit(ctx: PipelineContext) -> None:
    """Pipeline step entrypoint. Never raises (audit failure cannot break the run)."""
    try:
        write_rates_audit(ctx)
    except Exception as exc:
        logger.warning("rates_audit step failed: {err}", err=exc)
