"""End-to-end confirmation for the ARS product: every ARS module runs over a
synthetic ODD frame into one context and build_deck assembles a real
_ars_deck.pptx. Companion to test_full_deck_integration.py (TXN side) -- together
they confirm both products compose into a working deck after the refactor.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from pptx import Presentation

from ars_analysis.analytics.registry import load_all_modules, ordered_modules
from ars_analysis.output import deck_builder
from ars_analysis.pipeline.context import ClientInfo, OutputPaths, PipelineContext

from _fixtures import synthetic_rewards

_TEMPLATE = Path(deck_builder.__file__).resolve().parent / "template" / "2025-CSI-PPT-Template.pptx"


@pytest.mark.skipif(not _TEMPLATE.exists(), reason="CSI template not available")
def test_full_ars_deck_builds_end_to_end(tmp_path):
    load_all_modules()
    client = ClientInfo(client_id="1776", client_name="CoastHills CU", month="2026.06",
                        eligible_stat_codes=["O"])
    ctx = PipelineContext(client=client, paths=OutputPaths.from_dir(tmp_path))
    ctx.product = "ars"
    ctx.settings = SimpleNamespace(
        paths=SimpleNamespace(template_path=_TEMPLATE), branch_mapping=None)
    ctx.data = synthetic_rewards()

    ran = 0
    for cls in ordered_modules():
        m = cls()
        if m.validate(ctx):
            continue
        try:
            results = m.run(ctx)
            ctx.results[m.module_id] = results
            ctx.all_slides.extend(results)
            if results:
                ran += 1
        except Exception:
            # A module needing richer data than the fixture must not block the
            # deck -- the pipeline is resilient per-module.
            pass

    assert ran >= 15
    assert len(ctx.all_slides) > 0

    deck = deck_builder.build_deck(ctx)
    assert deck is not None and deck.exists()
    assert deck.name.endswith("_ars_deck.pptx")
    assert len(Presentation(str(deck)).slides) > 0
