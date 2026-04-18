"""Smoke test for the Truth section module."""

from __future__ import annotations

from sections.truth import register
from sections._base import LAYOUT_CUSTOM, SectionSpec


def test_truth_registers_valid_spec():
    spec = register()
    assert isinstance(spec, SectionSpec)
    assert spec.key == "truth"
    assert spec.label == "The Truth"


def test_truth_owns_three_slides():
    spec = register()
    assert "TRUTH-1" in spec.layout_map
    assert "TRUTH-2" in spec.layout_map
    assert "DCTR-3" in spec.layout_map


def test_truth_absorbs_dctr_3_from_dctr():
    spec = register()
    assert spec.absorb_ids.get("DCTR-3") == "dctr"


def test_truth_new_slides_use_custom_layout():
    spec = register()
    for sid in ("TRUTH-1", "TRUTH-2"):
        layout_idx, _ = spec.layout_map[sid]
        assert layout_idx == LAYOUT_CUSTOM
