"""DCTR section -- How Active Are Debit Cards?

Mirrors: 01_Analysis/00-Scripts/analytics/dctr/
Slide IDs: DCTR-1 through DCTR-16, A7.4 through A7.15
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, LAYOUT_TWO_CONTENT, SectionSpec

_PREFIXES = ["dctr", "a7"]

_LAYOUT_MAP = {
    # DCTR penetration slides
    "DCTR-1": (LAYOUT_CUSTOM, "screenshot"),
    "DCTR-2": (LAYOUT_CUSTOM, "screenshot"),
    "DCTR-3": (LAYOUT_CUSTOM, "screenshot"),
    "DCTR-4": (LAYOUT_CUSTOM, "screenshot"),
    "DCTR-5": (LAYOUT_CUSTOM, "screenshot"),
    "DCTR-6": (LAYOUT_CUSTOM, "screenshot"),
    "DCTR-7": (LAYOUT_CUSTOM, "screenshot"),
    "DCTR-8": (LAYOUT_CUSTOM, "screenshot"),
    "DCTR-9": (LAYOUT_CUSTOM, "screenshot"),
    "DCTR-10": (LAYOUT_CUSTOM, "screenshot"),
    "DCTR-11": (LAYOUT_CUSTOM, "screenshot"),
    "DCTR-12": (LAYOUT_CUSTOM, "screenshot"),
    "DCTR-13": (LAYOUT_CUSTOM, "screenshot"),
    "DCTR-14": (LAYOUT_CUSTOM, "screenshot"),
    "DCTR-15": (LAYOUT_CUSTOM, "screenshot"),
    "DCTR-16": (LAYOUT_CUSTOM, "screenshot"),
    # A7.x analysis charts
    "A7.4": (LAYOUT_CUSTOM, "screenshot"),
    "A7.5": (LAYOUT_CUSTOM, "screenshot"),
    "A7.6a": (LAYOUT_CUSTOM, "screenshot"),
    "A7.6b": (LAYOUT_CUSTOM, "screenshot"),
    "A7.7": (LAYOUT_CUSTOM, "screenshot"),
    "A7.8": (LAYOUT_CUSTOM, "screenshot"),
    "A7.9": (LAYOUT_CUSTOM, "screenshot"),
    "A7.10a": (LAYOUT_CUSTOM, "screenshot"),
    "A7.10b": (LAYOUT_CUSTOM, "screenshot"),
    "A7.10c": (LAYOUT_CUSTOM, "screenshot_kpi"),
    "A7.11": (LAYOUT_CUSTOM, "screenshot"),
    "A7.12": (LAYOUT_CUSTOM, "screenshot"),
    "A7.13": (LAYOUT_CUSTOM, "screenshot"),
    "A7.14": (LAYOUT_CUSTOM, "screenshot"),
    "A7.15": (LAYOUT_CUSTOM, "screenshot"),
}

_MERGES = [
    ("A7.6a", "A7.4", "DCTR Trajectory: Recent Trend & Segments"),
    ("A7.7", "A7.8", "DCTR Funnel: Historical vs TTM"),
    ("A7.11", "A7.12", "DCTR Opportunity: Age Analysis"),
]

_APPENDIX_IDS = {
    "A7.5",
    "A7.6b",
    "A7.13",
    "A7.14",
    "A7.15",
    "A7.9",
    "A7.10b",
    "A7.10c",
    "DCTR-4",
    "DCTR-5",
    "DCTR-6",
    "DCTR-7",
    "DCTR-10",
    "DCTR-11",
    "DCTR-12",
    "DCTR-13",
    "DCTR-15",
    "DCTR-16",
}

_SKIP_IDS = {"DCTR-1"}


def register() -> SectionSpec:
    """Return the DCTR section specification."""
    return SectionSpec(
        key="dctr",
        label="How Active Are Debit Cards?",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        merges=_MERGES,
        appendix_ids=_APPENDIX_IDS,
        skip_ids=_SKIP_IDS,
        absorb_ids={"A11.1": "value"},
    )
