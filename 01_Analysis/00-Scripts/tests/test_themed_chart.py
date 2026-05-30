"""Tests for shared/charts/themes.py (autonomous decks POC, design §B)."""
from __future__ import annotations

import pandas as pd

from ars_analysis.shared.charts import themes


def test_base_layout_has_expected_font_family():
    layout = themes.base_layout()
    assert layout["font"]["family"].lower().startswith("arial")


def test_base_layout_origin_is_zero():
    layout = themes.base_layout()
    # Y axis must start at zero by default — SLIDE_DESIGN.md §6.
    assert layout["yaxis"]["rangemode"] == "tozero"


def test_base_layout_no_default_axis_titles():
    layout = themes.base_layout()
    assert (layout["xaxis"]["title"]["text"] or "") == ""
    assert (layout["yaxis"]["title"]["text"] or "") == ""
