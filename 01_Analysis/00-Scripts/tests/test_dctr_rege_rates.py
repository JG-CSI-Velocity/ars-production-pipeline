"""Numerical regression tests for DCTR and Reg E rates.

Attrition had locked-value tests; DCTR and Reg E did not, so a drift in the
denominator, the debit value set, or the Reg-E column-of-record selection would
have shipped silently. These pin the INTENDED behavior (owner-ratified):

- DCTR = with_debit / total against the given (Eligible) base. No denominator
  surgery -- the base is whatever DataFrame the caller passes.
- The canonical debit value set counts strings AND booleans/ints (Yes/Y/D/True/1).
- Reg E rate = opted_in / total against the configured opt-in codes.
- The Reg E column of record is the chronologically-latest, not alphabetical.
"""

from __future__ import annotations

import pandas as pd

from ars_analysis.analytics.dctr._helpers import analyze_historical_dctr, dctr
from ars_analysis.analytics.rege._helpers import detect_reg_e_column, rege


def test_dctr_is_with_debit_over_total():
    df = pd.DataFrame({"Debit?": ["Yes"] * 10 + ["No"] * 10})
    total, with_debit, rate = dctr(df)
    assert (total, with_debit) == (20, 10)
    assert rate == 0.5


def test_dctr_counts_booleans_and_ints_like_strings():
    # The canonical value set must treat True/1 as 'has debit' so the Value,
    # DCTR and mailer sections agree for boolean/int-coded clients.
    df = pd.DataFrame({"Debit?": [True, 1, "Y", "D", False, 0, "N", ""]})
    total, with_debit, rate = dctr(df)
    assert total == 8
    assert with_debit == 4  # True, 1, "Y", "D"
    assert rate == 0.5


def test_analyze_historical_dctr_overall_rate():
    df = pd.DataFrame({
        "Date Opened": ["2024-01-01"] * 4,
        "Debit?": ["Yes", "Yes", "No", "No"],
        "Business?": ["No"] * 4,
    })
    _yearly, _decade, ins = analyze_historical_dctr(df)
    assert ins["total_accounts"] == 4
    assert ins["with_debit_count"] == 2
    assert ins["overall_dctr"] == 0.5


def test_rege_rate_is_opted_in_over_total():
    df = pd.DataFrame({"Reg E Code Jan26": ["OI", "OI", "OO", "OO", "OO"]})
    total, opted, rate = rege(df, "Reg E Code Jan26", opt_list=["OI"])
    assert (total, opted) == (5, 2)
    assert rate == 0.4


def test_detect_reg_e_column_is_chronological_not_alphabetical():
    # Alphabetical last would be 'Nov25' (N > J > D); chronological last is Jan26.
    df = pd.DataFrame({
        "Reg E Code Dec25": [0],
        "Reg E Code Jan26": [0],
        "Reg E Code Nov25": [0],
        "Other": [0],
    })
    assert detect_reg_e_column(df) == "Reg E Code Jan26"
