"""Smoke test for the Diagnosis: Targeting Gap section module."""

from __future__ import annotations

from sections.diagnosis_targeting import register
from sections._base import SectionSpec


def test_targeting_registers_valid_spec():
    spec = register()
    assert isinstance(spec, SectionSpec)
    assert spec.key == "diagnosis_targeting"
    assert spec.label == "Targeting Gap"


def test_targeting_owns_mailer_slides():
    spec = register()
    for sid in ("A14.2", "A15.3", "A16.1"):
        assert sid in spec.layout_map


def test_targeting_absorbs_from_mailer():
    spec = register()
    for sid in ("A14.2", "A15.3", "A16.1"):
        assert spec.absorb_ids.get(sid) == "mailer"
