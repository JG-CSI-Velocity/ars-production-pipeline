"""Open section -- Title + 4-beat Agenda.

Mirrors: 01_Analysis/00-Scripts/ preamble (P01, P02)
Slide IDs: P01 (client title), P02 (new 4-beat agenda)

Owns the deck opener. P01 reuses the existing ARS title layout.
P02 replaces the legacy agenda placeholder with a 4-beat signpost
(Truth / Diagnosis / Opportunity / Plan).
"""

from __future__ import annotations

from ._base import LAYOUT_BLANK, LAYOUT_TITLE_ARS, SectionSpec

_PREFIXES = ["p01", "p02"]

_LAYOUT_MAP = {
    "P01": (LAYOUT_TITLE_ARS, "title"),
    "P02": (LAYOUT_BLANK, "agenda"),
}


def register() -> SectionSpec:
    """Return the Open section specification."""
    return SectionSpec(
        key="open",
        label="Open",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
    )
