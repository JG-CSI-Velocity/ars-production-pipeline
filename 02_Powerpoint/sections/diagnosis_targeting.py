"""Diagnosis / Targeting Gap section -- the Climber evidence.

Absorbed slides from mailer:
  A14.2: responder profile
  A15.3: lift attribution
  A16.1: responder spend trajectory

Shows: mailers reach people who will respond, but response doesn't
translate into sustained wallet share. Maps to the Climber persona.
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["diag-tgt"]

_LAYOUT_MAP = {
    "A14.2": (LAYOUT_CUSTOM, "screenshot"),
    "A15.3": (LAYOUT_CUSTOM, "screenshot"),
    "A16.1": (LAYOUT_CUSTOM, "screenshot"),
}

_ABSORB_IDS = {
    "A14.2": "mailer",
    "A15.3": "mailer",
    "A16.1": "mailer",
}


def register() -> SectionSpec:
    return SectionSpec(
        key="diagnosis_targeting",
        label="Targeting Gap",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        absorb_ids=_ABSORB_IDS,
    )
