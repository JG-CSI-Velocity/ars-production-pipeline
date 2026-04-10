"""Overview section -- How Big Is This Program?

Mirrors: 01_Analysis/00-Scripts/analytics/overview/
Slide IDs: A1, A1b, A3
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["a1", "a3"]

_LAYOUT_MAP = {
    "A1": (LAYOUT_CUSTOM, "screenshot"),
}

_SKIP_IDS = {"A1", "A1b", "A3"}


def register() -> SectionSpec:
    """Return the Overview section specification."""
    return SectionSpec(
        key="overview",
        label="How Big Is This Program?",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        skip_ids=_SKIP_IDS,
    )
