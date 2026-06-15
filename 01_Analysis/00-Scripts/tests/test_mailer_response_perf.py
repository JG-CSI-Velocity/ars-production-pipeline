"""Regression tests for the mailer.response performance fixes (#208).

Both fixes must be OUTPUT-PRESERVING -- they only remove redundant per-wave work:
  1. analyze_ladder pre-filters to responded rows instead of iterrows() over the
     whole member table. The dropped rows are exactly those the NaN guard skipped.
  2. compute_inside_numbers parses Date Opened / DOB once per run (cached on the
     run context) instead of re-parsing with format="mixed" on every wave.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from ars_analysis.analytics.mailer._helpers import (  # noqa: E402
    analyze_ladder,
    compute_inside_numbers,
)

PAIRS = [("W1", "resp_w1", "mail_w1"), ("W2", "resp_w2", "mail_w2")]


def _ladder_data() -> pd.DataFrame:
    """Members spanning every classify_responder branch for W2 vs W1."""
    rows = [
        ("TH-10", "TH-20"),    # A: repeat, up   (3 -> 5)
        (None, "TH-10"),       # B: first        (no prior success)
        ("TH-15", "TH-10"),    # C: repeat, down (4 -> 3)
        ("TH-10", "TH-10"),    # D: repeat, same (3 -> 3)
        ("NU 1-4", "NU 5+"),   # E: first        (prior NU 1-4 scores 1, not a success)
        ("TH-10", None),       # F: NaN current  -> skipped
        (None, None),          # G: NaN current  -> skipped
        ("TH-10", "NU 1-4"),   # H: current scores 1 (<2) -> not included
    ]
    return pd.DataFrame(rows, columns=["resp_w1", "resp_w2"])


def test_analyze_ladder_exact_counts():
    result = analyze_ladder(_ladder_data(), PAIRS, month_idx=1)
    assert result["total_successful"] == 5      # A B C D E
    assert result["first_count"] == 2           # B E
    assert result["repeat_count"] == 3          # A C D
    assert result["movement_up"] == 1           # A
    assert result["movement_same"] == 1         # D
    assert result["movement_down"] == 1         # C
    assert result["distribution"] == {
        "NU 5+": 1, "TH-10": 3, "TH-15": 0, "TH-20": 1, "TH-25": 0,
    }


def test_analyze_ladder_ignores_nan_rows():
    """The pre-filter's safety net: all-NaN members must not change the result."""
    base = _ladder_data()
    padded = pd.concat(
        [base, pd.DataFrame([(None, None)] * 200, columns=base.columns)],
        ignore_index=True,
    )
    assert analyze_ladder(padded, PAIRS, 1) == analyze_ladder(base, PAIRS, 1)


def test_analyze_ladder_first_wave_is_none():
    assert analyze_ladder(_ladder_data(), PAIRS, 0) is None


def _inside_numbers_ctx():
    now = pd.Timestamp.now()
    data = pd.DataFrame({
        "resp": ["TH-10", "TH-15", "NU 5+", None],          # 3 responders + 1 non
        "Date Opened": [
            now - pd.Timedelta(days=365),                    # 1.0 yr  -> <2
            now - pd.Timedelta(days=5 * 365),                # 5.0 yr
            now - pd.Timedelta(days=180),                    # 0.5 yr  -> <2
            now - pd.Timedelta(days=10 * 365),
        ],
        "DOB": [
            now - pd.Timedelta(days=int(25 * 365.25)),       # age 25 -> 18-30
            now - pd.Timedelta(days=int(25 * 365.25)),       # age 25 -> 18-30
            now - pd.Timedelta(days=int(50 * 365.25)),       # age 50 -> 45-60
            now - pd.Timedelta(days=int(40 * 365.25)),
        ],
    })
    client = SimpleNamespace(reg_e_opt_in=[], reg_e_column=None)
    return SimpleNamespace(data=data, results={}, client=client)


EXPECTED_INSIDE = [
    ("67%", "of Responders were accounts opened fewer than 2 years ago"),  # 2/3
    ("67%", "of Responders aged 18-30"),                                   # 2/3
]


def test_compute_inside_numbers_values():
    ctx = _inside_numbers_ctx()
    metrics = compute_inside_numbers(ctx, ctx.data, "resp", ladder=None)
    assert metrics == EXPECTED_INSIDE


def test_compute_inside_numbers_caches_dates():
    ctx = _inside_numbers_ctx()
    compute_inside_numbers(ctx, ctx.data, "resp", ladder=None)
    cache = ctx.results["_mailer_parsed_dates"]
    assert cache["_built"] is True
    first_parse = cache["Date Opened"]

    # Second wave reuses the same parsed Series object -- no re-parse.
    compute_inside_numbers(ctx, ctx.data, "resp", ladder=None)
    assert ctx.results["_mailer_parsed_dates"]["Date Opened"] is first_parse


def test_cached_and_uncached_paths_agree():
    """data is ctx.data (cached) vs a foreign frame (parsed inline) must match."""
    ctx = _inside_numbers_ctx()
    cached = compute_inside_numbers(ctx, ctx.data, "resp", ladder=None)

    foreign = _inside_numbers_ctx()
    foreign.data = pd.DataFrame()  # force the non-cached branch
    uncached = compute_inside_numbers(foreign, _inside_numbers_ctx().data, "resp", ladder=None)
    assert cached == uncached == EXPECTED_INSIDE
