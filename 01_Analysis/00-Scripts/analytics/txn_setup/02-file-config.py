from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
import os
import re
import sys

# ------------------------------------------------------------
# Configuration — loaded from clients_config.json
# ------------------------------------------------------------
# CLIENT_ID must be set before this script runs.
# Options: environment variable, or passed by the pipeline runner.
CLIENT_ID = os.environ.get('CLIENT_ID', '')
if not CLIENT_ID:
    raise ValueError(
        "CLIENT_ID not set. Set the CLIENT_ID environment variable "
        "or pass it via the pipeline runner."
    )

# Load client config to validate CLIENT_ID exists
_config_candidates = [
    Path(__file__).resolve().parents[4] / "03_Config" / "clients_config.json",
    Path(r"M:\ARS\03_Config\clients_config.json"),
    Path("/Volumes/M/ARS/03_Config/clients_config.json"),
]
_clients_config = None
for _cp in _config_candidates:
    if _cp.exists():
        _clients_config = json.loads(_cp.read_text())
        break

if _clients_config and CLIENT_ID not in _clients_config:
    raise ValueError(
        f"CLIENT_ID '{CLIENT_ID}' not found in clients_config.json. "
        f"Available: {list(_clients_config.keys())[:5]}..."
    )

# Base paths — TXN files live in a dedicated folder, separate from ODD
# Structure: 00_Formatting/02-Data-Ready for Analysis/TXN Files/{CSM}/{client_id}/
# TXN files accumulate across months (no month subfolder).
# Year subfolders under client_id are supported but not required.
_ars_base_candidates = [
    Path(r"M:\ARS"),
    Path("/Volumes/M/ARS"),
    Path(__file__).resolve().parents[4],
]
ARS_BASE = next((p for p in _ars_base_candidates if p.exists()), _ars_base_candidates[0])
READY_FOR_ANALYSIS = ARS_BASE / "00_Formatting" / "02-Data-Ready for Analysis"
TXN_BASE = READY_FOR_ANALYSIS / "TXN Files"

# CSM and month from pipeline context (set by txn_wrapper)
CSM = os.environ.get('CSM', '')
MONTH = os.environ.get('MONTH', '')  # Format: YYYY.MM

if CSM:
    CLIENT_PATH = TXN_BASE / CSM / CLIENT_ID
else:
    # Fallback: scan for client folder across all CSM subfolders
    CLIENT_PATH = None
    if TXN_BASE.exists():
        for csm_dir in TXN_BASE.iterdir():
            if not csm_dir.is_dir():
                continue
            candidate = csm_dir / CLIENT_ID
            if candidate.exists():
                CLIENT_PATH = candidate
                CSM = csm_dir.name
                break
    if CLIENT_PATH is None:
        raise FileNotFoundError(
            f"No TXN folder found for client {CLIENT_ID} under {TXN_BASE}. "
            f"Run formatting with --with-trans first to copy TXN files."
        )

# Number of recent months to consider
RECENT_MONTHS = 13


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------
def is_year_folder(path: Path) -> bool:
    """
    Return True if the given path is a 4-digit year folder (e.g., 2025).
    """
    return path.is_dir() and path.name.isdigit() and len(path.name) == 4


def parse_file_date(filepath: Path) -> datetime | None:
    """Extract date from TXN filename. Handles all known naming variants.

    Patterns (see GitHub issue #45):
      coasthills-trans-02282026.txt           → MMDDYYYY at end of stem
      1441_16286_[2026.04.03][07.15.33]_...   → [YYYY.MM.DD] bracketed date
      1562_..._velocity.ars.transactions.2026.04.01.txt → YYYY.MM.DD dotted
      1585_30973_[2023.07.21]_...             → [YYYY.MM.DD] bracketed date
    """
    stem = filepath.stem

    # Pattern 1: bracketed date [YYYY.MM.DD]
    m = re.search(r'\[(\d{4})\.(\d{2})\.(\d{2})\]', stem)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # Pattern 2: dotted date YYYY.MM.DD (e.g., transactions.2026.04.01)
    m = re.search(r'(\d{4})\.(\d{2})\.(\d{2})', stem)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # Pattern 3: trailing MMDDYYYY (e.g., trans-02282026)
    m = re.search(r'(\d{8})$', stem)
    if m:
        try:
            return datetime.strptime(m.group(1), '%m%d%Y')
        except ValueError:
            pass

    return None


