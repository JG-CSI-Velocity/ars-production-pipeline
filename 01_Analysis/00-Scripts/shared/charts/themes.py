"""Plotly-themed chart engine.

A single ``themed_chart()`` function over a base Plotly layout that encodes
SLIDE_DESIGN.md §5–6 defaults: Arial 11pt, hero series in section accent,
peer median annotated, source line baked in, origin at zero.

POC scope: ``kind="rate_volume_combo"`` only. The dispatcher raises
``UnsupportedKind`` for everything else, so callers can fall back to their
existing matplotlib path (and the meta JSON can record `chart_engine:
matplotlib_fallback` — landed in the long-tail plan).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ars_analysis.shared.charts_palette import section_color, COLORS  # noqa: F401  (alias kept for downstream)


class UnsupportedKind(ValueError):
    """Raised by ``themed_chart`` when ``kind`` is not implemented yet."""


def base_layout() -> dict[str, Any]:
    """Return the canonical Plotly layout dict for the deck.

    Returned as a plain dict so tests can introspect keys without importing
    Plotly. ``themed_chart()`` passes this directly to ``fig.update_layout``.
    """
    return {
        "font": {"family": "Arial, Helvetica, sans-serif", "size": 11, "color": "#1E3D59"},
        "paper_bgcolor": "white",
        "plot_bgcolor": "white",
        "margin": {"l": 60, "r": 40, "t": 60, "b": 60},
        "showlegend": True,
        "legend": {"orientation": "h", "yanchor": "bottom", "y": -0.25, "x": 0.5, "xanchor": "center"},
        "xaxis": {
            "showgrid": False,
            "linecolor": "#BFC9D1",
            "ticks": "outside",
            "title": {"text": "", "font": {"size": 11}},
        },
        "yaxis": {
            "rangemode": "tozero",
            "showgrid": True,
            "gridcolor": "#EFF2F5",
            "zeroline": True,
            "zerolinecolor": "#BFC9D1",
            "title": {"text": "", "font": {"size": 11}},
        },
        "width": 1500,
        "height": 900,
    }
