"""Cache-hit gating for txn_setup 07/09 (perf quick win).

On a Parquet cache HIT the cache already contains merchant_consolidated and
the normalized business_flag merge -- yet 07 re-ran the full consolidation
and 09 re-did the full-frame astype/strip + ODD merge on every run. These
tests pin that the gated fast path produces byte-identical frames, and that
the staleness guards (changed consolidation rules, newer ODD) force the
recompute paths.
"""

from __future__ import annotations

import importlib.util
import os
import time
from pathlib import Path

import pandas as pd

_ANALYTICS = Path(__file__).resolve().parents[1] / "analytics"
_SETUP = _ANALYTICS / "txn_setup"
_CONSOLIDATOR = _SETUP / "06-merchant-name-consolidation.py"
_SUMMARY = _SETUP / "07-consolidation-summary.py"
_ODD_MERGE = _SETUP / "09-oddd-account-type.py"


def _load_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# txn_cache.consolidation_stale
# ---------------------------------------------------------------------------

def test_consolidation_stale_none_when_sources_older(tmp_path):
    txn_cache = _load_by_path("txn_cache_t1", _ANALYTICS / "txn_cache.py")
    src = tmp_path / "06.py"
    src.write_text("# rules")
    cache = tmp_path / "cache.parquet"
    cache.write_text("cache")
    os.utime(src, (time.time() - 100, time.time() - 100))
    assert txn_cache.consolidation_stale(cache, [src]) is None


def test_consolidation_stale_names_newer_source(tmp_path):
    txn_cache = _load_by_path("txn_cache_t2", _ANALYTICS / "txn_cache.py")
    cache = tmp_path / "cache.parquet"
    cache.write_text("cache")
    os.utime(cache, (time.time() - 100, time.time() - 100))
    src = tmp_path / "06.py"
    src.write_text("# changed rules")
    assert txn_cache.consolidation_stale(cache, [src]) == "06.py"


def test_consolidation_stale_none_without_cache(tmp_path):
    txn_cache = _load_by_path("txn_cache_t3", _ANALYTICS / "txn_cache.py")
    src = tmp_path / "06.py"
    src.write_text("# rules")
    assert txn_cache.consolidation_stale(tmp_path / "missing.parquet", [src]) is None


def test_consolidation_stale_treats_unreadable_source_as_stale(tmp_path):
    txn_cache = _load_by_path("txn_cache_t4", _ANALYTICS / "txn_cache.py")
    cache = tmp_path / "cache.parquet"
    cache.write_text("cache")
    assert txn_cache.consolidation_stale(cache, [tmp_path / "gone.py"]) == "gone.py"


# ---------------------------------------------------------------------------
# 07 gating
# ---------------------------------------------------------------------------

def _consolidator_ns() -> dict:
    ns: dict = {"pd": pd}
    exec(compile(_CONSOLIDATOR.read_text(encoding="utf-8"),
                 str(_CONSOLIDATOR), "exec"), ns)  # noqa: S102
    return ns


def _exec_07(ns: dict) -> dict:
    head = _SUMMARY.read_text(encoding="utf-8").split(
        "# Calculate consolidation impact"
    )[0]
    exec(compile(head, str(_SUMMARY), "exec"), ns)  # noqa: S102
    return ns


def _txn_df() -> pd.DataFrame:
    return pd.DataFrame({
        "merchant_name": ["WAL-MART #1", "NETFLIX.COM", None, ""],
        "transaction_type": ["PIN", "SIG", "ATM", "ACH"],
    })


def test_07_skips_recompute_on_pure_cache_hit():
    calls = {"n": 0}
    ns = _consolidator_ns()
    real = ns["standardize_merchant_name"]

    def counting(name):
        calls["n"] += 1
        return real(name)

    df = _txn_df()
    df["merchant_consolidated"] = ["CACHED-A", "CACHED-B", "CACHED-C", "CACHED-D"]
    ns.update({
        "standardize_merchant_name": counting,
        "combined_df": df,
        "SKIP_COMBINE": True,
        "CONSOLIDATION_STALE": False,
    })
    _exec_07(ns)

    assert calls["n"] == 0
    assert ns["combined_df"]["merchant_consolidated"].tolist() == [
        "CACHED-A", "CACHED-B", "CACHED-C", "CACHED-D",
    ]
    assert ns["_consolidation_recomputed"] is False


def test_07_recomputes_when_rules_stale():
    ns = _consolidator_ns()
    df = _txn_df()
    df["merchant_consolidated"] = ["STALE"] * 4
    ns.update({
        "combined_df": df,
        "SKIP_COMBINE": True,
        "CONSOLIDATION_STALE": True,
    })
    _exec_07(ns)

    assert ns["_consolidation_recomputed"] is True
    assert "STALE" not in ns["combined_df"]["merchant_consolidated"].tolist()


