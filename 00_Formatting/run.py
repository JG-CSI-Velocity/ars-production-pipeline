"""Step 1: Format ODD files and gather supporting files.

Reads raw ZIPs/CSVs from the CSM's data dump folder, unzips, converts
to Excel, runs the 7-step formatting, and saves the formatted output
to 02-Data-Ready for Analysis.

Optionally gathers:
- Transaction files from the CSM data dump folder
- Deferred revenue files from the billing folder
- Workbook files from the R: drive

Usage:
    python run.py                                    # current month, all CSMs
    python run.py --month 2026.03                    # specific month
    python run.py --month 2026.03 --csm JamesG       # single CSM only
    python run.py --month 2026.04 --csm JamesG --client 1680
    python run.py --month 2026.04 --csm JamesG --with-trans --with-deferred --with-workbook
"""

import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# Add 00-Scripts to path for shared modules
sys.path.insert(0, str(Path(__file__).parent / "00-Scripts"))

# Config files moved to 03_Config/ (mirrors M:\ARS\ layout)
_config_dir = Path(__file__).resolve().parent.parent / "03_Config"
sys.path.insert(0, str(_config_dir))

import pandas as pd
from settings import load_settings
from shared.format_odd import format_odd


def log_message(message, log_file=None):
    print(message)
    if log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(message + "\n")


def load_ars_config():
    """Load ars_config.json from 03_Config/."""
    candidates = [
        Path(__file__).resolve().parent.parent / "03_Config" / "ars_config.json",
        Path(r"M:\ARS\03_Config\ars_config.json"),
    ]
    for p in candidates:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return {}


