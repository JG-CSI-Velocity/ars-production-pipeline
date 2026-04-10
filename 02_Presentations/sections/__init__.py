"""Deck sections -- SCR Narrative Arc ordering.

Each section mirrors an analytics module in 01_Analysis/00-Scripts/analytics/.
The SECTION_REGISTRY list defines the order sections appear in the deck.
To add a new section: create a module, import it, add to the list.
"""

from __future__ import annotations

from ._base import SectionSpec, default_consolidate
from .overview import register as _overview
from .dctr import register as _dctr
from .rege import register as _rege
from .attrition import register as _attrition
from .mailer import register as _mailer
from .transaction import register as _transaction
from .ics import register as _ics
from .value import register as _value
from .insights import register as _insights

# SCR Narrative Arc -- order matters
SECTION_REGISTRY: list[SectionSpec] = [
    _overview(),       # Situation
    _dctr(),           # Complication
    _rege(),           # Complication
    _attrition(),      # Complication
    _mailer(),         # Resolution
    _transaction(),    # Resolution (spending patterns)
    _ics(),            # Resolution (ICS performance)
    _value(),          # Resolution (revenue impact -- slides absorbed by dctr/rege)
    _insights(),       # Call to action
]

__all__ = ["SECTION_REGISTRY", "SectionSpec", "default_consolidate"]
