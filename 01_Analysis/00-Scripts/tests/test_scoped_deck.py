"""build_scoped_deck must produce a one-section deck (title + divider + that
section's slides only) in a modules/<id>/ subfolder, using the real template.
This is the deliverable for the per-module closed loop."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from pptx import Presentation  # noqa: E402

from ars_analysis.analytics.base import AnalysisResult  # noqa: E402
from ars_analysis.analytics.section_registry import get_section  # noqa: E402
from ars_analysis.output import deck_builder  # noqa: E402
from ars_analysis.pipeline.context import (  # noqa: E402
    ClientInfo,
    OutputPaths,
    PipelineContext,
)


def _png(path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar([0, 1, 2], [3, 1, 2])
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return path


def _ctx(tmp_path: Path, slides) -> PipelineContext:
    ctx = PipelineContext(
        client=ClientInfo(client_id="1776", client_name="CoastHills CU",
                          month="2026.06", assigned_csm="JamesG"),
        paths=OutputPaths.from_dir(tmp_path),
    )
    ctx.all_slides = slides
    return ctx


def test_scoped_txn_deck_contains_only_its_section(tmp_path):
    slides = [
        AnalysisResult(slide_id="TXN-MERCH-01", title="Top Merchants",
                       chart_path=_png(tmp_path / "m1.png"), slide_type="screenshot"),
        AnalysisResult(slide_id="TXN-MERCH-02", title="Merchant Concentration",
                       chart_path=_png(tmp_path / "m2.png"), slide_type="screenshot"),
        # A different section's slide must NOT appear in the merchant deck.
        AnalysisResult(slide_id="TXN-COMP-01", title="Competitor Detection",
                       chart_path=_png(tmp_path / "c1.png"), slide_type="screenshot"),
    ]
    ctx = _ctx(tmp_path, slides)
    section = get_section("txn.merchant")

    out = deck_builder.build_scoped_deck(ctx, section)

    assert out is not None and out.exists()
    # Written under modules/<id>/ with the module-scoped filename.
    assert out.parent.name == "txn_merchant"
    assert out.name == "1776_2026.06_txn_merchant_deck.pptx"
    # title + divider + 2 merchant slides == 4 (the competition slide excluded).
    prs = Presentation(str(out))
    assert len(prs.slides) == 4


def test_scoped_deck_none_when_section_absent(tmp_path):
    slides = [
        AnalysisResult(slide_id="TXN-MERCH-01", title="Top Merchants",
                       chart_path=_png(tmp_path / "m1.png"), slide_type="screenshot"),
    ]
    ctx = _ctx(tmp_path, slides)
    # No ICS_cohort slides present -> nothing to build.
    out = deck_builder.build_scoped_deck(ctx, get_section("txn.ICS_cohort"))
    assert out is None
