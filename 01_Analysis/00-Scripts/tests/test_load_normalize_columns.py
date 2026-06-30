"""Loader column-normalization regression tests (#232).

A formatted/placed-as-is ODD can carry numeric column headers (e.g. a month
labeled 202406). When a required column is also missing, the loader's
"Available columns" diagnostic used to sort a mix of str + int headers and
crash with `TypeError: '<' not supported between 'str' and 'int'`, masking the
real, actionable "missing required columns" error. These tests pin the
behavior: the loader must raise a clear DataError, never the TypeError.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from openpyxl import Workbook

from ars_analysis.exceptions import DataError
from ars_analysis.pipeline.steps import load as L

# Canonical required columns the loader validates.
REQUIRED = ["Stat Code", "Product Code", "Date Opened", "Avg Bal"]


def _write_xlsx(path, headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(list(headers))  # header cell type follows the Python value type
    for row in rows:
        ws.append(list(row))
    wb.save(path)
    return path


def _ctx():
    return SimpleNamespace(
        client=SimpleNamespace(data_start_date=None), data=None, data_original=None
    )


def test_missing_required_column_with_numeric_headers_raises_dataerror(tmp_path):
    """Missing required col + numeric headers -> clear DataError, not TypeError (#232)."""
    L.odd_cache_clear()
    path = _write_xlsx(
        tmp_path / "mixed.xlsx",
        ["Stat Code", "Product Code", "Date Opened", 202406, 202407],  # no Avg Bal
        [["100", "DDA", "2022-01-01", 1, 2]],
    )
    with pytest.raises(DataError) as exc:
        L.step_load_file(_ctx(), path)
    assert "Avg Bal" in str(exc.value)


def test_numeric_headers_alone_load_fine(tmp_path):
    """Numeric headers are harmless when all required columns are present."""
    L.odd_cache_clear()
    path = _write_xlsx(
        tmp_path / "ok.xlsx",
        REQUIRED + [202406, 202407],
        [["100", "DDA", "2022-01-01", "50.0", 1, 2]],
    )
    ctx = _ctx()
    L.step_load_file(ctx, path)
    assert len(ctx.data) == 1
    assert len(ctx.data.columns) == 6
