"""Value section -- What Is the Revenue Impact?

Mirrors: 01_Analysis/00-Scripts/analytics/value/
Slide IDs: A11.1, A11.2

Note: A11.1 is absorbed by dctr, A11.2 by rege. This section exists
as the donor but produces no slides of its own in the main deck.
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["a10", "a11", "val"]

_LAYOUT_MAP = {
    "A11.1": (LAYOUT_CUSTOM, "screenshot"),
    "A11.2": (LAYOUT_CUSTOM, "screenshot"),
}


def register() -> SectionSpec:
    """Return the Value section specification."""
    return SectionSpec(
        key="value",
        label="What Is the Revenue Impact?",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
    )
