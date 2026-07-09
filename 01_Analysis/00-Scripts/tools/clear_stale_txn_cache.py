"""Delete stale TXN parquet caches across all clients.

The TXN parquet cache (`<client>_combined_cache.parquet`) is keyed only on
client + raw-file mtimes, so a CODE change that alters how `combined_df` is
built does not invalidate it -- an old-schema cache then crashes new code at
setup ("failed at the first module"). The TXN setup now auto-deletes any cache
older than a cutoff on the next run, but this one-shot sweep clears them all at
once so you don't have to run every client to self-heal.

Usage (dry-run by default -- shows what WOULD be deleted):
    python tools/clear_stale_txn_cache.py
    python tools/clear_stale_txn_cache.py --before 2026-07-09
    python tools/clear_stale_txn_cache.py --base "M:/ARS/00_Formatting/02-Data-Ready for Analysis/TXN Files"
    python tools/clear_stale_txn_cache.py --apply      # actually delete
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

CACHE_GLOB = "*_combined_cache.parquet"

# Same base resolution the TXN setup uses (analytics/txn_setup/02-file-config.py).
_BASE_CANDIDATES = [
    Path(r"M:\ARS") / "00_Formatting" / "02-Data-Ready for Analysis" / "TXN Files",
    Path("/Volumes/M/ARS") / "00_Formatting" / "02-Data-Ready for Analysis" / "TXN Files",
]


def default_base() -> Path:
    for p in _BASE_CANDIDATES:
        if p.exists():
            return p
    return _BASE_CANDIDATES[0]


def find_stale(base: Path, cutoff: datetime) -> list[tuple[Path, datetime, int]]:
    """Return (path, mtime, size_bytes) for every cache under base older than cutoff."""
    out = []
    for f in base.rglob(CACHE_GLOB):
        try:
            st = f.stat()
        except OSError:
            continue
        mt = datetime.fromtimestamp(st.st_mtime)
        if mt < cutoff:
            out.append((f, mt, st.st_size))
    return sorted(out, key=lambda t: t[1])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", type=Path, default=None,
                    help="root folder to scan (default: the TXN Files share)")
    ap.add_argument("--before", default="2026-07-09",
                    help="delete caches built before this date (YYYY-MM-DD, default 2026-07-09)")
    ap.add_argument("--apply", action="store_true",
                    help="actually delete (default is a dry-run preview)")
    args = ap.parse_args()

    base = args.base or default_base()
    try:
        cutoff = datetime.strptime(args.before, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: --before must be YYYY-MM-DD, got {args.before!r}")
        return 2
    if not base.exists():
        print(f"ERROR: base folder does not exist: {base}")
        print("  Pass --base with your TXN Files path.")
        return 2

    stale = find_stale(base, cutoff)
    print(f"Scanning {base}")
    print(f"Cutoff:  caches built before {cutoff:%Y-%m-%d}")
    print("-" * 60)
    if not stale:
        print("No stale caches found. Nothing to do.")
        return 0

    total_mb = sum(sz for _, _, sz in stale) / (1024 * 1024)
    for f, mt, sz in stale:
        print(f"  {mt:%Y-%m-%d}  {sz/(1024*1024):7.0f} MB  {f}")
    print("-" * 60)
    print(f"{len(stale)} stale cache(s), {total_mb:.0f} MB total.")

    if not args.apply:
        print("\nDRY RUN -- nothing deleted. Re-run with --apply to delete them.")
        return 0

    deleted = 0
    for f, _, _ in stale:
        try:
            f.unlink()
            deleted += 1
        except OSError as e:
            print(f"  WARNING: could not delete {f}: {type(e).__name__}: {e}")
    print(f"\nDeleted {deleted}/{len(stale)} cache(s). Next run per client rebuilds fresh.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
