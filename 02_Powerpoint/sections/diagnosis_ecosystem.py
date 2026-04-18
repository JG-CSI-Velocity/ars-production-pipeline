"""Diagnosis / Ecosystem Gap section -- the Decliner evidence + leakage.

Absorbed slides:
  A9.1 (attrition): overall attrition rate
  A9.3 (attrition): open vs closed accounts
  A9.9 (attrition): debit retention effect (why it matters)
  A7.10a (dctr): branch ranking -- leakage signal

Frames the third diagnosis gap: customers are leaving or relocating
spend across the ecosystem. Maps to the Decliner persona.
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["diag-eco"]

_LAYOUT_MAP = {
    "A9.1":   (LAYOUT_CUSTOM, "kpi_hero"),
    "A9.3":   (LAYOUT_CUSTOM, "screenshot"),
    "A9.9":   (LAYOUT_CUSTOM, "screenshot"),
    "A7.10a": (LAYOUT_CUSTOM, "screenshot"),
}

_ABSORB_IDS = {
    "A9.1": "attrition",
    "A9.3": "attrition",
    "A9.9": "attrition",
    "A7.10a": "dctr",
}


def register() -> SectionSpec:
    return SectionSpec(
        key="diagnosis_ecosystem",
        label="Ecosystem Gap",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        absorb_ids=_ABSORB_IDS,
    )
