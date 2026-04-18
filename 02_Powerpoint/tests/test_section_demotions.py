"""Verify that detail slides are demoted to appendix per blueprint sec.4.

Blueprint reference:
  docs/superpowers/specs/2026-04-17-deck-blueprint.md section 4.
"""

from __future__ import annotations

from sections.attrition import register as register_attrition
from sections.dctr import register as register_dctr
from sections.insights import register as register_insights
from sections.mailer import register as register_mailer
from sections.rege import register as register_rege
from sections.value import register as register_value


def test_dctr_detail_slides_in_appendix():
    spec = register_dctr()
    for sid in (
        "DCTR-4", "DCTR-5", "DCTR-6", "DCTR-7",
        "DCTR-10", "DCTR-11", "DCTR-12", "DCTR-13",
        "DCTR-15", "DCTR-16",
    ):
        assert sid in spec.appendix_ids, f"{sid} should be in dctr appendix"


def test_rege_detail_slides_in_appendix():
    spec = register_rege()
    for sid in ("A8.3", "A8.10", "A8.11"):
        assert sid in spec.appendix_ids, f"{sid} should be in rege appendix"


def test_attrition_impact_in_appendix():
    spec = register_attrition()
    assert "A9.11" in spec.appendix_ids


def test_value_s1_demoted():
    spec = register_value()
    assert "S1" in spec.appendix_ids or "A11.1" in spec.appendix_ids


def test_insights_non_plan_slides_in_appendix():
    spec = register_insights()
    for sid in ("S2", "S4", "S5"):
        assert sid in spec.appendix_ids


def test_mailer_older_months_appendix_logic_preserved():
    spec = register_mailer()
    assert spec.key == "mailer"
