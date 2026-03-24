"""Preamble -- the 13 intro slides that precede analysis content.

Title, executive dashboard, section dividers, and blank placeholders
for manual content (financial performance, revenue, lift matrix, etc.).
"""

from __future__ import annotations

import calendar
import math
from pathlib import Path

from ._base import (
    LAYOUT_CONTENT,
    LAYOUT_CUSTOM,
    LAYOUT_SECTION_ALT,
    LAYOUT_TITLE,
    LAYOUT_TITLE_DARK,
    LAYOUT_TITLE_RPE,
)


def _slide_content(slide_type, title, layout_index, kpis=None, images=None, notes_text=None):
    """Lightweight dict-based slide content for preamble slides.

    Returns a dict that the assembler converts to SlideContent.
    """
    return {
        "slide_type": slide_type,
        "title": title,
        "layout_index": layout_index,
        "kpis": kpis,
        "images": images,
        "notes_text": notes_text,
    }


def build_preamble_slides(client_name: str, month: str) -> list[dict]:
    """Build the 13 preamble slides that precede analysis content."""
    try:
        month_num = int(month.split(".")[1]) if "." in month else 1
        year = month.split(".")[0] if "." in month else "2026"
        month_name = calendar.month_name[month_num]
    except (ValueError, IndexError):
        month_name = ""
        year = ""

    title_date = f"{month_name} {year}" if month_name else month

    return [
        # P01: Master title
        _slide_content("title", f"{client_name}\nAccount Revenue Solution | {title_date}",
                        LAYOUT_TITLE_RPE),
        # P02: Executive Dashboard (replaced at runtime with KPI dashboard)
        _slide_content("blank", "Agenda", LAYOUT_CONTENT),
        # P03: Program Performance divider
        _slide_content("title", f"{client_name}\nProgram Performance | {title_date}",
                        LAYOUT_TITLE),
        # P04: Executive Summary
        _slide_content("blank", "Executive Summary", LAYOUT_TITLE_DARK),
        # P05: Monthly Revenue
        _slide_content("blank", "Monthly Revenue \u2013 Last 12 Months", LAYOUT_CUSTOM),
        # P06: ARS Lift Matrix
        _slide_content("blank", "ARS Lift Matrix", LAYOUT_CUSTOM),
        # P07: ARS Mailer Revisit divider
        _slide_content("title", f"{client_name}\nARS Mailer Revisit | {title_date}",
                        LAYOUT_TITLE),
        # P08: Swipes placeholder (wired to most recent A12 Swipes at runtime)
        _slide_content("blank", "ARS Mailer Revisit \u2013 Swipes", LAYOUT_CUSTOM),
        # P09: Spend placeholder (wired to most recent A12 Spend at runtime)
        _slide_content("blank", "ARS Mailer Revisit \u2013 Spend", LAYOUT_CUSTOM),
        # P10: Mailer Summaries divider
        _slide_content("title", f"Mailer Summaries\n{client_name} | {title_date}",
                        LAYOUT_SECTION_ALT),
        # P11: All Program Results
        _slide_content("blank", f"All Program Results\n{client_name} | {title_date}",
                        LAYOUT_CONTENT),
        # P12: Program Responses to Date (wired to A13.5 at runtime)
        _slide_content("blank", "Program Responses to Date", LAYOUT_CUSTOM),
        # P13: Data Check Overview
        _slide_content("blank",
                        "Data Check Overview\nOur goal is turning non-users and light-users into heavy users",
                        LAYOUT_CUSTOM),
    ]


def build_executive_kpi(ctx_results: dict, title_date: str = "") -> dict:
    """Build executive KPI dashboard from pipeline results.

    Returns a dict that the assembler converts to SlideContent
    with slide_type="kpi_dashboard".
    """
    def _safe_get(key, subkey, default=None):
        data = ctx_results.get(key, {})
        if isinstance(data, dict):
            inner = data.get("insights", data)
            return inner.get(subkey, default)
        return default

    def _color_rate(value, good_above, warn_above):
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return "gray"
        if value >= good_above:
            return "green"
        if value >= warn_above:
            return "yellow"
        return "red"

    def _color_rate_low(value, good_below, warn_below):
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return "gray"
        if value <= good_below:
            return "green"
        if value <= warn_below:
            return "yellow"
        return "red"

    kpis: dict[str, str] = {}

    dctr = _safe_get("dctr_1", "overall_dctr")
    if dctr is not None and isinstance(dctr, (int, float)) and not math.isnan(dctr):
        color = _color_rate(dctr, 0.30, 0.20)
        kpis["DCTR Penetration"] = f"{dctr:.1%}|{color}"
    else:
        kpis["DCTR Penetration"] = "N/A|gray"

    rege = _safe_get("rege_1", "opt_in_rate")
    if rege is not None and isinstance(rege, (int, float)) and not math.isnan(rege):
        color = _color_rate(rege, 0.70, 0.50)
        kpis["Reg E Opt-In"] = f"{rege:.1%}|{color}"
    else:
        kpis["Reg E Opt-In"] = "N/A|gray"

    att = _safe_get("attrition_1", "overall_rate")
    if att is not None and isinstance(att, (int, float)) and not math.isnan(att):
        color = _color_rate_low(att, 0.05, 0.10)
        kpis["Attrition Rate"] = f"{att:.1%}|{color}"
    else:
        kpis["Attrition Rate"] = "N/A|gray"

    total = _safe_get("dctr_1", "total_accounts")
    if total is not None and isinstance(total, (int, float)) and total > 0:
        kpis["Total Accounts"] = f"{int(total):,}"
    else:
        kpis["Total Accounts"] = "N/A|gray"

    title = f"Executive Dashboard | {title_date}" if title_date else "Executive Dashboard"
    return _slide_content("kpi_dashboard", title, LAYOUT_CUSTOM, kpis=kpis)
