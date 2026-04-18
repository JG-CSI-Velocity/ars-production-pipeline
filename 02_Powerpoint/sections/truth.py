"""Truth section -- the reframe.

New slides: TRUTH-1 (executive reframe), TRUTH-2 (true debit penetration)
Absorbed slides: DCTR-3 (TTM DCTR narrative, from dctr section)

Leads the deck after Open. Establishes that the program has not failed
on demand -- customers are spending. The gap is alignment.

Placeholders used by this section live in 02_Powerpoint/placeholders.py:
  TRUTH-1: {{CLIENT_NAME}}, {{NOTEBOOK_PENETRATION}}
  TRUTH-2: {{NOTEBOOK_PENETRATION}}, {{PIPELINE_DCTR}}
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["truth"]

_LAYOUT_MAP = {
    "TRUTH-1": (LAYOUT_CUSTOM, "kpi_hero"),
    "TRUTH-2": (LAYOUT_CUSTOM, "screenshot_kpi"),
    "DCTR-3":  (LAYOUT_CUSTOM, "screenshot"),
}

_ABSORB_IDS = {"DCTR-3": "dctr"}


def register() -> SectionSpec:
    """Return the Truth section specification."""
    return SectionSpec(
        key="truth",
        label="The Truth",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        absorb_ids=_ABSORB_IDS,
    )
