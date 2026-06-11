"""Build an HTML review from the persisted run_report.json + charts dir.

The run_report.json (introduced in W4) carries slide_id, title, chart_path,
and module_id per slide. That's enough to drive html_review.builder without
needing the live ctx.all_slides list. Lets the UI surface an HTML preview
for any completed run -- no PowerPoint required.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from html_review.builder import SECTION_ORDER, build_html
from html_review.model import ClientMeta


_MODULE_TO_SECTION = {
    "overview": "overview",
    "stat_codes": "overview",
    "product_codes": "overview",
    "eligibility": "overview",
    "dctr": "dctr",
    "rege": "rege",
    "reg_e": "rege",
    "attrition": "attrition",
    "value": "value",
    "mailer": "mailer",
    "transaction": "transaction",
    "ics": "ics",
    "insights": "insights",
}


def _section_for(slide_id: str, module_id: str) -> str:
    """Best-effort section derivation from slide_id prefix or module_id.

    More specific prefixes (A11, A12, A13, A14) checked before the generic A1
    overview prefix so VALUE / MAILER routing wins.
    """
    sid = (slide_id or "").upper()
    if sid.startswith("DCTR") or sid.startswith("A7"):
        return "dctr"
    if sid.startswith("REGE") or sid.startswith("A8"):
        return "rege"
    if sid.startswith("A9") or "ATTRITION" in sid:
        return "attrition"
    if sid.startswith("A11") or "VALUE" in sid:
        return "value"
    if sid.startswith("A12") or sid.startswith("A13") or sid.startswith("A14") or "MAILER" in sid:
        return "mailer"
    if sid.startswith("S") or "INSIGHT" in sid:
        return "insights"
    # Overview is the most generic A1 prefix -- check last so A11/A12/etc win.
    if sid.startswith("A1") or sid.startswith("OVERVIEW"):
        return "overview"
    # Fallback to module_id
    mid = (module_id or "").lower()
    for token, section in _MODULE_TO_SECTION.items():
        if mid.startswith(token):
            return section
    return "overview"


@dataclass
class _SlideStub:
    """Duck-typed AnalysisResultLike for html_review.builder."""
    slide_id: str
    title: str
    section: str
    chart_path: Path | None
    excel_data: dict[str, Any] | None = None
    notes: str = ""


def build_html_from_run_report(
    csm: str,
    month: str,
    client_id: str,
    completed_analysis_root: Path,
    presentations_root: Path,
    embed_images: bool = True,
    client_display_name: str = "",
) -> Path | None:
    """Build the html_review/index.html for a completed run. Returns path or None.

    Reads run_report.json from `completed_analysis_root/<csm>/<month>/<client_id>/`,
    writes the HTML to `presentations_root/<csm>/<month>/<client_id>/html_review/`.

    `embed_images=True` inlines every PNG as a base64 data URI so the operator
    can email the HTML or scp it without dragging the assets folder along.
    """
    analysis_dir = completed_analysis_root / csm / month / client_id
    _cands = sorted(
        analysis_dir.glob(f"{client_id}_{month}*_run_report.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if not _cands:
        return None
    report_path = _cands[0]

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    raw_slides = payload.get("slides") or []
    if not raw_slides:
        return None

    stubs: list[_SlideStub] = []
    for s in raw_slides:
        chart = s.get("chart_path") or ""
        cp = Path(chart) if chart and Path(chart).exists() else None
        if cp is None and s.get("has_chart"):
            # Best-effort fallback: look in charts/ for a PNG that contains slide_id
            sid_token = (s.get("slide_id", "") or "").lower().replace("-", "_").replace(".", "_")
            if sid_token:
                for cand in (analysis_dir / "charts").glob("*.png"):
                    if sid_token in cand.name.lower():
                        cp = cand
                        break
        stubs.append(_SlideStub(
            slide_id=s.get("slide_id", ""),
            title=s.get("title", ""),
            section=_section_for(s.get("slide_id", ""), s.get("module_id", "")),
            chart_path=cp,
            excel_data=None,
            notes=s.get("error", "") or "",
        ))

    # Month "2026.04" -> "2026-04" / "April 2026"
    month_dashes = month.replace(".", "-")
    try:
        year, mo = month.split(".")
        month_display = datetime(int(year), int(mo), 1).strftime("%B %Y")
    except ValueError:
        month_display = month

    client = ClientMeta(
        id=client_id,
        display_name=client_display_name or client_id,
        month=month_dashes,
        month_display=month_display,
        run_date=date.today().isoformat(),
    )

    out_dir = presentations_root / csm / month / client_id / "html_review"
    return build_html(stubs, client, out_dir, embed_images=embed_images)
