"""Reg E section -- Are Members Opting In to Overdraft Protection?

Mirrors: 01_Analysis/00-Scripts/analytics/rege/
Slide IDs: A8.1 through A8.13
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["a8", "rege"]

_LAYOUT_MAP = {
    "A8.1": (LAYOUT_CUSTOM, "screenshot"),
    "A8.2": (LAYOUT_CUSTOM, "screenshot"),
    "A8.3": (LAYOUT_CUSTOM, "screenshot"),
    "A8.4a": (LAYOUT_CUSTOM, "screenshot"),
    "A8.4b": (LAYOUT_CUSTOM, "screenshot"),
    "A8.4c": (LAYOUT_CUSTOM, "screenshot"),
    "A8.5": (LAYOUT_CUSTOM, "screenshot"),
    "A8.6": (LAYOUT_CUSTOM, "screenshot"),
    "A8.7": (LAYOUT_CUSTOM, "screenshot"),
    "A8.10": (LAYOUT_CUSTOM, "screenshot"),
    "A8.11": (LAYOUT_CUSTOM, "screenshot"),
    "A8.12": (LAYOUT_CUSTOM, "screenshot"),
    "A8.13": (LAYOUT_CUSTOM, "screenshot"),
}

_MERGES = [
    ("A8.10", "A8.11", "Reg E Funnel: All-Time vs TTM"),
    ("A8.5", "A8.6", "Reg E Opportunity: Age Analysis"),
]

_APPENDIX_IDS = {
    "A8.7",
    "A8.4c",
    "A8.2",
    "A8.1",
    "A8.12",
}


def register() -> SectionSpec:
    """Return the Reg E section specification."""
    return SectionSpec(
        key="rege",
        label="Are Members Opting In to Overdraft Protection?",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        merges=_MERGES,
        appendix_ids=_APPENDIX_IDS,
        absorb_ids={"A11.2": "value"},
    )
