"""ICS section -- Are ICS Accounts Performing?

Mirrors: 01_Analysis/00-Scripts/analytics/ (future)
Slide IDs: ICS-prefixed
"""

from __future__ import annotations

from ._base import SectionSpec

_PREFIXES = ["ics"]


def register() -> SectionSpec:
    """Return the ICS section specification."""
    return SectionSpec(
        key="ics",
        label="Are ICS Accounts Performing?",
        prefixes=_PREFIXES,
    )
