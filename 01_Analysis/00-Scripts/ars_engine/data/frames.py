"""FrameCatalog -- the one door sections use to reach data.

Sections declare ``requires_frames`` keys; the runner passes a catalog bound
to the client. Frames are small pre-aggregated pandas DataFrames pulled from
the DuckDB store (txn.*) or the loaded ODD subsets (odd.*), cached per run.

Keys:
    txn.monthly_by_merchant   txn.monthly_by_mcc      txn.monthly_by_type
    txn.monthly_by_account    txn.account_first_last
    odd.data / odd.open / odd.eligible / odd.eligible_personal /
    odd.eligible_business / odd.eligible_with_debit / odd.last_12_months
"""

from __future__ import annotations

import pandas as pd

from ars_engine.core.context import PipelineContext
from ars_engine.data import txn_store

_TXN_FRAMES = {
    "txn.monthly_by_merchant": "monthly_by_merchant",
    "txn.monthly_by_mcc": "monthly_by_mcc",
    "txn.monthly_by_type": "monthly_by_type",
    "txn.monthly_by_account": "monthly_by_account",
    "txn.account_first_last": "account_first_last",
}

_ODD_FRAMES = {
    "odd.data": lambda ctx: ctx.data,
    "odd.open": lambda ctx: ctx.subsets.open_accounts,
    "odd.eligible": lambda ctx: ctx.subsets.eligible_data,
    "odd.eligible_personal": lambda ctx: ctx.subsets.eligible_personal,
    "odd.eligible_business": lambda ctx: ctx.subsets.eligible_business,
    "odd.eligible_with_debit": lambda ctx: ctx.subsets.eligible_with_debit,
    "odd.last_12_months": lambda ctx: ctx.subsets.last_12_months,
}


class FrameCatalog:
    """Lazy, per-run frame access with an in-memory cache."""

    def __init__(self, ctx: PipelineContext):
        self._ctx = ctx
        self._cache: dict[str, pd.DataFrame] = {}

    def keys(self) -> list[str]:
        return sorted(list(_TXN_FRAMES) + list(_ODD_FRAMES))

    def get(self, key: str) -> pd.DataFrame:
        if key in self._cache:
            return self._cache[key]
        if key in _TXN_FRAMES:
            df = txn_store.read_table(self._ctx.client.client_id, _TXN_FRAMES[key])
        elif key in _ODD_FRAMES:
            df = _ODD_FRAMES[key](self._ctx)
            if df is None:
                raise KeyError(f"Frame {key!r} not loaded yet (run the load/subsets steps first)")
        else:
            raise KeyError(f"Unknown frame key: {key!r} (known: {self.keys()})")
        self._cache[key] = df
        return df

    def get_all(self, keys) -> dict[str, pd.DataFrame]:
        return {k: self.get(k) for k in keys}

