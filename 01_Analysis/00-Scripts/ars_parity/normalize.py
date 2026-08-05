"""Canonical normalization of run artifacts for stable comparison.

Rules:
- Tables become {"columns": [...], "rows": [[...]]} with rows sorted by the
  string form of the full row tuple (stable regardless of upstream ordering).
- NaN/None unify to None; numpy scalars become python scalars; timestamps
  become ISO strings. Floats keep full precision -- tolerance is applied at
  compare time, never at capture time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def _cell(v: Any) -> Any:
    import numpy as np

    if v is None:
        return None
    if isinstance(v, float) and v != v:  # NaN
        return None
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        f = float(v)
        return None if f != f else f
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, (pd.Timestamp,)):
        return v.isoformat()
    if isinstance(v, np.datetime64):
        return pd.Timestamp(v).isoformat()
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def normalize_df(df: pd.DataFrame) -> dict[str, Any]:
    """Normalize a DataFrame to a stable, JSON-safe table dict."""
    columns = [str(c) for c in df.columns]
    rows = [[_cell(v) for v in row] for row in df.itertuples(index=False, name=None)]
    rows.sort(key=lambda r: [str(x) for x in r])
    return {"columns": columns, "rows": rows}


def normalize_workbook(xlsx_path: Path | str) -> dict[str, dict[str, Any]]:
    """Read every sheet of a legacy ``*_analysis.xlsx`` into normalized tables.

    Sheet names are the legacy ``{slide_id}_{sheet}`` truncated to 31 chars;
    the summary sheet (first, no slide_id prefix pattern enforced) is included
    as-is -- comparison filters decide what to use.
    """
    xlsx_path = Path(xlsx_path)
    sheets = pd.read_excel(xlsx_path, sheet_name=None, engine="openpyxl")
    return {name: normalize_df(df) for name, df in sheets.items()}
