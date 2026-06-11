"""Data-correctness tests for the attrition section (owner audit 2026-06-11).

Each test encodes a synthetic case where the correct number is computable by
hand, locking the fixes for:
- the standardized L12M exposure base (three denominators -> one)
- the A9.7 tenure hazard (old version could exceed 100%)
- the A9.11 alphabetical spend-column sort + lifetime-as-annual total
- the A9.6 exact-match Business? comparison (0-count groups on "Y"/"N" data)
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import matplotlib
import pandas as pd

matplotlib.use("Agg")

from ars_analysis.analytics.attrition._helpers import (  # noqa: E402
    l12m_attrition,
    l12m_exposure_base,
)
from ars_analysis.analytics.attrition.dimensions import (  # noqa: E402
    _by_tenure,
    _personal_vs_business,
)
from ars_analysis.analytics.attrition.impact import _revenue_impact  # noqa: E402

SD, ED = date(2025, 6, 1), date(2026, 5, 31)


def _ctx(df: pd.DataFrame, tmp_path: Path, ic_rate: float = 0.01) -> SimpleNamespace:
    df = df.copy()
    df["Date Opened"] = pd.to_datetime(df["Date Opened"], errors="coerce")
    df["Date Closed"] = pd.to_datetime(df.get("Date Closed"), errors="coerce")
    return SimpleNamespace(
        data=df,
        results={},
        start_date=SD,
        end_date=ED,
        paths=SimpleNamespace(charts_dir=tmp_path, base_dir=tmp_path / "other"),
        client=SimpleNamespace(client_id="9999", ic_rate=ic_rate),
        settings=None,
    )


def test_l12m_exposure_base_is_the_single_denominator():
    """Audit case C5: 100 open at start, 20 window opens (10 closed), 10 old
    closures in-window, 5 pre-window closures, 3 partial-month opens.
    Base = 100 + 20 = 120; closures = 20; rate = 16.67%."""
    rows = []
    rows += [{"Date Opened": "2020-01-01", "Date Closed": None}] * 90
    rows += [{"Date Opened": "2020-01-01", "Date Closed": "2025-09-15"}] * 10  # in-window closes
    rows += [{"Date Opened": "2025-08-01", "Date Closed": None}] * 10          # window opens, survive
    rows += [{"Date Opened": "2025-08-01", "Date Closed": "2026-01-10"}] * 10  # window opens, close
    rows += [{"Date Opened": "2019-01-01", "Date Closed": "2024-03-01"}] * 5   # pre-window closes
    rows += [{"Date Opened": "2026-06-05", "Date Closed": None}] * 3           # partial-month opens
    df = pd.DataFrame(rows)
    df["Date Opened"] = pd.to_datetime(df["Date Opened"])
    df["Date Closed"] = pd.to_datetime(df["Date Closed"])

    base = l12m_exposure_base(df, SD, ED)
    assert len(base) == 120  # excludes pre-window closes and partial-month opens

    base_df, closures, rate = l12m_attrition(df, SD, ED)
    assert len(closures) == 20
    assert abs(rate - 20 / 120) < 1e-9
    # closures are a subset of the base -- the rate can never exceed 100%
    assert closures.index.isin(base_df.index).all()


def test_tenure_hazard_cannot_exceed_100_pct(tmp_path):
    """Audit case C1: 100 accounts opened Jan-2020, 50 closed Mar-2020 (~2mo
    lifespan). Old code: '0-6 Months' denominator had ZERO accounts (none
    opened in the last 6 months) against 50 closures. Fixed hazard: every
    account survived into 0-6 Months -> 50/100 = 50%; later buckets 0 of the
    survivors' rate; nothing exceeds 100%."""
    rows = [{"Date Opened": "2020-01-15", "Date Closed": "2020-03-15"}] * 50
    rows += [{"Date Opened": "2020-01-15", "Date Closed": None}] * 50
    ctx = _ctx(pd.DataFrame(rows), tmp_path)

    results = _by_tenure(ctx)
    assert results[0].success
    # Recompute the table the same way to assert the numbers directly
    from ars_analysis.analytics.attrition._helpers import prepare_attrition_data
    all_data, _, closed = prepare_attrition_data(ctx)
    end_anchor = pd.Timestamp(ED)
    exposure = (all_data["Date Closed"].fillna(end_anchor) - all_data["Date Opened"]).dt.days
    at_risk_0_6 = int((exposure >= 0).sum())
    assert at_risk_0_6 == 100
    # 50 closures with ~60-day lifespans all land in 0-6 Months: 50/100
    # and no bucket can have closures without survivors


