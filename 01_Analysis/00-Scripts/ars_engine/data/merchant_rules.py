"""Merchant name consolidation for the v3 store.

The 960-line rule chain in
``analytics/txn_setup/06-merchant-name-consolidation.py`` is a PURE function
of the merchant name string. Rather than re-typing (and risking drift in)
those rules, this module loads that exact file by path -- one source of
truth, exact parity by construction. At cutover the file relocates here
verbatim and the legacy copy is deleted.

Application strategy is the vectorized one from
``txn_setup/07-consolidation-summary.py`` (#254): run the rule chain over
DISTINCT merchant names (tens of thousands), producing a name->consolidated
map that the store joins across millions of rows. The per-row "smart unknown"
fallback (relabel empty-merchant rows by transaction_type) lives in
txn_store's SQL because it depends on transaction_type, not the name.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

from ars_engine.core.config import repo_root

RULES_FILENAME = "06-merchant-name-consolidation.py"


def rules_path() -> Path:
    return (
        repo_root()
        / "01_Analysis"
        / "00-Scripts"
        / "analytics"
        / "txn_setup"
        / RULES_FILENAME
    )


def rules_mtime() -> int:
    """Rule-source mtime -- bakes into the store meta so a rules edit
    invalidates the persisted merchant map (ports consolidation_stale)."""
    try:
        return int(rules_path().stat().st_mtime)
    except OSError:
        return 0


_standardize = None


def standardize_merchant_name(name) -> str:
    """The canonical rule chain, loaded once from its legacy home."""
    global _standardize
    if _standardize is None:
        path = rules_path()
        spec = importlib.util.spec_from_file_location("merchant_rules_legacy", path)
        mod = importlib.util.module_from_spec(spec)
        # The legacy file was written for the exec()-namespace world and uses
        # the pd global without importing it; provide it before executing.
        mod.pd = pd
        spec.loader.exec_module(mod)
        _standardize = mod.standardize_merchant_name
    return _standardize(name)


def build_merchant_map(names) -> pd.DataFrame:
    """Map distinct merchant names to consolidated names.

    Mirrors 07-consolidation-summary: real-NaN names never reach the rules
    (callers map them to 'UNKNOWN MERCHANT' at join time, same as the
    legacy fillna).
    """
    uniq = pd.Index(pd.Series(list(names)).dropna().unique())
    return pd.DataFrame(
        {
            "merchant_name": uniq,
            "merchant_consolidated": [standardize_merchant_name(m) for m in uniq],
        }
    )