# Shared filename detection -- loaded by path so it works both under the
# txn_wrapper exec environment and any standalone use (issue #251: Ascend's
# extensionless '..._monthlydebittransactions' files were silently ignored).
import importlib.util as _importlib_util

_txn_detection_path = Path(__file__).resolve().parent.parent / "txn_file_detection.py"
_txn_detection_spec = _importlib_util.spec_from_file_location(
    "txn_file_detection", _txn_detection_path
)
_txn_detection = _importlib_util.module_from_spec(_txn_detection_spec)
_txn_detection_spec.loader.exec_module(_txn_detection)


def _is_txn_file(p: Path) -> bool:
    """A TXN file by name -- see txn_file_detection.is_txn_dest_file."""
    return _txn_detection.is_txn_dest_file(p)


def gather_all_txn_files(client_root: Path) -> list[Path]:
    """Gather all TXN files from client folder.

    Handles both layouts:
      - Year subfolders: {client_id}/2025/*.txt, {client_id}/2026/*.csv
      - Flat: {client_id}/*.txt, {client_id}/*.csv
    """
    if not client_root.exists():
        raise FileNotFoundError(f"Client root path not found: {client_root}")

    all_files: list[Path] = []

    for item in client_root.iterdir():
        if _is_txn_file(item):
            all_files.append(item)
        elif item.is_dir() and item.name.isdigit() and len(item.name) == 4:
            # Year folder
            for f in item.iterdir():
                if _is_txn_file(f):
                    all_files.append(f)

    return all_files


# ------------------------------------------------------------
# Main logic
# ------------------------------------------------------------
import shutil
import tempfile

# Cache-path + freshness helpers, loaded by file path so they work under the
# txn_wrapper exec environment and standalone use alike.
import importlib.util as _importlib_util

_txn_cache_path = Path(__file__).resolve().parent.parent / "txn_cache.py"
_txn_cache_spec = _importlib_util.spec_from_file_location("txn_cache", _txn_cache_path)
_txn_cache = _importlib_util.module_from_spec(_txn_cache_spec)
_txn_cache_spec.loader.exec_module(_txn_cache)

TRAILING_MONTHS = 12
# PARQUET_CACHE is the SAVE target (machine-local SSD -- see txn_cache.
# local_cache_root); _ACTIVE_CACHE is where this run READS from, which can be
# the legacy copy next to the TXN files on the share exactly once (migration).
# 09-oddd-account-type saves to PARQUET_CACHE and gates its ODD re-merge on it.
PARQUET_CACHE, _ACTIVE_CACHE = _txn_cache.combined_cache_paths(CLIENT_ID, CLIENT_PATH)
if _ACTIVE_CACHE != PARQUET_CACHE:
    print(f"Note: migrating combined cache off the network share -- reading "
          f"{_ACTIVE_CACHE} one last time; future saves go to {PARQUET_CACHE.parent}")
USE_PARQUET_CACHE = None  # set below if cache is fresh

# 1) Gather all TXN files (handles year folders or flat layout)
all_files = gather_all_txn_files(CLIENT_PATH)

# 2) Define the trailing 12-month window.
# Anchor to the REPORT month (namespace MONTH, "2026.06"), not the wall
# clock: a 2026.06 deck re-run in August must select the same file set it
# selected in July, or every L12M aggregate changes with the run date. The
# window is [first of month after report - 12mo, first of month after
# report) -- for 2026.06 that is 2025-07-01..2026-07-01, matching what an
# on-time run always produced. Wall clock remains the fallback when MONTH
# is absent (standalone notebook use).
_report_month = str(globals().get("MONTH") or "")
try:
    _rm_year, _rm_mon = (int(x) for x in _report_month.split("."))
    window_end = datetime(_rm_year, _rm_mon, 1) + relativedelta(months=1)
except (ValueError, TypeError):
    now = datetime.now()
    window_end = datetime(now.year, now.month, 1)
    print(f"  NOTE: no report month in namespace -- anchoring the trailing "
          f"window to today ({window_end:%Y-%m}); re-runs may select "
          f"different files")
window_start = window_end - relativedelta(months=TRAILING_MONTHS)