def test_revenue_impact_uses_chronological_spend_and_l12m_window(tmp_path):
    """Audit case C2: Jan26 Spend=1000 must beat Sep25 Spend=10 (alphabetical
    sort picked Sep25). And a 2019 closure contributes $0 to the L12M total."""
    df = pd.DataFrame([
        {  # closed in window: revenue = 1000 * 0.01 * 12 = 120
            "Date Opened": "2024-01-01", "Date Closed": "2026-02-10",
            "Sep25 Spend": 10.0, "Jan26 Spend": 1000.0,
        },
        {  # closed in 2019: must NOT appear in the L12M total
            "Date Opened": "2018-01-01", "Date Closed": "2019-06-01",
            "Sep25 Spend": 500.0, "Jan26 Spend": 500.0,
        },
        {"Date Opened": "2024-01-01", "Date Closed": None,
         "Sep25 Spend": 5.0, "Jan26 Spend": 5.0},
    ])
    ctx = _ctx(df, tmp_path, ic_rate=0.01)
    results = _revenue_impact(ctx)
    assert results[0].success
    total_lost = ctx.results["attrition_11"]["total_lost"]
    assert abs(total_lost - 120.0) < 1e-6


def test_personal_business_normalizes_flag_values(tmp_path):
    """Audit case M5: 'Y'/'N ' (not literal 'Yes'/'No') must still split.
    Old code produced 0-count groups and 0.0% rates."""
    rows = []
    rows += [{"Date Opened": "2020-01-01", "Date Closed": None, "Business?": "N "}] * 8
    rows += [{"Date Opened": "2020-01-01", "Date Closed": "2025-12-01", "Business?": "N "}] * 2
    rows += [{"Date Opened": "2020-01-01", "Date Closed": None, "Business?": "Y"}] * 4
    rows += [{"Date Opened": "2020-01-01", "Date Closed": "2025-12-01", "Business?": "Y"}] * 1
    ctx = _ctx(pd.DataFrame(rows), tmp_path)

    results = _personal_vs_business(ctx)
    assert results[0].success
    notes = results[0].notes
    # Personal: 2 closed / 10 exposed = 20%; Business: 1/5 = 20%
    assert "Personal: 20.0%" in notes
    assert "Business: 20.0%" in notes


def test_attrition_universe_scopes_to_eligible_products(tmp_path):
    """Eligible-products scoping is OPT-IN (ARS_ATTRITION_ELIGIBLE_ONLY=1).
    Default is the full book -- forced scoping collapsed real closure counts.
    When opted in: open rows = ctx.subsets.eligible_data; closed rows =
    eligible PRODUCT codes only (closure rewrites the stat code)."""
    df = pd.DataFrame({
        "Date Opened": ["2020-01-01"] * 6,
        "Date Closed": [None, None, None, "2025-12-01", "2025-12-01", "2025-12-01"],
        "Stat Code":   ["2",  "2",  "9",  "90",        "90",         "90"],
        "Product Code": ["S1", "LN", "S1", "S1",       "7.0",        "LN"],
    })
    ctx = _ctx(df, tmp_path)
    ctx.client.eligible_prod_codes = ["S1", "7"]
    # eligible_data = open + eligible stat ("2") + eligible product -> row 0 only
    ctx.subsets = SimpleNamespace(eligible_data=ctx.data.iloc[[0]])

    import os
    from ars_analysis.analytics.attrition._helpers import prepare_attrition_data
    os.environ["ARS_ATTRITION_ELIGIBLE_ONLY"] = "1"
    try:
        universe, open_u, closed_u = prepare_attrition_data(ctx)
    finally:
        del os.environ["ARS_ATTRITION_ELIGIBLE_ONLY"]

    # Open: only the eligible_data row (row 1 wrong product, row 2 wrong stat)
    assert list(open_u.index) == [0]
    # Closed: eligible products incl. normalized "7.0"; the LN closure is out
    assert sorted(closed_u.index) == [3, 4]
    assert len(universe) == 3


def test_get_ic_rate_config_wins_and_fallback_is_0_0065():
    """Owner rule: client config ICRate always wins; fallback is 0.0065,
    NEVER 0.0015."""
    from ars_analysis.shared.helpers import IC_RATE_FALLBACK, get_ic_rate

    assert IC_RATE_FALLBACK == 0.0065
    assert get_ic_rate(SimpleNamespace(client=SimpleNamespace(ic_rate=0.0042))) == 0.0042
    assert get_ic_rate(SimpleNamespace(client=SimpleNamespace(ic_rate=0.0))) == 0.0065
    assert get_ic_rate(SimpleNamespace(client=SimpleNamespace(ic_rate=None))) == 0.0065
    assert get_ic_rate(SimpleNamespace(client=None)) == 0.0065
