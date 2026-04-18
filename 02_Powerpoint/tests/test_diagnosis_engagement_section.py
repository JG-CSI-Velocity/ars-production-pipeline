"""Smoke test for the Diagnosis: Engagement Gap section module."""

from __future__ import annotations

from sections.diagnosis_engagement import register
from sections._base import SectionSpec


def test_engagement_registers_valid_spec():
    spec = register()
    assert isinstance(spec, SectionSpec)
    assert spec.key == "diagnosis_engagement"
    assert spec.label == "Engagement Gap"


def test_engagement_owns_age_and_dormant_slides():
    spec = register()
    for sid in ("A7.11", "A7.12", "A20.1"):
        assert sid in spec.layout_map, f"{sid} missing from engagement section"


def test_engagement_absorbs_from_other_sections():
    spec = register()
    assert spec.absorb_ids.get("A7.11") == "dctr"
    assert spec.absorb_ids.get("A7.12") == "dctr"
    assert spec.absorb_ids.get("A20.1") == "insights"