def test_07_recomputes_when_column_missing_from_cache():
    ns = _consolidator_ns()
    ns.update({
        "combined_df": _txn_df(),
        "SKIP_COMBINE": True,
        "CONSOLIDATION_STALE": False,
    })
    _exec_07(ns)
    assert ns["_consolidation_recomputed"] is True
    assert "merchant_consolidated" in ns["combined_df"].columns


def test_07_cache_hit_frame_matches_cold_run():
    # Cold run produces the consolidated frame; feeding that frame back as a
    # cache hit must leave it byte-identical.
    ns_cold = _consolidator_ns()
    ns_cold.update({
        "combined_df": _txn_df(),
        "SKIP_COMBINE": False,
        "CONSOLIDATION_STALE": False,
    })
    _exec_07(ns_cold)
    cold = ns_cold["combined_df"].copy()

    ns_hit = _consolidator_ns()
    ns_hit.update({
        "combined_df": cold.copy(),
        "SKIP_COMBINE": True,
        "CONSOLIDATION_STALE": False,
    })
    _exec_07(ns_hit)

    pd.testing.assert_frame_equal(ns_hit["combined_df"], cold)


# ---------------------------------------------------------------------------
# 09 gating
# ---------------------------------------------------------------------------

def _exec_09_merge_head(ns: dict) -> dict:
    # Everything through the business/personal split; stops before the
    # datetime/year_month/cache-save tail, which needs the full namespace.
    head = _ODD_MERGE.read_text(encoding="utf-8").split(
        "# CREATE YEAR_MONTH COLUMN"
    )[0]
    exec(compile(head, str(_ODD_MERGE), "exec"), ns)  # noqa: S102
    return ns


def _merge_fixture(tmp_path, odd_older_than_cache: bool):
    cache = tmp_path / "1192_combined_cache.parquet"
    cache.write_text("cache")
    cache_mtime = cache.stat().st_mtime
    odd_mtime = cache_mtime - 100 if odd_older_than_cache else cache_mtime + 100

    combined_df = pd.DataFrame({
        "merchant_name": ["A", "B"],
        "primary_account_num": ["111", "222"],
        "transaction_date": ["01/05/2026", "01/06/2026"],
        "business_flag": ["Yes", "No"],  # as loaded from cache
    })
    rewards_df = pd.DataFrame({
        "Acct Number": ["111", "222"],
        "Business?": ["No", "No"],  # ODD now disagrees with the cache
    })
    return {
        "pd": pd,
        "combined_df": combined_df,
        "rewards_df": rewards_df,
        "SKIP_COMBINE": True,
        "PARQUET_CACHE": cache,
        "ODD_MTIME": odd_mtime,
    }


def test_09_reuses_cached_merge_when_odd_unchanged(tmp_path):
    ns = _merge_fixture(tmp_path, odd_older_than_cache=True)
    _exec_09_merge_head(ns)
    assert ns["_cached_merge_ok"] is True
    # Cached flags kept -- the disagreeing ODD is IGNORED because it predates
    # the cache (identical inputs would produce identical output).
    assert ns["combined_df"]["business_flag"].tolist() == ["Yes", "No"]
    assert len(ns["business_df"]) == 1
    assert len(ns["personal_df"]) == 1


def test_09_remerges_when_odd_newer_than_cache(tmp_path):
    ns = _merge_fixture(tmp_path, odd_older_than_cache=False)
    _exec_09_merge_head(ns)
    assert ns["_cached_merge_ok"] is False
    # The newer ODD wins: both accounts are now personal.
    assert ns["combined_df"]["business_flag"].tolist() == ["No", "No"]
    assert len(ns["business_df"]) == 0
    assert len(ns["personal_df"]) == 2


def test_09_remerges_when_odd_mtime_unknown(tmp_path):
    ns = _merge_fixture(tmp_path, odd_older_than_cache=True)
    ns["ODD_MTIME"] = None
    _exec_09_merge_head(ns)
    assert ns["_cached_merge_ok"] is False
    assert ns["combined_df"]["business_flag"].tolist() == ["No", "No"]


def test_09_remerges_on_cold_run(tmp_path):
    ns = _merge_fixture(tmp_path, odd_older_than_cache=True)
    ns["SKIP_COMBINE"] = False
    _exec_09_merge_head(ns)
    assert ns["_cached_merge_ok"] is False
    assert ns["combined_df"]["business_flag"].tolist() == ["No", "No"]
