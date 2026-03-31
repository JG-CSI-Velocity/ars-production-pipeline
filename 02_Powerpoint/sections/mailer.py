"""Mailer section -- How Effective Are the Mailer Campaigns?

Mirrors: 01_Analysis/00-Scripts/analytics/mailer/
Slide IDs: A12.x, A13.x, A14.x, A15.x, A16.x, A17.x

This is the most complex section due to month-based grouping:
- Per-month groups: summary (A13.{month}) + swipes (A12.{month}.Swipes) + spend (A12.{month}.Spend)
- Most recent 2 months -> main deck, older months -> appendix
- Aggregate and impact slides stay in main
"""

from __future__ import annotations

import re

from ._base import LAYOUT_CUSTOM, LAYOUT_MAIL_SUMMARY, SectionSpec

_PREFIXES = ["a12", "a13", "a14", "a15", "a16", "a17", "mail"]

_LAYOUT_MAP = {
    "A13.5": (LAYOUT_CUSTOM, "screenshot"),
    "A13.6": (LAYOUT_CUSTOM, "screenshot"),
    "A14.2": (LAYOUT_CUSTOM, "screenshot"),
    "A15.1": (LAYOUT_CUSTOM, "screenshot"),
    "A15.2": (LAYOUT_CUSTOM, "screenshot"),
    "A15.3": (LAYOUT_CUSTOM, "screenshot"),
    "A15.4": (LAYOUT_CUSTOM, "screenshot"),
    "A16.1": (LAYOUT_CUSTOM, "screenshot"),
    "A16.2": (LAYOUT_CUSTOM, "screenshot"),
    "A16.3": (LAYOUT_CUSTOM, "screenshot"),
    "A16.4": (LAYOUT_CUSTOM, "screenshot"),
    "A16.5": (LAYOUT_CUSTOM, "screenshot"),
    "A16.6": (LAYOUT_CUSTOM, "screenshot"),
    "A17.1": (LAYOUT_CUSTOM, "screenshot"),
    "A17.2": (LAYOUT_CUSTOM, "screenshot"),
    "A17.3": (LAYOUT_CUSTOM, "screenshot"),
}

_MONTH_ABBRS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
    "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
    "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _prefix_fallback(slide_id: str) -> tuple[int, str] | None:
    """Match dynamic slide IDs like A12.Nov25.Swipes, A13.Jan26."""
    sid = slide_id.lower()
    if sid.startswith("a12"):
        return (LAYOUT_MAIL_SUMMARY, "screenshot")
    if sid.startswith("a13") and sid not in ("a13.5", "a13.6"):
        return (LAYOUT_MAIL_SUMMARY, "mailer_summary")
    if sid.startswith("a16"):
        return (LAYOUT_CUSTOM, "screenshot")
    if sid.startswith("a17"):
        return (LAYOUT_CUSTOM, "screenshot")
    return None


def _parse_mailer_month(slide_id: str) -> tuple[int, int] | None:
    """Extract (year, month_num) from slide IDs like A13.Jan26."""
    m = re.search(r"\.([A-Z][a-z]{2})(\d{2})", slide_id)
    if m:
        abbr, yr = m.group(1), int(m.group(2))
        if abbr in _MONTH_ABBRS:
            return (2000 + yr, _MONTH_ABBRS[abbr])
    return None


def _consolidate_mailer(results: list) -> tuple[list, list]:
    """Split mailer results into main deck + appendix.

    Per-month groups: summary (A13.{month}) + swipes (A12.{month}.Swipes)
    + spend (A12.{month}.Spend).
    Most recent 2 months -> main. Older months -> appendix.
    A14.2 (mailer revisit) goes with most recent month.
    Aggregate and impact slides stay in main.
    """
    month_slides: dict[tuple[int, int], list] = {}
    aggregate = []
    revisit = []
    impact = []
    mailer_app = []
    other = []

    for r in results:
        sid = getattr(r, "slide_id", "")
        ym = _parse_mailer_month(sid)
        if ym:
            month_slides.setdefault(ym, []).append(r)
        elif sid.startswith("A13.Agg") or sid == "A13.5":
            aggregate.append(r)
        elif sid == "A13.6":
            mailer_app.append(r)
        elif sid.startswith("A14"):
            revisit.append(r)
        elif sid.startswith("A15"):
            impact.append(r)
        elif sid.startswith("A16"):
            impact.append(r)
        elif sid.startswith("A17"):
            impact.append(r)
        else:
            other.append(r)

    sorted_months = sorted(month_slides.keys(), reverse=True)

    def _intra_month_key(r) -> int:
        sid = getattr(r, "slide_id", "")
        if sid.startswith("A13."):
            return 0
        if "Swipes" in sid:
            return 1
        if "Spend" in sid:
            return 2
        return 3

    main_slides: list = []
    appendix_slides: list = []

    for i, ym in enumerate(sorted_months):
        group = sorted(month_slides[ym], key=_intra_month_key)
        if i < 2:
            main_slides.extend(group)
            if i == 0:
                main_slides.extend(revisit)
        else:
            appendix_slides.extend(group)

    main_slides.extend(aggregate)
    main_slides.extend(impact)
    main_slides.extend(other)
    appendix_slides.extend(mailer_app)

    return main_slides, appendix_slides


def register() -> SectionSpec:
    """Return the Mailer section specification."""
    return SectionSpec(
        key="mailer",
        label="How Effective Are the Mailer Campaigns?",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        prefix_fallback=_prefix_fallback,
        consolidate=_consolidate_mailer,
    )
