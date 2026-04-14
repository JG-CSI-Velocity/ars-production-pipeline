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

FILE_EXTENSION = 'txt'  # Set to 'txt' or 'csv' based on actual files

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
        if item.is_file() and item.suffix.lower() in ('.txt', '.csv'):
            all_files.append(item)
        elif item.is_dir() and item.name.isdigit() and len(item.name) == 4:
            # Year folder
            for f in item.iterdir():
                if f.is_file() and f.suffix.lower() in ('.txt', '.csv'):
                    all_files.append(f)

    return all_files


# ------------------------------------------------------------
# Main logic
# ------------------------------------------------------------
TRAILING_MONTHS = 12

# 1) Gather all TXN files (handles year folders or flat layout)
all_files = gather_all_txn_files(CLIENT_PATH)

# 2) Define the trailing 12-month window
now = datetime.now()
first_of_current_month = datetime(now.year, now.month, 1)
window_start = first_of_current_month - relativedelta(months=TRAILING_MONTHS)

# 3) Classify files: parse dates, filter to trailing window
dated_files: list[tuple[Path, datetime]] = []
unparsed_files: list[Path] = []

for f in all_files:
    file_date = parse_file_date(f)
    if file_date is None:
        unparsed_files.append(f)
    else:
        dated_files.append((f, file_date))

# 4) Sort by date descending, keep only files within trailing window
dated_files.sort(key=lambda x: x[1], reverse=True)
recent_files = [f for f, d in dated_files if d >= window_start]
older_files = [f for f, d in dated_files if d < window_start]

# 5) Include unparsed files (can't determine date -- safer to include)
# These will show a warning so JG can investigate naming.
files_to_load = recent_files + unparsed_files

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

if not files_to_load:
    print(f"WARNING: No TXN files found for trailing {TRAILING_MONTHS} months")
