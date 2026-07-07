"""Unit tests for the migrated transaction.product module.

These are the payoff of the exec->module migration: the product analysis is now
a real module with data injected via ctx.txn, so its math is unit-testable with
synthetic frames -- no real M:\\ARS data, no exec namespace. (The exec cells were
none of these.)
"""

from __future__ import annotations

import pandas as pd
import pytest

from ars_analysis.analytics.transaction.product import ProductAnalysis
from ars_analysis.pipeline.context import (
    ClientInfo,
    OutputPaths,
    PipelineContext,
    TxnData,
)


def _make_ctx(tmp_path, combined, rewards):
    ctx = PipelineContext(
        client=ClientInfo(client_id="TEST", client_name="Test CU", month="2025.01"),
        paths=OutputPaths.from_dir(tmp_path),
    )
    ctx.txn = TxnData(combined=combined, rewards=rewards)
    return ctx


def _synthetic_frames():
    # 3 accounts, 2 products (P1 dominant), 2 months.
    combined = pd.DataFrame({
        "primary_account_num": ["1", "1", "1", "2", "2", "3"],
        "transaction_date": pd.to_datetime([
            "2025-01-05", "2025-01-06", "2025-02-01",
            "2025-01-10", "2025-02-02", "2025-01-15",
        ]),
        "amount": [10.0, 20.0, 30.0, 100.0, 50.0, 5.0],
        "year_month": pd.PeriodIndex(
            ["2025-01", "2025-01", "2025-02", "2025-01", "2025-02", "2025-01"], freq="M"
        ),
        "merchant_consolidated": ["A", "B", "A", "A", "B", "A"],
        "business_flag": ["No", "No", "No", "Yes", "Yes", "No"],
    })
    rewards = pd.DataFrame({
        "Acct Number": ["1", "2", "3"],
        "Prod Code": ["P1", "P1", "P2"],
        "Prod Desc": ["Checking", "Checking", "Savings"],
    })
    return combined, rewards


def test_validate_gates_on_txn():
    ctx = PipelineContext(
        client=ClientInfo(client_id="T", client_name="T", month="2025.01"),
        paths=OutputPaths(),
    )
    assert ProductAnalysis().validate(ctx)  # non-empty errors when ctx.txn is None


def test_aggregate_math(tmp_path):
    combined, rewards = _synthetic_frames()
    ctx = _make_ctx(tmp_path, combined, rewards)

    assert ProductAnalysis().validate(ctx) == []  # gate passes with txn data

    ProductAnalysis().run(ctx)
    bucket = ctx.results["transaction.product"]
    pa = bucket["tables"]["prod_agg"]

    # 2 products, ranked by txn_count desc -> "P1 - Checking" dominant (5 txns).
    assert list(pa["rank"]) == [1, 2]
    dominant = pa.iloc[0]
    assert dominant["product_label"] == "P1 - Checking"
    assert int(dominant["txn_count"]) == 5          # acct 1 (3) + acct 2 (2)
    assert int(dominant["unique_accounts"]) == 2

    # txn_pct sums to 100 across products; txn_per_account = txn_count/unique.
    assert pa["txn_pct"].sum() == pytest.approx(100.0)
    for _, row in pa.iterrows():
        assert row["txn_per_account"] == pytest.approx(row["txn_count"] / row["unique_accounts"])

    # total accounts matched = 3 (all accounts mapped to a product).
    assert bucket["insights"]["total_accts_prod"] == 3
    assert bucket["insights"]["total_txns_prod"] == 6


def test_results_carry_denominator(tmp_path):
    combined, rewards = _synthetic_frames()
    ctx = _make_ctx(tmp_path, combined, rewards)
    results = ProductAnalysis().run(ctx)

    slides = [r for r in results if r.success and r.chart_path is not None]
    assert slides, "expected at least one chart slide"
    for r in slides:
        assert r.denominator_label == "Eligible"
        assert r.denominator_n == 3
        assert r.slide_id.startswith("TXN-PROD-")


def test_does_not_mutate_ctx_txn(tmp_path):
    combined, rewards = _synthetic_frames()
    ctx = _make_ctx(tmp_path, combined, rewards)
    before_cols = list(ctx.txn.combined.columns)
    ProductAnalysis().run(ctx)
    # cell 01 mutated combined_df in place; the module must operate on a copy.
    assert list(ctx.txn.combined.columns) == before_cols
    assert "prod_code" not in ctx.txn.combined.columns
