"""Regression tests for ODD column normalization/validation.

Covers the issue #232 crash: an ODD whose header row contains numeric cells
makes df.columns a mixed str/int Index. When a required column is also missing,
the "available columns" warning sorted that mixed Index and raised
"'<' not supported between instances of 'str' and 'int'", masking the real
"missing required columns" DataError.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ars_analysis.exceptions import DataError
from ars_analysis.pipeline.steps.load import _normalize_columns


def test_missing_column_with_numeric_headers_raises_dataerror():
    # "Avg Bal" (and its aliases) is absent; columns include numeric labels
    # so df.columns is a mixed str/int Index.
    df = pd.DataFrame(
        [["O", "182", "2024-01-15", 1, 2.0]],
        columns=pd.Index(["Stat Code", "Product Code", "Date Opened", 2024, 0], dtype=object),
    )

    with pytest.raises(DataError) as excinfo:
        _normalize_columns(df, Path("1800-odd.xlsx"))

    # The actionable error surfaces (not a TypeError from sorting mixed labels).
    assert "missing required columns" in str(excinfo.value)
    assert "Avg Bal" in str(excinfo.value)


def test_all_required_present_via_aliases_does_not_raise():
    df = pd.DataFrame(
        [["O", "182", "2024-01-15", 1000.0]],
        columns=["Stat Code", "Prod Code", "Date Opened", "Balance"],
    )

    _normalize_columns(df, Path("ok.xlsx"))

    # Aliases were renamed to canonical names.
    assert "Product Code" in df.columns
    assert "Avg Bal" in df.columns
