"""Attrition section -- Are We Losing Accounts?

Mirrors: 01_Analysis/00-Scripts/analytics/attrition/
Slide IDs: A9.1 through A9.13
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["a9", "att"]

_LAYOUT_MAP = {
    "A9.1": (LAYOUT_CUSTOM, "screenshot_kpi"),
    "A9.2": (LAYOUT_CUSTOM, "screenshot"),
    "A9.3": (LAYOUT_CUSTOM, "screenshot"),
    "A9.4": (LAYOUT_CUSTOM, "screenshot"),
    "A9.5": (LAYOUT_CUSTOM, "screenshot"),
    "A9.6": (LAYOUT_CUSTOM, "screenshot"),
    "A9.7": (LAYOUT_CUSTOM, "screenshot"),
    "A9.8": (LAYOUT_CUSTOM, "screenshot"),
    "A9.9": (LAYOUT_CUSTOM, "screenshot_kpi"),
    "A9.10": (LAYOUT_CUSTOM, "screenshot_kpi"),
    "A9.11": (LAYOUT_CUSTOM, "screenshot_kpi"),
    "A9.12": (LAYOUT_CUSTOM, "screenshot_kpi"),
    "A9.13": (LAYOUT_CUSTOM, "screenshot"),
}

_MERGES = [
    ("A9.3", "A9.6", "Attrition Profile: Open vs Closed & Personal vs Business"),
]

_APPENDIX_IDS = {
    "A9.2",
    "A9.4",
    "A9.5",
    "A9.7",
    "A9.8",
    "A9.13",
}


def register() -> SectionSpec:
    """Return the Attrition section specification."""
    return SectionSpec(
        key="attrition",
        label="Are We Losing Accounts?",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        merges=_MERGES,
        appendix_ids=_APPENDIX_IDS,
    )
