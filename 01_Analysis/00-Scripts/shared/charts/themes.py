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

from shared.charts_palette import section_color


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


def themed_chart(
    *,
    kind: str,
    data: pd.DataFrame,
    section_key: str,
    hero_series: str,
    x_series: str,
    volume_series: str | None = None,
    peer_median: float | None = None,
    your_value: float | None = None,
    overlays: list[dict] | None = None,
    peak_delta_annotation: bool = False,
    source: str,
    out_path: Path,
) -> Path:
    """Render a themed chart PNG.

    Only ``kind="rate_volume_combo"`` is implemented in the POC. Other kinds
    raise ``UnsupportedKind`` so callers can fall back to their existing
    matplotlib path.

    All arguments after ``kind`` are keyword-only — every call site reads as
    a labeled record. This is deliberate; the function will eventually accept
    8+ params and positional ordering would be a footgun.
    """
    if kind == "rate_volume_combo":
        out_path.parent.mkdir(parents=True, exist_ok=True)
        return _render_rate_volume_combo(
            data=data,
            section_key=section_key,
            hero_series=hero_series,
            volume_series=volume_series,
            x_series=x_series,
            peer_median=peer_median,
            your_value=your_value,
            overlays=overlays,
            peak_delta_annotation=peak_delta_annotation,
            source=source,
            out_path=out_path,
        )
    raise UnsupportedKind(f"themed_chart kind={kind!r} not implemented yet")


def _render_rate_volume_combo(
    *,
    data: pd.DataFrame,
    section_key: str,
    hero_series: str,
    volume_series: str | None,
    x_series: str,
    peer_median: float | None,
    your_value: float | None,  # noqa: ARG001 — reserved for future annotation
    overlays: list[dict] | None = None,
    peak_delta_annotation: bool = False,
    source: str,
    out_path: Path,
) -> Path:
    import plotly.graph_objects as go

    accent = section_color(section_key)
    x = data[x_series].tolist()
    rates_raw = data[hero_series].astype(float).tolist()
    rates_pct = [v * 100 for v in rates_raw]  # display as percent

    fig = go.Figure()

    if volume_series and volume_series in data.columns:
        fig.add_trace(
            go.Bar(
                x=x,
                y=data[volume_series].astype(float).tolist(),
                name="Volume",
                marker={"color": "#D9DEE3"},
                yaxis="y2",
                hovertemplate="%{y:,.0f}<extra>Volume</extra>",
                showlegend=False,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=rates_pct,
            name=hero_series,
            mode="lines+markers",
            line={"color": accent, "width": 3},
            marker={"size": 9, "color": accent},
            hovertemplate="%{y:.1f}%<extra>" + hero_series + "</extra>",
        )
    )

    if overlays:
        for overlay in overlays:
            o_name = overlay.get("name", "")
            o_color = overlay.get("color", "#888888")
            o_marker = overlay.get("marker_symbol", "circle")
            o_values_raw = overlay.get("values", [])
            # Convert decimals to percent points, preserving None as gaps.
            o_y = [None if v is None else float(v) * 100 for v in o_values_raw]
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=o_y,
                    name=o_name,
                    mode="lines+markers",
                    line={"color": o_color, "width": 2.5},
                    marker={"size": 9, "color": o_color, "symbol": o_marker},
                    connectgaps=False,
                    hovertemplate="%{y:.1f}%<extra>" + o_name + "</extra>",
                )
            )

    layout = base_layout()
    layout["yaxis"]["title"] = {"text": "Rate", "font": {"size": 11}}
    layout["yaxis"]["ticksuffix"] = "%"
    if volume_series and volume_series in data.columns:
        layout["yaxis2"] = {
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
            "rangemode": "tozero",
            "title": {"text": "Volume", "font": {"size": 11, "color": "#999"}},
            "tickfont": {"color": "#999"},
        }
    fig.update_layout(**layout)

    if peer_median is not None:
        fig.add_hline(
            y=peer_median * 100,
            line={"color": "#555555", "dash": "dash", "width": 1.5},
            annotation_text=f"Peer median {peer_median * 100:.0f}%",
            annotation_position="top left",
            annotation_font={"color": "#555555", "size": 10},
        )

    if peak_delta_annotation and len(rates_pct) >= 2:
        deltas = [rates_pct[i] - rates_pct[i - 1] for i in range(1, len(rates_pct))]
        if deltas:
            best_idx = max(range(len(deltas)), key=lambda i: deltas[i]) + 1
            fig.add_annotation(
                x=x[best_idx],
                y=rates_pct[best_idx],
                text=f"+{deltas[best_idx - 1]:.1f}pp",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowcolor=accent,
                ax=0,
                ay=-30,
                font={"size": 12, "color": accent, "family": "Arial Black, Arial, sans-serif"},
            )

    if source:
        fig.add_annotation(
            text=f"Source: {source}",
            xref="paper", yref="paper",
            x=0, y=-0.18,
            showarrow=False,
            font={"size": 9, "color": "#888"},
            align="left",
        )

    fig.write_image(str(out_path), scale=1)
    return out_path
