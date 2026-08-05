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


def input_manifest_path(cache_path) -> Path:
    """Sidecar recording exactly which input files a combined cache baked in."""
    p = Path(cache_path)
    return p.with_name(p.name + ".inputs.json")


def save_input_manifest(cache_path, files) -> None:
    """Record {name: [size, int(mtime)]} of the inputs a cache was built from.

    Written atomically next to the cache. Failures are non-fatal: a missing
    manifest just downgrades freshness checking to the legacy mtime rule.
    """
    import json
    import uuid

    entries = {}
    for f in files:
        try:
            st = Path(f).stat()
        except OSError:
            continue
        entries[Path(f).name] = [st.st_size, int(st.st_mtime)]
    target = input_manifest_path(cache_path)
    try:
        tmp = target.with_suffix(f".{uuid.uuid4().hex[:8]}.tmp")
        tmp.write_text(json.dumps(entries, indent=0), encoding="utf-8")
        tmp.replace(target)
    except OSError:
        pass


def input_set_matches(cache_path, files):
    """Compare the cache's recorded input set against the current files.

    Returns True (exact match), False (set or any size/mtime changed), or
    None when no manifest exists (legacy cache -- caller falls back to the
    mtime-only rule). Catches the two silent-stale paths the mtime rule
    misses: a deleted input (cache still 'newer than everything') and an
    mtime-preserving re-delivery (copy2/robocopy keep source mtimes).
    """
    import json

    target = input_manifest_path(cache_path)
    if not target.exists():
        return None
    try:
        recorded = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    current = {}
    for f in files:
        try:
            st = Path(f).stat()
        except OSError:
            return False  # a listed input is unreadable -- treat as changed
        current[Path(f).name] = [st.st_size, int(st.st_mtime)]
    return current == recorded


def duplicate_file_groups(paths) -> list[list[Path]]:
    """Group byte-identical files: same size AND same head+tail 1 MiB hash.

    A monthly TXN export re-delivered under a new name double-counts a whole
    month everywhere downstream (issue #251: two 1192 files, identical to the
    byte, one relabeled). Size alone could collide, so identical sizes are
    confirmed by hashing the first and last MiB -- cheap even over the
    network. Returns only groups with >1 member, each sorted by name (the
    first entry is the keeper).
    """
    import hashlib

    by_size: dict[int, list[Path]] = {}
    for p in paths:
        p = Path(p)
        try:
            size = p.stat().st_size
        except OSError:
            continue
        by_size.setdefault(size, []).append(p)

    groups: list[list[Path]] = []
    for size, candidates in by_size.items():
        if len(candidates) < 2:
            continue
        by_sig: dict[str, list[Path]] = {}
        for p in candidates:
            try:
                with open(p, 'rb') as fh:
                    digest = hashlib.sha256()
                    digest.update(fh.read(1024 * 1024))
                    if size > 2 * 1024 * 1024:
                        fh.seek(-1024 * 1024, 2)
                        digest.update(fh.read(1024 * 1024))
                sig = digest.hexdigest()
            except OSError:
                continue
            by_sig.setdefault(sig, []).append(p)
        for same in by_sig.values():
            if len(same) > 1:
                groups.append(sorted(same, key=lambda q: q.name))
    return groups


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
