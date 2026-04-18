"""Diagnosis / Engagement Gap section -- the Non-User evidence.

Absorbed slides (all reused, no new slides):
  A7.11 (dctr): DCTR by account age -- who never activated
  A7.12 (dctr): DCTR by holder age -- generational pattern
  A20.1 (insights): dormant population sizing

Frames the first diagnosis gap: a large population has simply never
engaged with the card. Maps to the Non-User persona.
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["diag-eng"]

_LAYOUT_MAP = {
    "A7.11": (LAYOUT_CUSTOM, "screenshot"),
    "A7.12": (LAYOUT_CUSTOM, "screenshot"),
    "A20.1": (LAYOUT_CUSTOM, "screenshot"),
}

_ABSORB_IDS = {
    "A7.11": "dctr",
    "A7.12": "dctr",
    "A20.1": "insights",
}


def register() -> SectionSpec:
    return SectionSpec(
        key="diagnosis_engagement",
        label="Engagement Gap",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        absorb_ids=_ABSORB_IDS,
    )
