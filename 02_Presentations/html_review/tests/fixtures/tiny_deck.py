"""Synthetic AnalysisResult stand-ins for html_review tests.

The real AnalysisResult lives in 01_Analysis/00-Scripts/analytics/base.py
but that path can't be imported (digit prefix). builder.py uses structural
typing -- it reads attributes, doesn't require a specific class. These
stubs carry the same attribute shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass
class AnalysisResultLike:
    """Walks like an AnalysisResult. Used by tests."""

    slide_id: str
    title: str
    section: str                                       # 'overview', 'attrition', etc.
    chart_path: Path | None = None
    excel_data: dict[str, pd.DataFrame] | None = None
    notes: str = ""
    kpis: dict[str, str] | None = None
    bullets: list[str] = field(default_factory=list)
    success: bool = True


def tiny_deck(tmp_path: Path) -> list[AnalysisResultLike]:
    """3 synthetic analyses covering the rendering variants.

    Writes a real PNG to tmp_path so chart_path resolves to a real file.
    """
    from PIL import Image

    png_path = tmp_path / "chart.png"
    Image.new("RGB", (1800, 900), (13, 148, 136)).save(png_path)

    return [
        # 1. PNG + notes only
        AnalysisResultLike(
            slide_id="attrition_01",
            title="Attrition declined 8% after the Q4 re-engagement campaign.",
            section="attrition",
            chart_path=png_path,
            notes="Campaign ROI: $128 incremental debit spend per responder.",
        ),
        # 2. PNG + single-sheet excel_data
        AnalysisResultLike(
            slide_id="attrition_02",
            title="Spend velocity flagged 30% of at-risk accounts.",
            section="attrition",
            chart_path=png_path,
            excel_data={
                "Cohort": pd.DataFrame(
                    {"segment": ["New", "Tenured"], "flagged_pct": [22.0, 38.5]}
                )
            },
        ),
        # 3. PNG + multi-sheet excel_data (tests the sheet <select>)
        AnalysisResultLike(
            slide_id="campaign_03",
            title="Cohort lift varied by tenure segment.",
            section="mailer",
            chart_path=png_path,
            excel_data={
                "Lift": pd.DataFrame({"seg": ["NU", "TH-10"], "lift": [12.1, 8.4]}),
                "Sample sizes": pd.DataFrame({"seg": ["NU", "TH-10"], "n": [240, 180]}),
            },
            notes="Three-month pre/post window.",
        ),
    ]
