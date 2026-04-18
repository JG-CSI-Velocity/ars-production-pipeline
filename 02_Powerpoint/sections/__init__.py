"""Deck sections -- Narrative Arc ordering.

Top of the registry is the main-deck narrative (Open -> Truth -> Diagnosis
-> Persona Bridge -> Opportunity -> Plan). Topic sections remain in the
registry below the narrative so absorbed slides route correctly and
demoted slides reach the appendix.
"""

from __future__ import annotations

from ._base import SectionSpec, default_consolidate

# Narrative sections (new)
from .open import register as _open
from .truth import register as _truth
from .diagnosis_engagement import register as _diagnosis_engagement
from .diagnosis_targeting import register as _diagnosis_targeting
from .diagnosis_ecosystem import register as _diagnosis_ecosystem
from .persona_bridge import register as _persona_bridge
from .opportunity import register as _opportunity
from .plan import register as _plan

# Topic sections (existing -- now provide absorbed slides + appendix content)
from .overview import register as _overview
from .dctr import register as _dctr
from .rege import register as _rege
from .attrition import register as _attrition
from .mailer import register as _mailer
from .transaction import register as _transaction
from .ics import register as _ics
from .value import register as _value
from .insights import register as _insights

# Order matters -- narrative first, then topic sections as absorb donors.
SECTION_REGISTRY: list[SectionSpec] = [
    # --- Main-deck narrative ---
    _open(),
    _truth(),
    _diagnosis_engagement(),
    _diagnosis_targeting(),
    _diagnosis_ecosystem(),
    _persona_bridge(),
    _opportunity(),
    _plan(),

    # --- Topic sections (absorb donors / appendix providers) ---
    _overview(),
    _dctr(),
    _rege(),
    _attrition(),
    _mailer(),
    _transaction(),
    _ics(),
    _value(),
    _insights(),
]

__all__ = ["SECTION_REGISTRY", "SectionSpec", "default_consolidate"]
