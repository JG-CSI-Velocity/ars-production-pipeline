"""Persona Bridge section -- one slide, three personas.

Introduces the 3 customer types (Non-User, Climber, Decliner) as a
3-card composite slide sized with placeholder counts. Sits between
Diagnosis and Opportunity to transition from "what's broken" to
"what's possible."

Placeholders used by this slide:
  {{NONUSER_COUNT}}, {{CLIMBER_COUNT}}, {{DECLINER_COUNT}}

slide_type is "persona_cards" -- a new type the deck_assembler renders
as three stacked cards side by side. If the assembler falls back to
"screenshot" because the type is unknown, the slide still builds.
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["bridge"]

_LAYOUT_MAP = {
    "BRIDGE-1": (LAYOUT_CUSTOM, "persona_cards"),
}


def register() -> SectionSpec:
    return SectionSpec(
        key="persona_bridge",
        label="Meet the Three Customer Types",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
    )