# 3) Classify files: parse dates, filter to trailing window
dated_files: list[tuple[Path, datetime]] = []
unparsed_files: list[Path] = []

for f in all_files:
    file_date = parse_file_date(f)
    if file_date is None:
        unparsed_files.append(f)
    else:
        dated_files.append((f, file_date))

# 4) Sort by date descending, keep only files within trailing window.
# The upper bound matters for late re-runs: without it, a July file delivered
# early would silently join an August re-run of the June deck.
dated_files.sort(key=lambda x: x[1], reverse=True)
recent_files = [f for f, d in dated_files if window_start <= d < window_end]
older_files = [f for f, d in dated_files if d < window_start or d >= window_end]

# 5) Include unparsed files (can't determine date -- safer to include)
files_to_load = recent_files + unparsed_files

# 6) Check Parquet cache -- if it's newer than ALL TXN files, skip file reading.
# The single most impactful speedup: the first run spends ~26 minutes reading
# 14+ TXN files off the M: network share; subsequent runs load the cached
# .parquet in seconds. Every branch of this decision prints a status line so
# users can tell at a glance why a given run is slow.
# Force a rebuild when TXN_FORCE_REBUILD is set. The cache is keyed only on
# client + file mtimes, so after a CODE change to how combined_df is built
# (05-combine-data / 09-oddd-account-type) it still reads "fresh" and silently
# serves stale data. run_module sets this on the single-module path so
# iterating on a fix always reloads; operators can set it by hand too.
_force_rebuild = bool(os.environ.get("TXN_FORCE_REBUILD"))

# Auto-invalidate caches built before this cutoff. The cache key is only
# client+file-mtimes, so a CODE change to how combined_df is built does NOT
# invalidate it -- an old-schema cache then crashes new code at setup ("failed
# at the first module"). Any cache older than the cutoff is deleted and rebuilt
# fresh, self-healing every client on its next run. Bump the date (or set
# TXN_CACHE_MIN_DATE=YYYY-MM-DD) after a change that alters combined_df's schema.
_cache_min_str = os.environ.get("TXN_CACHE_MIN_DATE", "2026-07-09")
try:
    _CACHE_MIN_DATE = datetime.strptime(_cache_min_str, "%Y-%m-%d")
except ValueError:
    _CACHE_MIN_DATE = datetime(2026, 7, 9)

print()
print("-" * 60)
print("PARQUET CACHE STATUS")
print("-" * 60)
if not _ACTIVE_CACHE.exists():
    print(f"  Status: NO CACHE (will be built during this run)")
    print(f"  Location: {PARQUET_CACHE}")
    print(f"  Note: first run for this client is slow; subsequent runs are fast.")
elif _ACTIVE_CACHE.stat().st_mtime < _CACHE_MIN_DATE.timestamp():
    # Pre-cutoff cache: built by older code, may not match the current schema.
    _stale_dt = datetime.fromtimestamp(_ACTIVE_CACHE.stat().st_mtime)
    print(f"  Status: STALE (built {_stale_dt:%Y-%m-%d} before cutoff "
          f"{_CACHE_MIN_DATE:%Y-%m-%d} -- deleting and rebuilding)")
    try:
        _ACTIVE_CACHE.unlink()
    except OSError as _e:
        print(f"  WARNING: could not delete stale cache: {type(_e).__name__}: {_e}")
    # USE_PARQUET_CACHE stays None -> rebuild from source this run.
elif _force_rebuild:
    print(f"  Status: FORCE-REBUILD (TXN_FORCE_REBUILD set -- ignoring cache)")
    print(f"  Cache:  {_ACTIVE_CACHE.name} (will be overwritten)")
elif not files_to_load:
    # Cache exists but no raw files -- rely on cache
    USE_PARQUET_CACHE = _ACTIVE_CACHE
    _cache_mtime = _ACTIVE_CACHE.stat().st_mtime
    print(f"  Status: HIT (no raw TXN files found; using cache)")
    print(f"  Cache:  {_ACTIVE_CACHE}")
    print(f"  Date:   {datetime.fromtimestamp(_cache_mtime):%Y-%m-%d %H:%M}")
