"""Pipeline execution context — typed replacement for raw ctx dict."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from shared.config import PlatformConfig
from shared.types import AnalysisResult


@dataclass
class PipelineContext:
    """Carries all state through a pipeline run.

    Replaces the 45+ key raw dict from ars_analysis-jupyter.
    Mutable during execution; populated incrementally by pipeline steps.
    """

    # --- Client identity ---
    client_name: str = ""
    client_id: str = ""
    fi_name: str = ""
    csm: str = ""
    analysis_date: date = field(default_factory=date.today)

    # --- Input files ---
    input_files: dict[str, Path] = field(default_factory=dict)

    # --- Output paths ---
    output_dir: Path = Path("output")
    chart_dir: Path = Path("output/charts")
    excel_path: Path | None = None
    pptx_path: Path | None = None

    # --- Config ---
    config: PlatformConfig | None = None
    client_config: dict[str, Any] = field(default_factory=dict)

    # --- Data ---
    data: pd.DataFrame | None = None
    data_original: pd.DataFrame | None = None
    subsets: dict[str, pd.DataFrame] = field(default_factory=dict)

    # --- Time range ---
    start_date: pd.Timestamp | None = None
    end_date: pd.Timestamp | None = None
    last_12_months: list[str] = field(default_factory=list)

    # --- L12M window (set once, used everywhere) ---
    # If analysis_date is April 2026, L12M = Apr 2025 through Mar 2026
    # l12m_start = first day of month 12 months before analysis_date
    # l12m_end = last day of month before analysis_date
    l12m_start: pd.Timestamp | None = None
    l12m_end: pd.Timestamp | None = None

    def compute_l12m_window(self) -> None:
        """Set l12m_start and l12m_end from analysis_date. Call once at pipeline start."""
        ref = pd.Timestamp(self.analysis_date)
        # First day of current month
        first_of_month = ref.replace(day=1)
        # L12M end = last day of previous month
        self.l12m_end = first_of_month - pd.Timedelta(days=1)
        # L12M start = first day, 12 months back
        self.l12m_start = (first_of_month - pd.DateOffset(months=12))

    def in_l12m(self, dt_series: pd.Series) -> pd.Series:
        """Boolean mask: True for dates within the L12M window."""
        if self.l12m_start is None:
            self.compute_l12m_window()
        return (dt_series >= self.l12m_start) & (dt_series <= self.l12m_end)

    # --- Results ---
    results: dict[str, AnalysisResult] = field(default_factory=dict)
    all_slides: list[dict[str, Any]] = field(default_factory=list)
    export_log: list[dict[str, str]] = field(default_factory=list)

    # --- Progress ---
    progress_callback: Callable[[str], None] | None = None
