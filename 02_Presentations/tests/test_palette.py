"""Tests for style.palette -- CSI color constants and helpers."""

from pptx.dml.color import RGBColor

from style.palette import (
    AMBER,
    CORAL,
    GRAY,
    NAVY,
    SLATE,
    TEAL,
    WHITE,
)


def test_named_colors_match_slide_mapping_hex():
    assert NAVY == RGBColor(0x1B, 0x36, 0x5D)
    assert TEAL == RGBColor(0x0D, 0x94, 0x88)
    assert CORAL == RGBColor(0xE7, 0x4C, 0x3C)
    assert AMBER == RGBColor(0xF3, 0x9C, 0x12)
    assert GRAY == RGBColor(0x95, 0xA5, 0xA6)
    assert SLATE == RGBColor(0x6B, 0x72, 0x80)
    assert WHITE == RGBColor(0xFF, 0xFF, 0xFF)


from style.palette import is_palette_color, nearest_palette


def test_is_palette_color_true_for_exact_match():
    assert is_palette_color(RGBColor(0x1B, 0x36, 0x5D)) is True


def test_is_palette_color_false_for_off_palette():
    assert is_palette_color(RGBColor(0xFF, 0x00, 0xFF)) is False


def test_nearest_palette_snaps_near_coral_to_coral():
    # Off by 2 in each channel -- distance = sqrt(12) ~= 3.46, well within threshold 5.0
    nearby_coral = RGBColor(0xE5, 0x4E, 0x3E)
    assert nearest_palette(nearby_coral) == CORAL


def test_nearest_palette_returns_none_when_nothing_close_enough():
    # Bright magenta is far from all palette colors
    magenta = RGBColor(0xFF, 0x00, 0xFF)
    assert nearest_palette(magenta) is None


def test_nearest_palette_respects_threshold():
    # Exactly 5 away -- within threshold of 5.0
    just_inside = RGBColor(0x1E, 0x39, 0x5D)  # navy with (+3,+3,0) -> d=~4.24
    assert nearest_palette(just_inside) == NAVY


from style.palette import focal


def test_focal_returns_named_color_with_muted_set():
    result = focal("teal")
    assert result["focal"] == TEAL
    assert NAVY in result["muted"]
    assert TEAL not in result["muted"]  # focal excluded from muted


def test_focal_raises_for_unknown_name():
    import pytest
    with pytest.raises(KeyError):
        focal("chartreuse")
