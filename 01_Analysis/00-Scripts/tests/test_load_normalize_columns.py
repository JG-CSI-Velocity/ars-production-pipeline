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


def test_title_banner_row_is_skipped(tmp_path):
    """A title/banner row above the headers must be skipped (#232, the 1800 case).

    1800's ODD opened with 'First American Bank - OD Data Dump' on row 1, so
    header=0 read the title and all four required columns looked missing.
    """
    L.odd_cache_clear()
    path = _write_xlsx(
        tmp_path / "title.xlsx",
        [1, "First American Bank - OD Data Dump", None, None, None],  # title row
        [
            REQUIRED + ["Branch"],                       # real header row
            ["100", "DDA", "2022-01-01", "50.0", "Main"],
            ["101", "SAV", "2023-05-05", "75.0", "West"],
        ],
    )
    ctx = _ctx()
    L.step_load_file(ctx, path)
    assert len(ctx.data) == 2
    assert list(ctx.data.columns[:4]) == REQUIRED


def test_header_row_zero_is_not_second_guessed(tmp_path):
    """A normal header-on-row-0 file must not be shifted."""
    L.odd_cache_clear()
    path = _write_xlsx(
        tmp_path / "row0.xlsx", REQUIRED, [["100", "DDA", "2022-01-01", "50.0"]]
    )
    ctx = _ctx()
    L.step_load_file(ctx, path)
    assert len(ctx.data) == 1


def test_numeric_headers_coerced_to_str(tmp_path):
    """Numeric column headers must load as str so module column-name string ops
    (c.endswith(...), 'Reg E' in c, regex) don't crash (#232: mailer.*, insights.*)."""
    L.odd_cache_clear()
    path = _write_xlsx(
        tmp_path / "numhdr.xlsx",
        REQUIRED + [202406, "Jan26 Reg E Code", "Jan26 Spend"],
        [["100", "DDA", "2022-01-01", "50.0", 7, "Y", 12.5]],
    )
    ctx = _ctx()
    L.step_load_file(ctx, path)
    assert all(isinstance(c, str) for c in ctx.data.columns)
    # The exact ops that killed insights.dormant / branch_scorecard must not raise.
    assert [c for c in ctx.data.columns if c.endswith(" Spend")] == ["Jan26 Spend"]
    assert [c for c in ctx.data.columns if "Reg E" in c and "Code" in c] == ["Jan26 Reg E Code"]


def test_required_columns_match_whitespace_and_case(tmp_path):
    """Headers drift: ' Stat Code', 'prod code', 'AVG BAL' must still match."""
    L.odd_cache_clear()
    path = _write_xlsx(
        tmp_path / "drift.xlsx",
        [" Stat Code", "prod code", "Date Opened ", "AVG BAL"],
        [["100", "DDA", "2022-01-01", "50.0"]],
    )
    ctx = _ctx()
    L.step_load_file(ctx, path)  # must not raise
    for canonical in REQUIRED:
        assert canonical in ctx.data.columns
