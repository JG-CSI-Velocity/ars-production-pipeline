"""Shared synthetic fixtures for per-section smoke tests.

`synthetic_combined()` is a minimal combined_df carrying the columns the
transaction-frame sections read, so their data-aggregation scripts can run
end-to-end without real client data. Extend it here (add a column) when a new
section needs one -- one fixture, reused by every section smoke.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from ars_analysis.analytics import txn_wrapper as tw

ANALYTICS = Path(tw.__file__).resolve().parent

_MCCS = ["5411", "5812", "5541", "6011"]
_TXN_TYPES = ["PIN", "SIG", "ACH", "POS"]


def synthetic_combined() -> pd.DataFrame:
    """8 merchants x 12 months, varying volume, with the common column contract:
    identity (merchant_consolidated, primary_account_num/account_number),
    time (year_month, transaction_date), money (amount), and category/branch
    (mcc_code, transaction_type, branch)."""
    merchants = [f"MERCHANT {i}" for i in range(8)]
    months = [f"2026-{m:02d}" for m in range(1, 13)]
    rows = []
    for mi, mer in enumerate(merchants):
        for mo in months:
            for k in range(5 + mi):
                acct = f"A{(mi * 7 + k) % 20:03d}"
                rows.append({
                    "merchant_consolidated": mer,
                    "year_month": mo,
                    "transaction_date": f"{mo}-15",
                    "primary_account_num": acct,
                    "account_number": acct,
                    "amount": 100.0 + mi * 10 + k * 5,
                    "mcc_code": _MCCS[k % len(_MCCS)],
                    "transaction_type": _TXN_TYPES[k % len(_TXN_TYPES)],
                    "branch": f"BR{mi % 3}",
                })
    return pd.DataFrame(rows)


def synthetic_rewards() -> pd.DataFrame:
    """A minimal account-level frame (the ODD / rewards_df) carrying a broad set
    of the columns account-level sections read. 20 accounts; sections that need
    a column absent here gate themselves off gracefully."""
    n = 20
    rows = []
    for i in range(n):
        acct = f"A{i:03d}"
        rows.append({
            "account_number": acct,
            "primary_account_num": acct,
            "Acct Number": acct,
            "ICS Account": i % 3 == 0,
            "Source": ["Mail", "Branch", "Digital"][i % 3],
            "Curr Bal": 100.0 * (i + 1),
            "Avg Bal": 90.0 * (i + 1),
            "Stat Code": ["O", "O", "C"][i % 3],
            "Product Code": ["CK", "SV", "MM"][i % 3],
            "Date Opened": f"2024-{(i % 12) + 1:02d}-01",
            "Date Closed": "" if i % 4 else "2026-03-01",
            "Business?": i % 5 == 0,
            "Account Holder Age": 25 + (i % 50),
            "branch": f"BR{i % 3}",
            "Branch": f"BR{i % 3}",
            "DC Indicator": i % 2,
            "pin_count": i, "pin_dollars": 10.0 * i,
            "sig_count": i + 1, "sig_dollars": 12.0 * i,
        })
    return pd.DataFrame(rows)


def namespace_with_theme() -> dict:
    """A section execution namespace with the production theme loaded (as in a
    real run), ready for a combined_df to be dropped in."""
    ctx = SimpleNamespace(
        client=SimpleNamespace(client_id="T", client_name="Test", month="2026.06",
                               assigned_csm="c", eligible_stat_codes=["O"]),
        data=None,
    )
    ns = tw._build_namespace(ctx)
    tw._load_shared_theme(ns)
    return ns