def process_csm(csm_name, src_directory, staging_directory, output_directory, log_file=None, client_filter=None, force=False, clients_config=None):
    """Process ODD files for a single CSM.

    1. Copy ZIPs from CSM source to staging (01-Data-Ready for Formatting)
    2. Extract, rename CSVs, convert to Excel in staging
    3. Run 7-step formatting
    4. Save formatted output to output (02-Data-Ready for Analysis)

    Never modifies the CSM source folder.
    If client_filter is set, only process files starting with that client ID.
    """
    if not os.path.exists(src_directory):
        log_message(f"  {csm_name}: Source not found: {src_directory}", log_file)
        return 0, 0

    os.makedirs(staging_directory, exist_ok=True)
    os.makedirs(output_directory, exist_ok=True)

    success_count = 0
    error_count = 0

    # Step 1: Copy ODD ZIPs from CSM source to 01-Data-Ready for Formatting
    # NEVER modifies the CSM source folder
    zip_files = [f for f in os.listdir(src_directory) if f.endswith('.zip')
                 and 'odd' in f.lower()
                 and (client_filter is None or f.startswith(client_filter))]
    if zip_files:
        log_message(f"  {csm_name}: Found {len(zip_files)} ZIP file(s)", log_file)
    else:
        log_message(f"  {csm_name}: No ODD ZIP files found in {src_directory}", log_file)

    for item in zip_files:
        item_path = os.path.join(src_directory, item)
        # Extract client ID from ZIP filename (e.g., 1200 from 1200_ODDD.zip)
        zip_client = re.match(r'^(\d+)', item)
        zip_client_id = zip_client.group(1) if zip_client else 'unknown'

        # Skip excluded clients
        if clients_config and clients_config.get(zip_client_id, {}).get("exclude", False):
            _reason = clients_config[zip_client_id].get("exclude_reason", "excluded")
            log_message(f"    Skipping {zip_client_id} -- {_reason}", log_file)
            continue

        client_staging = os.path.join(staging_directory, zip_client_id)

        # Skip if already extracted (CSV exists in staging) unless --force
        if not force and os.path.exists(client_staging):
            existing_csvs = [f for f in os.listdir(client_staging) if f.endswith('.csv') and 'odd' in f.lower()]
            if existing_csvs:
                log_message(f"    Skipping {item} -- already extracted ({existing_csvs[0]})", log_file)
                continue

        os.makedirs(client_staging, exist_ok=True)

        if zipfile.is_zipfile(item_path):
            with zipfile.ZipFile(item_path, 'r') as zip_ref:
                # Read ODD CSVs from ZIP and write with cleaned name directly
                # No intermediate extract + rename -- avoids Windows file lock issues
                odd_entries = [n for n in zip_ref.namelist()
                               if 'odd' in n.lower() and not n.startswith('__MACOSX')]
                for entry in odd_entries:
                    # Determine final filename: truncate after "ODD"
                    basename = os.path.basename(entry)
                    odd_pos = basename.upper().find('ODD')
                    if odd_pos != -1:
                        final_name = basename[:odd_pos + 3] + '.csv'
                    else:
                        final_name = basename
                    final_path = os.path.join(client_staging, final_name)
                    with open(final_path, 'wb') as out_f:
                        out_f.write(zip_ref.read(entry))
                    log_message(f"    Extracted: {basename} -> {final_name}", log_file)

    # Step 2: Find ODD CSVs across all client subfolders in staging
    csv_files = []
    for client_dir in os.listdir(staging_directory):
        client_path = os.path.join(staging_directory, client_dir)
        if not os.path.isdir(client_path):
            continue
        if client_filter and client_dir != client_filter:
            continue
        for f in os.listdir(client_path):
            if f.endswith('.csv') and 'odd' in f.lower():
                csv_files.append((client_dir, f))

    # Step 3+4: Read CSV, format, write formatted Excel directly to output
    # Skips the intermediate CSV->Excel conversion entirely (avoids OLE issues)
    if csv_files:
        log_message(f"  {csm_name}: Formatting {len(csv_files)} file(s)", log_file)

    for client_id, csv_file in csv_files:
        try:
            # Skip excluded clients
            if clients_config and clients_config.get(client_id, {}).get("exclude", False):
                _reason = clients_config[client_id].get("exclude_reason", "excluded")
                log_message(f"    Skipping {client_id} -- {_reason}", log_file)
                continue

            client_path = os.path.join(staging_directory, client_id)
            csv_path = os.path.join(client_path, csv_file)

            # Skip if already formatted (output Excel exists AND is valid) unless --force
            excel_filename = os.path.splitext(csv_file)[0] + '.xlsx'
            client_output_dir = os.path.join(output_directory, client_id)
            output_path = os.path.join(client_output_dir, excel_filename)
            if not force and os.path.exists(output_path):
                _existing_size = os.path.getsize(output_path)
                if _existing_size > 10000:  # must be > 10KB to be a real Excel file
                    log_message(f"    Skipping {csv_file} -- already formatted ({_existing_size / 1024 / 1024:.1f} MB)", log_file)
                    continue
                else:
                    log_message(f"    Existing output is invalid ({_existing_size} bytes) -- re-formatting", log_file)
                    os.remove(output_path)

            df = pd.read_csv(csv_path, skiprows=4, low_memory=False)

            if df.empty:
                log_message(f"    Skipping empty: {csv_file}", log_file)
                continue

            # Drop first column if it's an index column
            if df.columns[0].startswith("Unnamed") or df.iloc[:, 0].dtype == "int64":
                df = df.drop(columns=[df.columns[0]])

            log_message(f"    Formatting: {csv_file} ({len(df):,} rows, {len(df.columns)} cols)", log_file)

            # Run the canonical 7-step formatting
            df = format_odd(df)

            # Save formatted Excel directly to output
            excel_filename = os.path.splitext(csv_file)[0] + '.xlsx'
            client_output_dir = os.path.join(output_directory, client_id)
            os.makedirs(client_output_dir, exist_ok=True)
            output_path = os.path.join(client_output_dir, excel_filename)

            df.to_excel(output_path, index=False, engine='xlsxwriter')

            final_size = os.path.getsize(output_path) / (1024 * 1024)
            log_message(f"    Done: {excel_filename} ({final_size:.1f} MB) -> {client_output_dir}", log_file)
            success_count += 1

        except Exception as e:
            log_message(f"    ERROR formatting {csv_file}: {e}", log_file)
            error_count += 1

    return success_count, error_count


# ─── EXTRA FILE GATHERING ──────────────────────────────────────────────

