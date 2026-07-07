"""Stage transaction files from a CSM data dump into ``TXN Files/{CSM}/{client}/``.

Standalone (stdlib + ``month_resolver`` only) so BOTH the formatting run
(``00_Formatting/run.py``) and the analysis run (``01_Analysis`` txn_wrapper)
can call one implementation. The analysis side imports this by file path to
auto-stage TXN files when a run skipped formatting and the destination is empty.

Detection / dedup contract (GitHub issue #45): a TXN file is a ``.txt``/``.csv``
whose name contains ``tran`` (covers ``trans``/``transaction``/``monthlytran``),
or an extensionless name ending in ``_transaction`` (Dan's bracketed-timestamp
files). Files already present with the same name+size are skipped.

``log`` is an injected ``Callable[[str], None]`` (defaults to ``print``) so the
formatting run can route messages through its tee-logger while the analysis run
routes them through loguru.
"""

from __future__ import annotations

import os
import re
import shutil
import zipfile
from pathlib import Path

from month_resolver import resolve_source_month_dir


def gather_trans_files(src_directory, txn_output_base, csm_name,
                       client_filter=None, log=None, clients_config=None):
    """Copy loose transaction files from a source dir into TXN Files.

    Destination: ``{txn_output_base}/{csm_name}/{client_id}/``. Incremental:
    skips files that already exist with the same size. Returns (success, errors).
    """
    if log is None:
        log = print
    if not os.path.exists(src_directory):
        return 0, 0

    # Find transaction files -- 'tran' substring covers all known variants:
    #   coasthills-trans-MMDDYYYY.txt
    #   1441_..._debit card transaction monthly.csv
    #   1562_..._velocity.ars.transactions.YYYY.MM.DD.txt
    #   1585_..._monthly_transaction_data_mls.txt
    #   1795_..._monthlytran.csv
    #   1745_29335_[YYYY.MM.DD][HH.MM.SS]_transaction  (no extension)
    trans_files = []
    for f in os.listdir(src_directory):
        if os.path.isdir(os.path.join(src_directory, f)):
            continue
        f_lower = f.lower()
        is_txn = (
            ('tran' in f_lower and f_lower.endswith(('.txt', '.csv')))
            or f_lower.endswith('_transaction')
        )
        if is_txn:
            # Extract client ID: leading digits before _ or -
            client_match = re.match(r'^(\d+)', f)
            if client_match:
                cid = client_match.group(1)
                # Skip excluded clients
                if clients_config and clients_config.get(cid, {}).get("exclude", False):
                    continue
                if client_filter is None or cid == client_filter:
                    trans_files.append((cid, f))
            else:
                log(f"    Trans SKIPPED (no client ID in filename): {f}")

    if not trans_files:
        log(f"    No transaction files found")
        return 0, 0

    success = 0
    skipped = 0
    errors = 0
    for client_id, filename in trans_files:
        try:
            src_path = os.path.join(src_directory, filename)
            src_size = os.path.getsize(src_path)

            # Destination: TXN Files/{CSM}/{client_id}/
            dest_dir = os.path.join(txn_output_base, csm_name, client_id)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, filename)

            # Skip if same file already exists (same name + same size)
            if os.path.exists(dest_path):
                if os.path.getsize(dest_path) == src_size:
                    skipped += 1
                    continue
                # Different size = updated file, overwrite
                log(f"    Trans: {filename} -- size changed, re-copying")

            shutil.copy2(src_path, dest_path)
            log(f"    Trans: {filename} -> {dest_dir}")
            success += 1
        except Exception as e:
            log(f"    Trans ERROR: {filename}: {e}")
            errors += 1

    if skipped:
        log(f"    Trans: {skipped} file(s) already up to date")

    return success, errors


