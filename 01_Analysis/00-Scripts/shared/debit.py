"""Canonical 'has debit card' detection.

Single source of truth so every analytics module agrees on:
1. Which column to read (auto-detect across known aliases).
2. Which values count as 'has debit' (string codes + booleans + ints).

Before this module existed, four divergent definitions lived in:
- analytics/dctr/_helpers.py (the most permissive set)
- analytics/insights/dormant.py (string-only)
- analytics/insights/branch_scorecard.py (string-only)
- analytics/mailer/reach.py (allowed booleans and 1, but used "Yes/Y/True/1" only)

They disagreed on cases like `True`, `1`, `"D"`, `"DC"`, producing different
debit-holder counts across modules for the same client.
"""

from __future__ import annotations

import pandas as pd

DEBIT_CANDIDATES: tuple[str, ...] = ("Debit?", "Debit", "DC Indicator", "DC_Indicator")
DEBIT_YES_VALUES: frozenset[str] = frozenset(("YES", "Y", "TRUE", "1", "D", "DC", "DEBIT"))


def detect_debit_col(df: pd.DataFrame) -> str | None:
    """Return the first known debit-card column present in df, or None."""
    for c in DEBIT_CANDIDATES:
        if c in df.columns:
            return c
    return None


def debit_mask(df: pd.DataFrame, col: str | None = None) -> pd.Series:
    """Boolean mask: True where the row has a debit card.

    Tolerates string codes (Yes/Y/D/DC/Debit), booleans (True/False),
    and integer flags (1/0). Empty / NaN / unknown values become False.
    """
    if col is None:
        col = detect_debit_col(df)
    if col is None or col not in df.columns:
        return pd.Series(False, index=df.index)
    return df[col].astype(str).str.strip().str.upper().isin(DEBIT_YES_VALUES)


def has_debit(df: pd.DataFrame, col: str | None = None) -> pd.DataFrame:
    """Return the subset of df where the row has a debit card."""
    return df[debit_mask(df, col)]
