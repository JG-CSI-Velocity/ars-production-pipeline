"""Lock the seasonal-window arithmetic in mcc_code/12_mcc_seasonal.py.

The fix-the-calc choice for the audit's MCC seasonal bug was:
trim the input to the last 12 complete months before crosstabbing,
so every calendar month appears exactly once. The chart script
computes this inline (it's a .py exec script, not an importable
module), so this test re-derives the same window math and pins
down the contract.

The window-start / window-end calculation is what would silently
slip if someone "simplifies" the code later -- e.g. by dropping
the .replace(day=1) and breaking the partial-month exclusion.
"""
from __future__ import annotations

import pandas as pd
import pytest


def derive_window(max_date: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Same expression that lives in 12_mcc_seasonal.py."""
    last_complete = max_date.replace(day=1) - pd.Timedelta(days=1)
    window_start = last_complete.replace(day=1) - pd.DateOffset(months=11)
    return window_start, last_complete


def test_partial_month_excluded():
    """If max date is mid-June, the last complete month is May, not June."""
    start, end = derive_window(pd.Timestamp("2025-06-12"))
    assert end == pd.Timestamp("2025-05-31")
    assert start == pd.Timestamp("2024-06-01")


def test_exactly_twelve_months_in_window():
    """The window must always span exactly 12 distinct calendar months."""
    start, end = derive_window(pd.Timestamp("2025-06-12"))
    months_in_window = pd.date_range(start, end, freq="MS")
    assert len(months_in_window) == 12


def test_last_day_of_month_treated_as_partial():
    """Conservative semantics: even if max_date is the last day of June,
    we can't *verify* June is complete (the data may have been pulled at
    noon on June 30). Only treat a month as complete once we see a
    transaction in the following month. So max_date = June 30 -> last
    complete month is May."""
    start, end = derive_window(pd.Timestamp("2025-06-30"))
    assert end == pd.Timestamp("2025-05-31")
    assert start == pd.Timestamp("2024-06-01")


def test_one_day_into_next_month_makes_prior_month_complete():
    """As soon as ANY July transaction exists, June is provably complete
    -- regardless of how much July data we have."""
    start, end = derive_window(pd.Timestamp("2025-07-01"))
    assert end == pd.Timestamp("2025-06-30")
    assert start == pd.Timestamp("2024-07-01")


def test_window_spans_year_boundary():
    """A window ending in February should reach back through the
    previous March -- the year boundary is in the middle."""
    start, end = derive_window(pd.Timestamp("2025-03-15"))
    assert end == pd.Timestamp("2025-02-28")
    assert start == pd.Timestamp("2024-03-01")


def test_window_filter_collapses_multi_year_january():
    """Synthetic data with TWO Januarys (Jan-2024 and Jan-2025) plus an
    October-2024 must, after the window filter, contain only the Januarys
    that fall inside the window -- proving the pre-fix double-counting
    bug is gone."""
    rows = pd.DataFrame({
        "transaction_date": pd.to_datetime([
            "2024-01-15", "2024-01-20", "2024-01-25",  # Jan-2024
            "2024-10-05",                              # Oct-2024
            "2025-01-10", "2025-01-12",                # Jan-2025
            "2025-06-08",                              # Jun-2025 (partial)
        ]),
        "mcc_code": ["5411"] * 7,
    })
    max_date = rows["transaction_date"].max()
    start, end = derive_window(max_date)
    # Window: 2024-06-01 .. 2025-05-31.
    windowed = rows[(rows["transaction_date"] >= start) &
                    (rows["transaction_date"] <= end)]
    # Jan-2024 (before window), Jun-2025 (after window) excluded.
    # Oct-2024 and Jan-2025 retained.
    by_month = windowed["transaction_date"].dt.month.value_counts().to_dict()
    # Exactly one January (Jan-2025), exactly one October (Oct-2024).
    assert by_month.get(1) == 2  # both Jan-2025 rows
    assert by_month.get(10) == 1  # Oct-2024
    # No February-July of 2024 in the *filter result* either (no data).
    # And critically, no double-counted Jan.
    assert 1 in by_month
    # If the old buggy code had been used, Jan would have summed to 5
    # (3 from Jan-2024 + 2 from Jan-2025). The fix keeps it at 2.
