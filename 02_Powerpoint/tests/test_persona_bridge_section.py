"""Smoke test for the Persona Bridge section module."""

from __future__ import annotations

from sections.persona_bridge import register
from sections._base import LAYOUT_CUSTOM, SectionSpec


def test_bridge_registers_valid_spec():
    spec = register()
    assert isinstance(spec, SectionSpec)
    assert spec.key == "persona_bridge"
    assert spec.label == "Meet the Three Customer Types"


def test_bridge_owns_single_slide():
    spec = register()
    assert list(spec.layout_map.keys()) == ["BRIDGE-1"]


def test_bridge_uses_custom_layout_and_persona_card_type():
    spec = register()
    layout_idx, slide_type = spec.layout_map["BRIDGE-1"]
    assert layout_idx == LAYOUT_CUSTOM
    assert slide_type == "persona_cards"
