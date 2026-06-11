"""Shared helper functions used across analysis pipelines."""

from __future__ import annotations

import pandas as pd

# Owner rule (2026-06-11): the interchange-rate fallback is 0.0065 -- it must
# NEVER be 0.0015 -- and the client config ICRate always wins when set.
IC_RATE_FALLBACK = 0.0065


def get_ic_rate(ctx) -> float:
    """Interchange rate for revenue estimates: client config, else 0.0065."""
    rate = getattr(getattr(ctx, "client", None), "ic_rate", None)
    try:
        rate = float(rate) if rate else 0.0
    except (TypeError, ValueError):
        rate = 0.0
    return rate if rate > 0 else IC_RATE_FALLBACK


def safe_percentage(numerator: float, denominator: float) -> float:
    """Compute percentage with zero-division and NaN guard. Returns 0-100."""
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return round((numerator / denominator) * 100, 2)


def safe_ratio(numerator: float, denominator: float, decimals: int = 2) -> float:
    """Compute ratio with zero-division and NaN guard."""
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return round(numerator / denominator, decimals)