else:
    _cache_mtime = _ACTIVE_CACHE.stat().st_mtime
    _newest_file_mtime = max(f.stat().st_mtime for f in files_to_load)
    # Prefer the exact input-set manifest when the cache has one: it catches
    # the two silent-stale paths the mtime rule can't -- a deleted input
    # (cache still "newer than everything") and an mtime-preserving
    # re-delivery (copy2/robocopy keep source mtimes). Legacy caches without
    # a manifest fall back to the mtime rule; the next save writes one.
    _inputs_match = _txn_cache.input_set_matches(_ACTIVE_CACHE, files_to_load)
    if _inputs_match is True:
        USE_PARQUET_CACHE = _ACTIVE_CACHE
        _age_hours = (datetime.now().timestamp() - _cache_mtime) / 3600
        _cache_mb = _ACTIVE_CACHE.stat().st_size / (1024 * 1024)
        print(f"  Status: HIT (input file set unchanged; skipping file read)")
        print(f"  Cache:  {_ACTIVE_CACHE} ({_cache_mb:.0f} MB)")
        print(f"  Date:   {datetime.fromtimestamp(_cache_mtime):%Y-%m-%d %H:%M} ({_age_hours:.1f}h old)")
    elif _inputs_match is False:
        print(f"  Status: MISS (input file set changed -- files added, removed, "
              f"or replaced since the cache was built; rebuilding)")
    elif _cache_mtime > _newest_file_mtime:
        USE_PARQUET_CACHE = _ACTIVE_CACHE
        _age_hours = (datetime.now().timestamp() - _cache_mtime) / 3600
        _cache_mb = _ACTIVE_CACHE.stat().st_size / (1024 * 1024)
        print(f"  Status: HIT (skipping file read, saving ~25 min)")
        print(f"  Cache:  {_ACTIVE_CACHE} ({_cache_mb:.0f} MB)")
        print(f"  Date:   {datetime.fromtimestamp(_cache_mtime):%Y-%m-%d %H:%M} ({_age_hours:.1f}h old)")
        print(f"  Note:   pre-manifest cache (mtime rule) -- next rebuild "
              f"records the exact input set")
    else:
        _newest_file_dt = datetime.fromtimestamp(_newest_file_mtime)
        _cache_dt = datetime.fromtimestamp(_cache_mtime)
        print(f"  Status: MISS (newer TXN files present -- rebuilding)")
        print(f"  Cache date:   {_cache_dt:%Y-%m-%d %H:%M}")
        print(f"  Newest file:  {_newest_file_dt:%Y-%m-%d %H:%M}")

# Consolidation-logic staleness: the cached merchant_consolidated column bakes
# in the rules from 06/07. If either script changed after the cache was
# written, 07 recomputes on this run even though the data itself is a HIT
# (cheap: the consolidator runs once per distinct merchant). 09 then rewrites
# the cache so the next run is a clean HIT again.
CONSOLIDATION_STALE = False
if USE_PARQUET_CACHE is not None:
    _stale_src = _txn_cache.consolidation_stale(
        USE_PARQUET_CACHE,
        [
            Path(__file__).resolve().parent / "06-merchant-name-consolidation.py",
            Path(__file__).resolve().parent / "07-consolidation-summary.py",
        ],
    )
    if _stale_src:
        CONSOLIDATION_STALE = True
        print(f"  Note: {_stale_src} changed after the cache was written --")
        print(f"        merchant consolidation will be recomputed this run")
print("-" * 60)
print()

# TXN files are read directly from the network share.
# The Parquet cache (above) is the real speed optimization -- after the first
# run, subsequent runs load from cache in seconds instead of re-reading.
LOCAL_TXN_DIR = None

# ------------------------------------------------------------
# Summary output
# ------------------------------------------------------------
print(f"Client path:         {CLIENT_PATH}")
print(f"Total files found:   {len(all_files)}")
print(f"Trailing window:     {window_start:%Y-%m-%d} to {first_of_current_month:%Y-%m-%d} ({TRAILING_MONTHS} months)")
print(f"Recent files:        {len(recent_files)}")
print(f"Older (excluded):    {len(older_files)}")

if unparsed_files:
    print(f"WARNING: {len(unparsed_files)} file(s) with unparsed dates (included by default):")
    for u in unparsed_files:
        print(f"  {u.name}")

if not files_to_load and USE_PARQUET_CACHE is None:
    print(f"WARNING: No TXN files found for trailing {TRAILING_MONTHS} months")
