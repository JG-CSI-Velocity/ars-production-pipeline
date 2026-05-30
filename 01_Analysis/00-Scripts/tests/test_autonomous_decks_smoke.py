"""POC smoke test for autonomous decks (design step 5 / commit afdce7a).

Exercises the three new paths on synthetic data shaped like client 1615:
  1. Branching catalog title selection (dctr.activation_baseline -> populated sentence)
  2. Themed-chart PNG render (rate_volume_combo)
  3. Structural cover slide (lead-finding subline)

Does NOT touch PowerPoint output - that's the full E2E in the long-tail plan.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def fake_1615_ctx(tmp_path):
    """Synthetic context shaped like a real client run.

    Numbers are fake. Field names + path shapes mirror real `ctx.results`
    so the same module paths the analytics modules use also work here.
    """
    paths = types.SimpleNamespace(charts_dir=tmp_path, base_dir=tmp_path.parent)
    client = types.SimpleNamespace(client_name="Guardians Credit Union", client_id="1615", month="2026.05")
    results = {
        "dctr_1": {
            "rate": 0.42,
            "eligible_count": 12400,
            "decade": pd.DataFrame({
                "Decade":         ["10-19", "20-29", "30-39", "40-49", "50-59", "60+"],
                "DCTR %":         [0.18,    0.36,    0.44,    0.41,    0.30,    0.21],
                "Total Accounts": [400,     1800,    2400,    2100,    1600,    700],
            }),
        },
        "dctr_4": {"decade": pd.DataFrame(columns=["Decade", "DCTR %", "Total Accounts"])},
        "dctr_5": {"decade": pd.DataFrame(columns=["Decade", "DCTR %", "Total Accounts"])},
        "value_summary": {
            "lead_finding": "DCTR gap to peer is the largest revenue lever this cycle.",
        },
    }
    return types.SimpleNamespace(paths=paths, client=client, results=results, settings=None)


def test_branching_catalog_picks_a_dctr_variant(fake_1615_ctx):
    """Path 1: branching catalog resolves dctr.activation_baseline to a populated sentence."""
    from ars_analysis.output.action_title_populator import ActionTitlePopulator
    from ars_analysis.output import template_catalog

    # Force a fresh cache so this test sees the on-disk catalog.
    template_catalog.CatalogCache._families = None
    ActionTitlePopulator._catalog = None

    title = ActionTitlePopulator.populate(
        template_id="dctr.activation_baseline",
        ctx_results=fake_1615_ctx.results,
        ctx=fake_1615_ctx,
        fallback_title="default",
    )
    assert "{" not in title
    assert title != "default"
    assert "42%" in title  # rate=0.42 formatted as pct
    assert "12,400" in title  # eligible_count=12400 formatted as int


def test_themed_chart_renders_decade_trend_png(fake_1615_ctx):
    """Path 2: themed_chart produces a PNG for the rate_volume_combo shape."""
    from ars_analysis.analytics.dctr.trends import DCTRTrends
    out = DCTRTrends()._decade_trend(fake_1615_ctx)
    assert len(out) == 1
    assert out[0].chart_path is not None
    assert Path(out[0].chart_path).exists()
    assert Path(out[0].chart_path).stat().st_size > 0


def test_structural_cover_uses_lead_finding(fake_1615_ctx):
    """Path 3: structural cover slide picks up lead-finding subline."""
    from ars_analysis.output.deck_builder import _build_preamble_slides
    preamble = _build_preamble_slides(
        client_name=fake_1615_ctx.client.client_name,
        month=fake_1615_ctx.client.month,
        product_mode="ars",
        ctx_results=fake_1615_ctx.results,
    )
    assert "DCTR gap to peer" in preamble[0].title
    assert "Guardians Credit Union" in preamble[0].title
    # 13-slide ARS preamble must still have 13 slides.
    assert len(preamble) == 13
    # Sanity-check P02 didn't drift during the cover wire-up.
    assert preamble[1].title == "Agenda"


def test_smoke_all_three_paths_together(fake_1615_ctx):
    """All three paths exercise without raising. The actual content checks
    are above; this is the wires-connect check."""
    from ars_analysis.output.action_title_populator import ActionTitlePopulator
    from ars_analysis.output import template_catalog
    from ars_analysis.output.deck_builder import _build_preamble_slides
    from ars_analysis.analytics.dctr.trends import DCTRTrends

    template_catalog.CatalogCache._families = None
    ActionTitlePopulator._catalog = None

    # Title
    title = ActionTitlePopulator.populate(
        "dctr.activation_baseline", fake_1615_ctx.results, ctx=fake_1615_ctx,
        fallback_title="default",
    )
    # Chart
    chart_result = DCTRTrends()._decade_trend(fake_1615_ctx)
    # Cover
    preamble = _build_preamble_slides(
        fake_1615_ctx.client.client_name, fake_1615_ctx.client.month,
        product_mode="ars", ctx_results=fake_1615_ctx.results,
    )

    assert title and chart_result and preamble
    assert "{" not in title
    assert chart_result[0].chart_path and Path(chart_result[0].chart_path).exists()
    assert preamble[0].title
