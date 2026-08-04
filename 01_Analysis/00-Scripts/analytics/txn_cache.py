"""Freshness helpers for the TXN combined-data Parquet cache.

Loaded by file path from txn_setup/02-file-config.py (same pattern as
txn_file_detection.py), so this module must stay dependency-free and
side-effect-free.
"""

from __future__ import annotations

import os
from pathlib import Path


def local_cache_root() -> Path:
    """Machine-local root for derived artifacts (parquet caches, sidecars).

    The M: share moves at ~1.7 MB/s on the work machine (issue #251), so
    derived files stored there make even "cache hits" re-stream hundreds of
    MB over the network. Everything under this root is a disposable
    accelerator -- deleting it costs a rebuild, never data. M: remains the
    source of truth for raw inputs.

    Override with ARS_LOCAL_CACHE_DIR. Defaults: %LOCALAPPDATA%\\ARS-cache
    on Windows, ~/.ars-cache elsewhere.
    """
    override = os.environ.get("ARS_LOCAL_CACHE_DIR")
    if override:
        return Path(override)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "ARS-cache"
    return Path.home() / ".ars-cache"


def file_cache_path(kind: str, client_id, src, suffix: str) -> Path | None:
    """Keyed local-cache path for a derived copy of src, or None if src is gone.

    Key = source name + int(mtime) + size, embedded in the filename so a
    re-delivered source file misses the old key and triggers a rebuild.
    Layout: <root>/<kind>/<client_id>/<name>.<mtime>.<size><suffix>
    """
    src = Path(src)
    try:
        stat = src.stat()
    except OSError:
        return None
    return (
        local_cache_root() / kind / str(client_id)
        / f"{src.name}.{int(stat.st_mtime)}.{stat.st_size}{suffix}"
    )


def prune_stale_keys(target: Path, src_name: str) -> None:
    """Delete siblings of target caching older keys of the same source file."""
    try:
        for old in target.parent.glob(f"{src_name}.*"):
            if old != target:
                old.unlink(missing_ok=True)
    except OSError:
        pass


def combined_cache_paths(client_id, client_path) -> tuple[Path, Path]:
    """(save_target, read_source) for a client's combined-data parquet cache.

    Saves always go to the local root. Reads prefer the local copy; when it
    doesn't exist yet but the pre-local-tier cache next to the TXN files on
    the share does, that legacy copy is read one last time (migration) --
    the next save lands locally and takes over.
    """
    local = local_cache_root() / "txn-combined" / f"{client_id}_combined_cache.parquet"
    legacy = Path(client_path) / f"{client_id}_combined_cache.parquet"
    read = legacy if (not local.exists() and legacy.exists()) else local
    return local, read


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
