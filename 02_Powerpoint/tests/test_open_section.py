"""Smoke test for the Open section module."""

from __future__ import annotations

from sections.open import register
from sections._base import LAYOUT_BLANK, LAYOUT_TITLE_ARS, SectionSpec


def test_open_registers_valid_spec():
    spec = register()
    assert isinstance(spec, SectionSpec)
    assert spec.key == "open"
    assert spec.label == "Open"


def test_open_owns_p01_and_p02():
    spec = register()
    assert "P01" in spec.layout_map
    assert "P02" in spec.layout_map


def test_open_p01_uses_ars_title_layout():
    spec = register()
    layout_idx, slide_type = spec.layout_map["P01"]
    assert layout_idx == LAYOUT_TITLE_ARS
    assert slide_type == "title"


def test_open_p02_uses_blank_layout():
    spec = register()
    layout_idx, slide_type = spec.layout_map["P02"]
    assert layout_idx == LAYOUT_BLANK
    assert slide_type == "agenda"
