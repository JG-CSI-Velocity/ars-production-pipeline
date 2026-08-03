"""Freshness helpers for the TXN combined-data Parquet cache.

Loaded by file path from txn_setup/02-file-config.py (same pattern as
txn_file_detection.py), so this module must stay dependency-free and
side-effect-free.
"""

from __future__ import annotations

from pathlib import Path


def consolidation_stale(cache_path, logic_sources) -> str | None:
    """Name of the first logic source modified after the cache was written.

    The cached ``merchant_consolidated`` column bakes in the rules from the
    consolidation scripts; if one of them changed after the cache was saved,
    the cached column is outdated and must be recomputed even on a data HIT.
    Returns None when the cache is missing (nothing to be stale relative to)
    or every source predates the cache. An unreadable source counts as stale
    -- forcing a recompute is the safe direction.
    """
    try:
        cache_mtime = Path(cache_path).stat().st_mtime
    except OSError:
        return None
    for src in logic_sources:
        src = Path(src)
        try:
            if src.stat().st_mtime > cache_mtime:
                return src.name
        except OSError:
            return src.name
    return None
