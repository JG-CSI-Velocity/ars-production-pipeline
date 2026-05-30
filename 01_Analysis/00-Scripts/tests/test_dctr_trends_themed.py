"""Verify analytics/dctr/trends._decade_trend can produce a themed PNG."""
from __future__ import annotations

import types
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def _ctx(tmp_path):
    """Build a minimal PipelineContext-shaped stub."""
    paths = types.SimpleNamespace(charts_dir=tmp_path, base_dir=tmp_path.parent)
    client = types.SimpleNamespace(client_name="Test Client", client_id="1615", month="2026.05")
    results = {
        "dctr_1": {"decade": pd.DataFrame({
            "Decade":         ["10-19", "20-29", "30-39", "40-49", "50-59", "60+"],
            "DCTR %":         [0.18,    0.36,    0.44,    0.41,    0.30,    0.21],
            "Total Accounts": [400,     1800,    2400,    2100,    1600,    700],
        })},
        "dctr_4": {"decade": pd.DataFrame(columns=["Decade", "DCTR %", "Total Accounts"])},
        "dctr_5": {"decade": pd.DataFrame(columns=["Decade", "DCTR %", "Total Accounts"])},
    }
    return types.SimpleNamespace(paths=paths, client=client, results=results, settings=None)


def test_decade_trend_emits_png_via_themed_chart(_ctx, tmp_path):
    from ars_analysis.analytics.dctr.trends import DCTRTrends
    out = DCTRTrends()._decade_trend(_ctx)
    assert len(out) == 1
    result = out[0]
    assert result.slide_id == "A7.5"
    assert result.chart_path is not None
    assert Path(result.chart_path).exists()


def test_decade_trend_uses_themed_chart_not_fallback(_ctx, monkeypatch):
    """Regression net: the Plotly path is what produced the chart, not the
    matplotlib fallback. If themed_chart silently raises and we drop into
    matplotlib, this test fails loudly."""
    from ars_analysis.analytics.dctr.trends import DCTRTrends

    def _explode(*_a, **_kw):
        raise AssertionError("matplotlib fallback was called -- themed_chart silently failed")

    monkeypatch.setattr(DCTRTrends, "_decade_trend_matplotlib_fallback", _explode)
    results = DCTRTrends()._decade_trend(_ctx)
    assert len(results) == 1
    assert results[0].chart_path is not None
    assert Path(results[0].chart_path).exists()
