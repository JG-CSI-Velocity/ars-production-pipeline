"""Insights section -- What Should We Do Next?

Mirrors: 01_Analysis/00-Scripts/analytics/insights/
Slide IDs: S1-S8, A18.x, A19.x, A20.x
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "a18", "a19", "a20"]

_LAYOUT_MAP = {
    "S1": (LAYOUT_CUSTOM, "screenshot"),
    "S2": (LAYOUT_CUSTOM, "screenshot"),
    "S3": (LAYOUT_CUSTOM, "screenshot"),
    "S4": (LAYOUT_CUSTOM, "screenshot"),
    "S5": (LAYOUT_CUSTOM, "screenshot"),
    "S6": (LAYOUT_CUSTOM, "screenshot"),
    "S7": (LAYOUT_CUSTOM, "screenshot"),
    "S8": (LAYOUT_CUSTOM, "screenshot"),
    "A18.1": (LAYOUT_CUSTOM, "screenshot"),
    "A18.2": (LAYOUT_CUSTOM, "screenshot"),
    "A18.3": (LAYOUT_CUSTOM, "screenshot"),
    "A19.1": (LAYOUT_CUSTOM, "screenshot"),
    "A19.2": (LAYOUT_CUSTOM, "screenshot"),
    "A20.1": (LAYOUT_CUSTOM, "screenshot"),
    "A20.2": (LAYOUT_CUSTOM, "screenshot"),
    "A20.3": (LAYOUT_CUSTOM, "screenshot"),
}


def register() -> SectionSpec:
    """Return the Insights section specification."""
    return SectionSpec(
        key="insights",
        label="What Should We Do Next?",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
    )
