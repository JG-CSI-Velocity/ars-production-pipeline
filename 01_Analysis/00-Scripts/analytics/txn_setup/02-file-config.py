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

# Base paths — TXN files live alongside ODD files
# Structure: 00_Formatting/02-Data-Ready for Analysis/{CSM}/{YYYY.MM}/{client_id}/
_ars_base_candidates = [
    Path(r"M:\ARS"),
    Path("/Volumes/M/ARS"),
    Path(__file__).resolve().parents[4],
]
ARS_BASE = next((p for p in _ars_base_candidates if p.exists()), _ars_base_candidates[0])
BASE_PATH = ARS_BASE / "00_Formatting" / "02-Data-Ready for Analysis"

# CSM and month must be provided or discovered
CSM = os.environ.get('CSM', '')
MONTH = os.environ.get('MONTH', '')  # Format: YYYY.MM

if CSM and MONTH:
    CLIENT_PATH = BASE_PATH / CSM / MONTH / CLIENT_ID
else:
    # Fallback: scan for client folder across all CSM/month combos
    CLIENT_PATH = None
    if BASE_PATH.exists():
        for csm_dir in BASE_PATH.iterdir():
            if not csm_dir.is_dir():
                continue
            for month_dir in csm_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                candidate = month_dir / CLIENT_ID
                if candidate.exists():
                    CLIENT_PATH = candidate
                    CSM = csm_dir.name
                    MONTH = month_dir.name
                    break
            if CLIENT_PATH:
                break
    if CLIENT_PATH is None:
        CLIENT_PATH = BASE_PATH  # will fail gracefully downstream

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
    """
    Extract the date from filenames ending in 'trans-MMDDYYYY'.
    Example: 'coasthills-trans-02282026.txt' -> 2026-02-28
    """
    match = re.search(r'trans-(\d{8})$', filepath.stem)
    if match:
        return datetime.strptime(match.group(1), '%m%d%Y')
    return None


def get_client_year_folders(client_root: Path) -> list[Path]:
    """
    Return a list of all year folders (e.g., 2025, 2026) under the client root.
    """
    if not client_root.exists():
        raise FileNotFoundError(f"Client root path not found: {client_root}")
    return [p for p in client_root.iterdir() if is_year_folder(p)]


def gather_all_files(year_folders: list[Path], extension: str) -> list[Path]:
    """
    Gather all files with the given extension across all year folders.
    """
    all_files: list[Path] = []
    pattern = f"*.{extension}"
    for year_path in year_folders:
        all_files.extend(year_path.glob(pattern))
    return all_files


# ------------------------------------------------------------
# Main logic
# ------------------------------------------------------------
# 1) Discover year folders
year_folders = get_client_year_folders(CLIENT_PATH)

# 2) Gather all files across all year folders using configured extension
all_files = gather_all_files(year_folders, FILE_EXTENSION)

# 3) Define the recent-month window (last RECENT_MONTHS completed months)
now = datetime.now()
first_of_current_month = datetime(now.year, now.month, 1)
start_window = first_of_current_month - relativedelta(months=RECENT_MONTHS)
end_window = first_of_current_month - relativedelta(days=1)

# 4) Classify files by whether we can parse a date from the filename
dated_files: list[tuple[Path, datetime]] = []
unparsed_files: list[Path] = []

for f in all_files:
    file_date = parse_file_date(f)
    if file_date is None:
        unparsed_files.append(f)
    else:
        dated_files.append((f, file_date))

# 5) Sort dated files by date descending
dated_files.sort(key=lambda x: x[1], reverse=True)

# 6) Split into recent and older sets (by count, not by date range)
recent_files = [f for f, _ in dated_files[:RECENT_MONTHS]]
older_files = [f for f, _ in dated_files[RECENT_MONTHS:]]

# ------------------------------------------------------------
# Summary output
# ------------------------------------------------------------
print(f"Client path:         {CLIENT_PATH}")
print(f"Year folders found:  {sorted([p.name for p in year_folders])}")
print(f"File extension:      .{FILE_EXTENSION}")
print(f"Total files:         {len(all_files)}")
print(
    f"Recent ({RECENT_MONTHS} files): "
    f"{len(recent_files)}  ({start_window:%Y-%m-%d} to {end_window:%Y-%m-%d})"
)
print(f"Older files:         {len(older_files)}")

if unparsed_files:
    print(f"WARNING: Unparsed filenames (no trans-MMDDYYYY in stem): {len(unparsed_files)}")
    for u in unparsed_files:
        print(f"  {u.name}")