def gather_trans_files(src_directory, txn_output_base, csm_name, client_filter=None, log_file=None, clients_config=None):
    """Copy transaction files from CSM data dump into TXN Files folder.

    Destination: 02-Data-Ready for Analysis/TXN Files/{CSM}/{client_id}/
    Detection: .txt/.csv files whose name starts with a client ID and contains
    'tran' anywhere (covers 'trans', 'transaction', 'monthlytran', etc.).
    See GitHub issue #45 for the full naming variation list.
    Incremental: skips files that already exist with the same size.
    """
    if not os.path.exists(src_directory):
        return 0, 0

    # Find transaction files -- 'tran' substring covers all known variants:
    #   coasthills-trans-MMDDYYYY.txt
    #   1441_..._debit card transaction monthly.csv
    #   1562_..._velocity.ars.transactions.YYYY.MM.DD.txt
    #   1585_..._monthly_transaction_data_mls.txt
    #   1795_..._monthlytran.csv
    trans_files = []
    for f in os.listdir(src_directory):
        if os.path.isdir(os.path.join(src_directory, f)):
            continue
        f_lower = f.lower()
        if 'tran' in f_lower and f_lower.endswith(('.txt', '.csv')):
            # Extract client ID: either leading digits before _ or before -
            client_match = re.match(r'^(\d+)', f)
            if client_match:
                cid = client_match.group(1)
                # Skip excluded clients
                if clients_config and clients_config.get(cid, {}).get("exclude", False):
                    continue
                if client_filter is None or cid == client_filter:
                    trans_files.append((cid, f))

    if not trans_files:
        log_message(f"    No transaction files found", log_file)
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
                log_message(f"    Trans: {filename} -- size changed, re-copying", log_file)

            shutil.copy2(src_path, dest_path)
            log_message(f"    Trans: {filename} -> {dest_dir}", log_file)
            success += 1
        except Exception as e:
            log_message(f"    Trans ERROR: {filename}: {e}", log_file)
            errors += 1

    if skipped:
        log_message(f"    Trans: {skipped} file(s) already up to date", log_file)

    return success, errors


def gather_deferred_files(client_ids, deferred_base, output_directory, log_file=None):
    """Copy deferred revenue files for each client.

    Looks in: {deferred_base}/{client_id}*/ARS deferred billing/
    For files containing 'deferred' in the name.
    """
    if not deferred_base or not os.path.exists(deferred_base):
        log_message(f"    Deferred base not found: {deferred_base}", log_file)
        return 0, 0

    success = 0
    errors = 0
    for client_id in client_ids:
        try:
            # Find client folder (format: #### Client Name)
            client_folders = [f for f in os.listdir(deferred_base) if f.startswith(client_id)]
            if not client_folders:
                continue

            deferred_path = os.path.join(deferred_base, client_folders[0], "ARS deferred billing")
            if not os.path.exists(deferred_path):
                continue

            deferred_files = [f for f in os.listdir(deferred_path)
                              if 'deferred' in f.lower() and f.endswith(('.xlsx', '.xls'))]
            if not deferred_files:
                continue

            dest_dir = os.path.join(output_directory, client_id)
            os.makedirs(dest_dir, exist_ok=True)
            src_file = os.path.join(deferred_path, deferred_files[0])
            dest_file = os.path.join(dest_dir, deferred_files[0])

            if os.path.exists(dest_file):
                log_message(f"    Deferred: {client_id} -- already exists, skipping", log_file)
                continue

            shutil.copy2(src_file, dest_file)
            log_message(f"    Deferred: {deferred_files[0]} -> {dest_dir}", log_file)
            success += 1
        except Exception as e:
            log_message(f"    Deferred ERROR {client_id}: {e}", log_file)
            errors += 1

    return success, errors


def gather_workbook_files(client_ids, workbook_base, csm_folder_name, month, output_directory, log_file=None):
    """Copy workbook files from R: drive for each client.

    Looks in: {workbook_base}/{month}/{csm_folder_name}/
    For files matching: {client_id}-*workbook*.xlsx
    """
    workbook_source = os.path.join(workbook_base, month, csm_folder_name)
    if not os.path.exists(workbook_source):
        log_message(f"    Workbook source not found: {workbook_source}", log_file)
        return 0, 0

    success = 0
    errors = 0
    for client_id in client_ids:
        try:
            workbook_files = [f for f in os.listdir(workbook_source)
                              if f.startswith(f"{client_id}-") and 'workbook' in f.lower() and f.endswith('.xlsx')]
            if not workbook_files:
                continue

            dest_dir = os.path.join(output_directory, client_id)
            os.makedirs(dest_dir, exist_ok=True)
            src_file = os.path.join(workbook_source, workbook_files[0])
            dest_file = os.path.join(dest_dir, workbook_files[0])

            if os.path.exists(dest_file):
                log_message(f"    Workbook: {client_id} -- already exists, skipping", log_file)
                continue

            shutil.copy2(src_file, dest_file)
            log_message(f"    Workbook: {workbook_files[0]} -> {dest_dir}", log_file)
            success += 1
        except Exception as e:
            log_message(f"    Workbook ERROR {client_id}: {e}", log_file)
            errors += 1

    return success, errors