def gather_trans_from_zips(src_directory, txn_output_base, csm_name,
                           client_filter=None, log=None, clients_config=None):
    """Extract transaction files bundled INSIDE the ODD zips into TXN Files.

    CSM data-dump zips (e.g. 1200_ODDD.zip) carry both the ODD entry and a
    transaction entry; this pulls the transaction entry out and routes it to
    ``TXN Files/{CSM}/{client_id}/`` -- same destination and detection/dedup
    contract as gather_trans_files(). The large ODD member is never decompressed
    (only its metadata is read). Returns (success, errors).
    """
    if log is None:
        log = print
    if not os.path.exists(src_directory):
        return 0, 0

    # Same ODD-zip discovery as process_csm (never modifies the CSM source)
    zip_files = [f for f in os.listdir(src_directory) if f.endswith('.zip')
                 and 'odd' in f.lower()
                 and (client_filter is None or f.startswith(client_filter))]

    success = 0
    skipped = 0
    errors = 0
    for item in zip_files:
        item_path = os.path.join(src_directory, item)
        if not zipfile.is_zipfile(item_path):
            continue

        # Fallback client ID from the zip name (e.g. 1200 from 1200_ODDD.zip)
        zip_client = re.match(r'^(\d+)', item)
        zip_cid = zip_client.group(1) if zip_client else None

        try:
            with zipfile.ZipFile(item_path, 'r') as zip_ref:
                for entry in zip_ref.namelist():
                    if entry.startswith('__MACOSX') or entry.endswith('/'):
                        continue
                    base = os.path.basename(entry)
                    f_lower = base.lower()

                    # ODD wins -- already extracted/formatted by process_csm.
                    # Also resolves an entry matching both 'odd' and 'tran'.
                    if 'odd' in f_lower:
                        continue

                    # Same detection as gather_trans_files
                    is_txn = (
                        ('tran' in f_lower and f_lower.endswith(('.txt', '.csv')))
                        or f_lower.endswith('_transaction')
                    )
                    if not is_txn:
                        continue

                    # Client ID: entry's leading digits, else the zip's client ID
                    entry_match = re.match(r'^(\d+)', base)
                    cid = entry_match.group(1) if entry_match else zip_cid
                    if not cid:
                        log(f"    Trans SKIPPED (no client ID in entry or zip name): {item}!{base}")
                        continue

                    # Skip excluded clients
                    if clients_config and clients_config.get(cid, {}).get("exclude", False):
                        continue
                    if client_filter is not None and cid != client_filter:
                        continue

                    try:
                        src_size = zip_ref.getinfo(entry).file_size

                        # Destination: TXN Files/{CSM}/{client_id}/
                        dest_dir = os.path.join(txn_output_base, csm_name, cid)
                        os.makedirs(dest_dir, exist_ok=True)
                        dest_path = os.path.join(dest_dir, base)

                        # Skip if same file already exists (same name + same size)
                        if os.path.exists(dest_path):
                            if os.path.getsize(dest_path) == src_size:
                                skipped += 1
                                continue
                            # Different size = updated file, overwrite
                            log(f"    Trans (zip): {base} -- size changed, re-copying")

                        with open(dest_path, 'wb') as out_f:
                            out_f.write(zip_ref.read(entry))
                        log(f"    Trans (zip): {item}!{base} -> {dest_dir}")
                        success += 1
                    except Exception as e:
                        log(f"    Trans (zip) ERROR: {item}!{base}: {e}")
                        errors += 1
        except Exception as e:
            log(f"    Trans (zip) ERROR opening {item}: {e}")
            errors += 1

    if skipped:
        log(f"    Trans (zip): {skipped} file(s) already up to date")

    return success, errors


def stage_txn_files(csm, client_id, month, csm_source_root, txn_files_base,
                    clients_config=None, log=None):
    """Stage one client's TXN files from a CSM source dump into TXN Files.

    Mirrors the formatting run's ``--with-trans`` block, as a superset for the
    auto-stage use case: loose files + zip-bundled entries, from both the
    month-specific source folder (resolved tolerantly per issue #220) and the
    CSM root (some clients drop TXN files at the top level). All writes go to
    ``{txn_files_base}/{csm}/{client_id}/``. Idempotent (name+size dedup).

    Returns (staged, errors).
    """
    if log is None:
        log = print

    total_ok, total_err = 0, 0
    src_month = resolve_source_month_dir(csm_source_root, month)
    csm_root = Path(csm_source_root)

    search_dirs: list[Path] = []
    if src_month and Path(src_month).exists():
        search_dirs.append(Path(src_month))
    if csm_root.exists() and Path(csm_root) not in search_dirs:
        search_dirs.append(csm_root)

    for d in search_dirs:
        ok, err = gather_trans_files(str(d), txn_files_base, csm, client_id, log, clients_config)
        total_ok += ok
        total_err += err
        ok, err = gather_trans_from_zips(str(d), txn_files_base, csm, client_id, log, clients_config)
        total_ok += ok
        total_err += err

    return total_ok, total_err
