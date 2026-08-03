"""Single source of truth for recognizing transaction data files by name.

Used by the analysis loader (txn_setup/02-file-config.py), the diagnostic
script, and 00_Formatting/run.py (loaded there by file path, so this module
must stay dependency-free and side-effect-free).

Naming variants in the wild (issues #45 and #251):
    coasthills-trans-MMDDYYYY.txt
    1441_..._debit card transaction monthly.csv
    1562_..._velocity.ars.transactions.YYYY.MM.DD.txt
    1745_29335_[YYYY.MM.DD][HH.MM.SS]_transaction        (no extension)
    1192_35687_[YYYY.MM.DD][HH.MM.SS]_monthlydebittransactions  (no extension)
    1192_30938_[YYYY.MM.DD][HH.MM.SS]_184202             (renamed, no 'tran')

Two levels of matching:
- is_txn_filename: conservative, for scanning CSM data-dump folders where
  ODDs, zips, and unrelated files coexist. Requires transaction-ish naming.
- is_txn_dest_file: permissive, for the curated TXN Files/{CSM}/{client}/
  destination where everything is transaction data by construction. Also
  accepts Velocity-export-shaped names with no 'tran' in them (renamed files).
"""

from __future__ import annotations

import re
from pathlib import Path

# Extensions that are never transaction data, wherever they appear.
NON_DATA_EXTENSIONS = ('.zip', '.xlsx', '.xls', '.parquet', '.pdf', '.json', '.log')

# Velocity export naming: {client}_{batch}_[YYYY.MM.DD]... at the start.
_VELOCITY_EXPORT_RE = re.compile(r'^\d+_\d+_\[\d{4}\.\d{2}\.\d{2}\]')

# Longest real extension we expect ('.txt', '.csv', '.dat', ...). Longer or
# non-alphanumeric tails after the last dot come from bracketed timestamps in
# extensionless names, e.g. '...[10.03.04]_monthlydebittransactions'.
_MAX_REAL_EXTENSION_LEN = 4


def _has_real_extension(name_lower: str) -> bool:
    if '.' not in name_lower:
        return False
    tail = name_lower.rsplit('.', 1)[-1]
    return tail.isalnum() and len(tail) <= _MAX_REAL_EXTENSION_LEN


def is_txn_filename(name: str) -> bool:
    """True if a filename looks like transaction data (dump-side, conservative).

    Matches .txt/.csv files with 'tran' anywhere in the name, and extensionless
    files ending in 'transaction'/'transactions' or containing 'tran'.
    """
    f_lower = name.lower()
    if f_lower.endswith(NON_DATA_EXTENSIONS):
        return False
    if f_lower.endswith(('_transaction', 'transactions')):
        return True
    if 'tran' not in f_lower:
        return False
    if f_lower.endswith(('.txt', '.csv')):
        return True
    return not _has_real_extension(f_lower)


def is_txn_dest_file(path: Path) -> bool:
    """True if a file in TXN Files/{CSM}/{client}/ is transaction data.

    Permissive: everything in the destination folder is transaction data by
    construction, so besides is_txn_filename this also accepts .txt/.csv
    without 'tran' in the name and Velocity-export-shaped names (covers files
    renamed on delivery, e.g. '1192_30938_[2026.02.05][14.22.13]_184202').
    """
    if not path.is_file():
        return False
    f_lower = path.name.lower()
    if f_lower.endswith(NON_DATA_EXTENSIONS):
        return False
    if f_lower.endswith(('.txt', '.csv')):
        return True
    return is_txn_filename(path.name) or bool(_VELOCITY_EXPORT_RE.match(path.name))