# ─── MAIN ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Step 1: Format ODD files and gather supporting files")
    parser.add_argument("--month", type=str, default=None,
                        help="Target month in YYYY.MM format (default: current month)")
    parser.add_argument("--csm", type=str, default=None,
                        help="Process only this CSM (default: all)")
    parser.add_argument("--client", type=str, default=None,
                        help="Process only this client ID (default: all)")
    parser.add_argument("--force", action="store_true",
                        help="Re-process even if output already exists")
    parser.add_argument("--config", type=str, default=None,
                        help="Path to ars_config.json")
    parser.add_argument("--with-trans", action="store_true",
                        help="Also copy transaction files from data dump into client folders")
    parser.add_argument("--with-deferred", action="store_true",
                        help="Also copy deferred revenue files into client folders")
    parser.add_argument("--with-workbook", action="store_true",
                        help="Also copy workbook files from R: drive into client folders")
    parser.add_argument("--with-all", action="store_true",
                        help="Gather all extra files (trans + deferred + workbook)")
    parser.add_argument("--parallel", type=int, default=1,
                        help="Number of clients to format in parallel (default: 1, sequential)")
    args = parser.parse_args()

    month = args.month or datetime.now().strftime("%Y.%m")

    # TXN file gathering is always on -- no flag needed.
    # CSMs run this from the UI which doesn't pass --with-trans.
    args.with_trans = True

    # Shortcut: --with-all enables deferred + workbook
    if args.with_all:
        args.with_deferred = True
        args.with_workbook = True

    print()
    print("=" * 70)
    print("  STEP 1: FORMAT ODD FILES")
    print(f"  Month:  {month}")
    if args.csm:
        print(f"  CSM:    {args.csm}")
    if args.client:
        print(f"  Client: {args.client}")
    extras = []
    if args.with_trans:
        extras.append("trans")
    if args.with_deferred:
        extras.append("deferred")
    if args.with_workbook:
        extras.append("workbook")
    if extras:
        print(f"  Extras: {', '.join(extras)}")
    if args.parallel > 1:
        print(f"  Parallel: {args.parallel} workers")
    print("=" * 70)
    print()

    # Load settings
    settings = load_settings(args.config)
    ars_config = load_ars_config()

    # Staging: 01-Data-Ready for Formatting (raw files land here)
    staging_base = settings.paths.retrieve_dir
    # Output: 02-Data-Ready for Analysis (formatted files go here)
    output_base = settings.paths.watch_root

    # Log file
    log_dir = output_base / month
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = str(log_dir / "formatting_log.txt")

    log_message(f"  Config loaded:", log_file)
    log_message(f"    Staging:     {staging_base}", log_file)
    log_message(f"    Output:      {output_base}", log_file)

    # Get active CSMs (fuzzy match: "James" matches "JamesG", case-insensitive)
    def _csm_matches(config_name, user_input):
        if user_input is None:
            return True
        return config_name.lower().startswith(user_input.lower())

    active_csms = {
        name: path for name, path in settings.csm_sources.sources.items()
        if str(path) != "UPDATE_THIS_PATH"
        and _csm_matches(name, args.csm)
    }

    log_message(f"    CSMs to process: {', '.join(active_csms.keys())}", log_file)
    print()

    total_success = 0
    total_errors = 0

    # Load clients config (used for exclude checks, deferred/workbook gathering)
    clients_config = {}
    config_path = Path(__file__).resolve().parent.parent / "03_Config" / "clients_config.json"
    if config_path.exists():
        clients_config = json.loads(config_path.read_text(encoding="utf-8"))

    def _is_excluded(client_id):
        """Check if a client is excluded in clients_config.json."""
        cfg = clients_config.get(client_id, {})
        return cfg.get("exclude", False)

    def _process_one_csm(csm_name, csm_source):
        """Process a single CSM -- can be called in parallel."""
        src = Path(csm_source) / month
        staging = staging_base / csm_name / month
        output = output_base / csm_name / month

        log_message(f"  {csm_name}:", log_file)
        log_message(f"    Source:  {src}", log_file)
        log_message(f"    Staging: {staging}", log_file)
        log_message(f"    Output:  {output}", log_file)

        success, errors = process_csm(csm_name, str(src), str(staging), str(output), log_file, args.client, args.force, clients_config)

        # ─── EXTRA FILE GATHERING ───
        output_str = str(output)

        if args.with_trans:
            log_message(f"  {csm_name}: Gathering transaction files...", log_file)
            txn_base = str(output_base / "TXN Files")
            t_ok_total, t_err_total = 0, 0
            # Search month subfolder (e.g., .../JamesG/OD Data Dumps/2026.04/)
            if src.exists():
                t_ok, t_err = gather_trans_files(str(src), txn_base, csm_name, args.client, log_file, clients_config)
                t_ok_total += t_ok
                t_err_total += t_err
            # Also search CSM root (some clients drop TXN files at the top level)
            csm_root = Path(csm_source)
            if csm_root.exists() and csm_root != src:
                t_ok, t_err = gather_trans_files(str(csm_root), txn_base, csm_name, args.client, log_file, clients_config)
                t_ok_total += t_ok
                t_err_total += t_err
            log_message(f"    Trans: {t_ok_total} copied, {t_err_total} errors", log_file)

        if args.with_deferred:
            extra_cfg = ars_config.get("extra_files", {})
            deferred_base = extra_cfg.get("deferred_base", "")
            if deferred_base:
                client_ids = [args.client] if args.client else list(clients_config.keys())
                log_message(f"  {csm_name}: Gathering deferred files...", log_file)
                d_ok, d_err = gather_deferred_files(client_ids, deferred_base, output_str, log_file)
                log_message(f"    Deferred: {d_ok} copied, {d_err} errors", log_file)

        if args.with_workbook:
            extra_cfg = ars_config.get("extra_files", {})
            workbook_base = extra_cfg.get("workbook_base", "")
            csm_folder_map = extra_cfg.get("workbook_csm_folder", {})
            csm_folder_name = csm_folder_map.get(csm_name, csm_name)
            if workbook_base:
                client_ids = [args.client] if args.client else list(clients_config.keys())
                log_message(f"  {csm_name}: Gathering workbook files...", log_file)
                w_ok, w_err = gather_workbook_files(client_ids, workbook_base, csm_folder_name, month, output_str, log_file)
                log_message(f"    Workbooks: {w_ok} copied, {w_err} errors", log_file)

        return success, errors

    if args.parallel > 1 and len(active_csms) > 1:
        # Parallel: process multiple CSMs concurrently
        from concurrent.futures import ThreadPoolExecutor, as_completed
        log_message(f"  Parallel mode: {args.parallel} workers for {len(active_csms)} CSMs", log_file)

        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            futures = {
                pool.submit(_process_one_csm, name, path): name
                for name, path in active_csms.items()
            }
            for future in as_completed(futures):
                csm_name = futures[future]
                try:
                    success, errors = future.result()
                    total_success += success
                    total_errors += errors
                except Exception as exc:
                    log_message(f"  {csm_name}: PARALLEL ERROR: {exc}", log_file)
                    total_errors += 1
    else:
        # Sequential: one CSM at a time
        for csm_name, csm_source in active_csms.items():
            success, errors = _process_one_csm(csm_name, csm_source)
            total_success += success
            total_errors += errors

    # Summary
    print()
    print("=" * 70)
    log_message(f"  STEP 1 COMPLETE", log_file)
    log_message(f"    Formatted: {total_success} files", log_file)
    if total_errors:
        log_message(f"    Errors:    {total_errors}", log_file)
    log_message(f"    Output:    {output_base / month}", log_file)
    log_message(f"    Log:       {log_file}", log_file)
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
