"""Per-module smoke over a shared synthetic combined_df -- proves the fixture
pattern for the ~40 transaction-frame sections. Runs the real merchant data
aggregation script against a few hundred synthetic rows (plus the production
theme) and checks it produces its frames without error."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from ars_analysis.analytics import txn_wrapper as tw

_ANALYTICS = Path(tw.__file__).resolve().parent


def synthetic_combined() -> pd.DataFrame:
    """A minimal combined_df with the columns transaction-frame sections read:
    merchant_consolidated, year_month, transaction_date, primary_account_num,
    amount. 8 merchants x 12 months, varying volume so ranking/consistency/
    cohort logic all have something to chew on."""
    merchants = [f"MERCHANT {i}" for i in range(8)]
    months = [f"2026-{m:02d}" for m in range(1, 13)]
    rows = []
    for mi, mer in enumerate(merchants):
        for mo in months:
            for k in range(5 + mi):  # busier merchants have more rows
                rows.append({
                    "merchant_consolidated": mer,
                    "year_month": mo,
                    "transaction_date": f"{mo}-15",
                    "primary_account_num": f"A{(mi * 7 + k) % 20:03d}",
                    "amount": 100.0 + mi * 10 + k * 5,
                })
    return pd.DataFrame(rows)


def _namespace_with_theme() -> dict:
    ctx = SimpleNamespace(
        client=SimpleNamespace(client_id="T", client_name="Test", month="2026.06",
                               assigned_csm="c", eligible_stat_codes=["O"]),
        data=None,
    )
    ns = tw._build_namespace(ctx)
    tw._load_shared_theme(ns)  # GEN_COLORS + gen_* helpers, as in a real run
    return ns


def test_merchant_data_script_runs_over_synthetic_combined():
    ns = _namespace_with_theme()
    ns["combined_df"] = synthetic_combined()

    script = _ANALYTICS / "merchant" / "01_merchant_data.py"
    exec(compile(script.read_text(encoding="utf-8"), str(script), "exec"), ns)  # noqa: S102

    # Produces the merchant aggregation frames the rest of the section consumes.
    merch_agg = ns.get("merch_agg")
    assert merch_agg is not None and len(merch_agg) == 8
    assert {"merchant_consolidated", "txn_count", "total_spend", "rank"} <= set(merch_agg.columns)
    assert list(merch_agg["rank"]) == sorted(merch_agg["rank"])  # ranked
    assert "consistency_df" in ns  # cv frame built (may be filtered by $10k floor)
    assert "cohort_df" in ns and len(ns["cohort_df"]) == 12  # one row per month
