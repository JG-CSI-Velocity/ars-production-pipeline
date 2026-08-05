"""The ONE slide/result contract.

Supersedes both legacy result types:
- ``analytics/base.py::AnalysisResult`` (the deck-facing shape: slide_id,
  excel_data, kpis, bullets, denominator stamps, layout hints) -- kept
  field-for-field so the deck compiler consumes old and new results alike.
- ``shared/types.py::AnalysisResult`` (the runner-boundary shape) -- absorbed
  via :func:`from_legacy_result`.

New in v3: ``chart`` may carry a declarative ChartSpec (ars_engine.charts.spec)
instead of only a rendered PNG path; the chart renderer fills ``chart_path``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class SlideSpec:
    """Standard output container for one analysis -> one (candidate) slide."""

    slide_id: str
    title: str
    chart_path: Path | None = None
    excel_data: dict[str, pd.DataFrame] | None = None
    notes: str = ""
    success: bool = True
    error: str = ""
    layout_index: int = 8  # LAYOUT_CUSTOM (2025-CSI-PPT-Template)
    slide_type: str = "screenshot"
    kpis: dict[str, str] | None = None
    extra_charts: list[Path] | None = None
    bullets: list[str] | None = None
    # Hex color string e.g. "#1B365D"; overrides layout default title color.
    title_color: str | None = None
    # Denominator label per the 4-layer framework: one of
    # "Eligible", "Eligible Personal", "Eligible Business", "Open".
    # Empty string means "not a rate" (chart, dollar figure, etc.).
    # Sections MUST stamp this on any result that surfaces a rate/ratio/share;
    # primitives.denominators.rate() stamps it automatically.
    denominator_label: str = ""
    denominator_n: int = 0
    # Computed findings the deck compiler's title/callout/spec inputs resolve
    # against (replaces legacy metadata["insights"]). Keys are section-declared
    # and validated by spec_lint against results_schema.json.
    insights: dict[str, Any] = field(default_factory=dict)
    # v3: declarative chart (ars_engine.charts.spec.ChartSpec). When set, the
    # chart renderer produces chart_path from it (content-hash cached).
    chart: object = None

    @property
    def df(self) -> pd.DataFrame:
        """Convenience: the 'main' table, or empty if missing."""
        return (self.excel_data or {}).get("main", pd.DataFrame())


def from_legacy_result(obj: Any) -> SlideSpec:
    """Adapt either legacy AnalysisResult shape to a SlideSpec.

    - ``analytics.base.AnalysisResult``: field names match SlideSpec directly.
    - ``shared.types.AnalysisResult``: name/data/charts/metadata shape.

    This is the migration bridge: while engine_flags route some sections to the
    legacy engine, the runner wraps their outputs here so the deck compiler
    sees exactly one type.
    """
    if isinstance(obj, SlideSpec):
        return obj

    # analytics/base.py shape -- has slide_id
    if hasattr(obj, "slide_id"):
        return SlideSpec(
            slide_id=obj.slide_id,
            title=obj.title,
            chart_path=getattr(obj, "chart_path", None),
            excel_data=getattr(obj, "excel_data", None),
            notes=getattr(obj, "notes", ""),
            success=getattr(obj, "success", True),
            error=getattr(obj, "error", ""),
            layout_index=getattr(obj, "layout_index", 8),
            slide_type=getattr(obj, "slide_type", "screenshot"),
            kpis=getattr(obj, "kpis", None),
            extra_charts=getattr(obj, "extra_charts", None),
            bullets=getattr(obj, "bullets", None),
            title_color=getattr(obj, "title_color", None),
            denominator_label=getattr(obj, "denominator_label", ""),
            denominator_n=getattr(obj, "denominator_n", 0),
        )

    # shared/types.py shape -- has name/data/metadata
    if hasattr(obj, "name"):
        meta = dict(getattr(obj, "metadata", {}) or {})
        charts = list(getattr(obj, "charts", []) or [])
        err = getattr(obj, "error", None)
        return SlideSpec(
            slide_id=meta.get("slide_id", obj.name),
            title=getattr(obj, "title", "") or obj.name,
            chart_path=charts[0] if charts else None,
            extra_charts=charts[1:] or None,
            excel_data=dict(getattr(obj, "data", {}) or {}) or None,
            notes=getattr(obj, "summary", ""),
            success=err is None,
            error=err or "",
            denominator_label=meta.get("denominator_label", ""),
            denominator_n=int(meta.get("denominator_n", 0) or 0),
            insights=meta.get("insights", {}) or {},
        )

    raise TypeError(f"Cannot adapt {type(obj).__name__} to SlideSpec")
