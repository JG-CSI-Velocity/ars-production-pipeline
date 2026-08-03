"""Parity tests for the vectorized merchant consolidation (perf quick win).

07-consolidation-summary.py used to run combined_df['merchant_name']
.apply(standardize_merchant_name) -- a ~960-line if-chain called once per row
over millions of rows. The vectorized form maps the function over the DISTINCT
merchant strings and broadcasts back (same trick as tag_competitors, issue
#214). standardize_merchant_name depends only on its input string, so the two
forms must be exactly equivalent -- these tests pin that.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

_SETUP = Path(__file__).resolve().parents[1] / "analytics" / "txn_setup"
_CONSOLIDATOR = _SETUP / "06-merchant-name-consolidation.py"
_SUMMARY = _SETUP / "07-consolidation-summary.py"


def _load_consolidator() -> dict:
    ns: dict = {"pd": pd}
    src = _CONSOLIDATOR.read_text(encoding="utf-8")
    exec(compile(src, str(_CONSOLIDATOR), "exec"), ns)  # noqa: S102
    return ns


def _run_summary_head(combined_df: pd.DataFrame) -> dict:
    # Exec 07 up to the summary/display section: just the consolidation +
    # smart-unknown fallback, which is the part the perf change touches.
    src = _SUMMARY.read_text(encoding="utf-8")
    head = src.split("# Calculate consolidation impact")[0]
    ns = _load_consolidator()
    ns["combined_df"] = combined_df
    exec(compile(head, str(_SUMMARY), "exec"), ns)  # noqa: S102
    return ns


_FIXTURE_MERCHANTS = [
    "WALMART.COM",
    "wal-mart #3893",
    "WM SUPERCENTER 1234",
    "APPLE.COM/BILL",
    "apple com bill cupertino",
    "NETFLIX.COM",
    "Netflix com",
    "JOE'S DINER LLC",
    "JOE'S DINER LLC",  # duplicate on purpose
    "",  # empty string (not NaN)
    "   ",  # whitespace only
    "NAN",  # literal sentinel string
    "None",
    None,  # real NaN
    "TROPICAL FIN CU FT LAUDER FL",
]


def _fixture_df(merchants, ttype=None) -> pd.DataFrame:
    df = pd.DataFrame({"merchant_name": pd.Series(merchants, dtype="object")})
    if ttype is not None:
        df["transaction_type"] = ttype
    return df


def test_vectorized_matches_rowwise_apply():
    # No transaction_type column -> the smart-unknown fallback never fires,
    # isolating the line the perf change replaced.
    df = _fixture_df(_FIXTURE_MERCHANTS)
    ns = _run_summary_head(df)

    expected = df["merchant_name"].apply(ns["standardize_merchant_name"])
    pd.testing.assert_series_equal(
        ns["combined_df"]["merchant_consolidated"],
        expected,
        check_names=False,
    )


def test_vectorized_handles_all_nan_column():
    df = _fixture_df([None, None, None])
    ns = _run_summary_head(df)
    assert (ns["combined_df"]["merchant_consolidated"] == "UNKNOWN MERCHANT").all()


def test_vectorized_handles_categorical_dtype():
    df = _fixture_df(_FIXTURE_MERCHANTS)
    df["merchant_name"] = df["merchant_name"].astype("category")
    ns = _run_summary_head(df)

    expected = (
        df["merchant_name"]
        .astype("object")
        .apply(ns["standardize_merchant_name"])
    )
    pd.testing.assert_series_equal(
        ns["combined_df"]["merchant_consolidated"],
        expected,
        check_names=False,
    )


def test_smart_unknown_fallback_still_relabels_by_transaction_type():
    df = _fixture_df(
        ["", "", "", "WALMART.COM"],
        ttype=["ATM", "ACH", "weird-code", "PIN"],
    )
    ns = _run_summary_head(df)
    got = ns["combined_df"]["merchant_consolidated"].tolist()
    assert got == [
        "ATM WITHDRAWAL",
        "ACH TRANSFER (NO MERCHANT)",
        "UNKNOWN MERCHANT",  # unmapped code falls through
        "WALMART.COM",  # online kept separate from WALMART (ALL LOCATIONS)
    ]


def test_vectorized_faster_path_uses_uniques(monkeypatch):
    # The whole point: the consolidator must run once per DISTINCT merchant,
    # not once per row. 6 rows / 2 distinct values -> at most a handful of
    # calls (map may probe NaN handling), never one per row.
    calls = {"n": 0}
    ns = _load_consolidator()
    real = ns["standardize_merchant_name"]

    def counting(name):
        calls["n"] += 1
        return real(name)

    df = _fixture_df(["WALMART.COM", "NETFLIX.COM"] * 3)
    src = _SUMMARY.read_text(encoding="utf-8")
    head = src.split("# Calculate consolidation impact")[0]
    ns["standardize_merchant_name"] = counting
    ns["combined_df"] = df
    exec(compile(head, str(_SUMMARY), "exec"), ns)  # noqa: S102

    assert calls["n"] <= 2, f"expected per-unique calls, got {calls['n']} for 6 rows"
