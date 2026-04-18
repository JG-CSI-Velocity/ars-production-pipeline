"""Smoke test for the Diagnosis: Ecosystem Gap section module."""

from __future__ import annotations

from sections.diagnosis_ecosystem import register
from sections._base import SectionSpec


def test_ecosystem_registers_valid_spec():
    spec = register()
    assert isinstance(spec, SectionSpec)
    assert spec.key == "diagnosis_ecosystem"
    assert spec.label == "Ecosystem Gap"


def test_ecosystem_owns_attrition_and_branch_slides():
    spec = register()
    for sid in ("A9.1", "A9.3", "A9.9", "A7.10a"):
        assert sid in spec.layout_map


def test_ecosystem_absorbs_from_correct_sections():
    spec = register()
    assert spec.absorb_ids.get("A9.1") == "attrition"
    assert spec.absorb_ids.get("A9.3") == "attrition"
    assert spec.absorb_ids.get("A9.9") == "attrition"
    assert spec.absorb_ids.get("A7.10a") == "dctr"
