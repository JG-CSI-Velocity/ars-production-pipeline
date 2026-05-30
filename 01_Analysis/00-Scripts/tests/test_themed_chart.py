"""Tests for shared/charts/themes.py (autonomous decks POC, design §B)."""
from __future__ import annotations

from pathlib import Path

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


def test_themed_chart_rate_volume_combo_writes_png(tmp_path: Path):
    df = pd.DataFrame(
        {
            "bucket": ["10-19", "20-29", "30-39", "40-49", "50-59", "60+"],
            "volume": [400, 1800, 2400, 2100, 1600, 700],
            "rate": [0.18, 0.36, 0.44, 0.41, 0.30, 0.21],
        }
    )
    out = tmp_path / "dctr_decade.png"
    written = themes.themed_chart(
        kind="rate_volume_combo",
        data=df,
        section_key="dctr",
        hero_series="rate",
        volume_series="volume",
        x_series="bucket",
        peer_median=0.34,
        your_value=0.42,
        source="dctr_1.decade",
        out_path=out,
    )
    assert written == out
    assert out.exists()
    assert out.stat().st_size > 0


def test_themed_chart_unknown_kind_raises():
    df = pd.DataFrame({"x": [0], "y": [0]})
    try:
        themes.themed_chart(
            kind="not_a_real_kind",
            data=df,
            section_key="dctr",
            hero_series="y",
            volume_series=None,
            x_series="x",
            peer_median=None,
            your_value=None,
            source="test",
            out_path=Path("/tmp/should_not_exist.png"),
        )
    except themes.UnsupportedKind:
        return
    raise AssertionError("Expected UnsupportedKind to be raised.")
