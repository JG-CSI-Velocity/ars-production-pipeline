"""One synthetic AnalysisResultLike per canonical section (9 total).

Used for the smoke test to verify every section renders.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from PIL import Image

from html_review.tests.fixtures.tiny_deck import AnalysisResultLike


SECTIONS = [
    ("overview",   "Portfolio overview: 62% penetration, up from 58%."),
    ("dctr",       "DCTR reached 72% across the portfolio."),
    ("rege",       "Reg E opt-in rose 6 points after Q3 messaging."),
    ("attrition",  "Attrition declined 8% after re-engagement."),
    ("value",      "Top-value segment grew 11% YoY."),
    ("mailer",     "ARS campaign drove 14% incremental response."),
    ("transaction","Signature mix increased 4 points, led by grocery."),
    ("ics",        "ICS channel acquired 247 new accounts at $38 CAC."),
    ("insights",   "Three priorities: ICS expansion, Reg E, campaign cadence."),
]


def representative(tmp_path: Path) -> list[AnalysisResultLike]:
    png_path = tmp_path / "chart.png"
    Image.new("RGB", (1800, 900), (27, 54, 93)).save(png_path)
    out = []
    for section, title in SECTIONS:
        out.append(AnalysisResultLike(
            slide_id=f"{section}_01",
            title=title,
            section=section,
            chart_path=png_path,
            excel_data={"Detail": pd.DataFrame({"metric": ["x"], "value": [1]})},
            notes=f"Representative analysis for the {section} section.",
        ))
    return out
