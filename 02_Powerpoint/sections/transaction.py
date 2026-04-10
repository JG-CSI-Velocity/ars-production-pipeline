"""Transaction section -- What Do Spending Patterns Reveal?

Mirrors: 01_Analysis/00-Scripts/analytics/ (future)
Slide IDs: M1-M26, B1-B8
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = [
    "txn", "m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8", "m9",
    "m10", "m11", "m12", "m13", "m14", "m15", "m16", "m17", "m18",
    "m19", "m20", "m21", "m22", "m23", "m24", "m25", "m26",
    "b1", "b2", "b3", "b4", "b5", "b8",
]


def register() -> SectionSpec:
    """Return the Transaction section specification."""
    return SectionSpec(
        key="transaction",
        label="What Do Spending Patterns Reveal?",
        prefixes=_PREFIXES,
    )
