"""Step 1: Format ODD files from CSM source folder.

Reads raw ZIPs/CSVs from the CSM's M: drive folder, unzips, converts
to Excel, runs the 7-step formatting, and saves the formatted output
to 02-Data-Ready for Analysis.

Usage:
    python run.py                                    # current month, all CSMs
    python run.py --month 2026.03                    # specific month
    python run.py --month 2026.03 --csm JamesG       # single CSM only
"""

import argparse
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# Add repo root to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from configs.settings import load_settings
from shared.format_odd import format_odd


def log_message(message, log_file=None):
    print(message)
    if log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(message + "\n")


def process_csm(csm_name, src_directory, staging_directory, output_directory, log_file=None, client_filter=None):
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

    for item in zip_files:
        item_path = os.path.join(src_directory, item)
        # Extract client ID from ZIP filename (e.g., 1200 from 1200_ODDD.zip)
        zip_client = re.match(r'^(\d+)', item)
        zip_client_id = zip_client.group(1) if zip_client else 'unknown'
        client_staging = os.path.join(staging_directory, zip_client_id)
        os.makedirs(client_staging, exist_ok=True)

        staged_zip = os.path.join(client_staging, item)
        if zipfile.is_zipfile(item_path):
            shutil.copy2(item_path, staged_zip)
            with zipfile.ZipFile(staged_zip, 'r') as zip_ref:
                # Only extract ODD files from the ZIP
                odd_entries = [n for n in zip_ref.namelist()
                               if 'odd' in n.lower() and not n.startswith('__MACOSX')]
                for entry in odd_entries:
                    zip_ref.extract(entry, client_staging)
            os.remove(staged_zip)
            log_message(f"    Copied + extracted: {item} -> {client_staging}", log_file)

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
    renamed_csv_files = []
    for client_id, csv_file in csv_files:
        client_path = os.path.join(staging_directory, client_id)
        odd_position = csv_file.upper().find('ODD')
        if odd_position != -1:
            new_name = csv_file[:odd_position + 3] + '.csv'
            new_path = os.path.join(client_path, new_name)
            original_path = os.path.join(client_path, csv_file)
            if original_path != new_path:
                if os.path.exists(new_path):
                    os.remove(new_path)
                os.rename(original_path, new_path)
                log_message(f"    Renamed: {csv_file} -> {new_name}", log_file)
            renamed_csv_files.append((client_id, new_name))
        else:
            renamed_csv_files.append((client_id, csv_file))

    # Step 3+4: Read CSV, format, write formatted Excel directly to output
    # Skips the intermediate CSV->Excel conversion entirely (avoids OLE issues)
    if renamed_csv_files:
        log_message(f"  {csm_name}: Formatting {len(renamed_csv_files)} file(s)", log_file)

    for client_id, csv_file in renamed_csv_files:
        try:
            client_path = os.path.join(staging_directory, client_id)
            csv_path = os.path.join(client_path, csv_file)
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

            # Save formatted Excel directly to output: CSM/YYYY.MM/ClientID/
            excel_filename = os.path.splitext(csv_file)[0] + '.xlsx'
            client_output_dir = os.path.join(output_directory, client_id)
            os.makedirs(client_output_dir, exist_ok=True)
            output_path = os.path.join(client_output_dir, excel_filename)
            df.to_excel(output_path, index=False, engine='openpyxl')

            log_message(f"    Done: {excel_filename} -> {client_output_dir}", log_file)
            success_count += 1

        except Exception as e:
            log_message(f"    ERROR formatting {item}: {e}", log_file)
            error_count += 1

    return success_count, error_count


def main():
    parser = argparse.ArgumentParser(description="Step 1: Format ODD files")
    parser.add_argument("--month", type=str, default=None,
                        help="Target month in YYYY.MM format (default: current month)")
    parser.add_argument("--csm", type=str, default=None,
                        help="Process only this CSM (default: all)")
    parser.add_argument("--client", type=str, default=None,
                        help="Process only this client ID (default: all)")
    parser.add_argument("--config", type=str, default=None,
                        help="Path to ars_config.json")
    args = parser.parse_args()

    month = args.month or datetime.now().strftime("%Y.%m")

    print()
    print("=" * 70)
    print("  STEP 1: FORMAT ODD FILES")
    print(f"  Month:  {month}")
    if args.csm:
        print(f"  CSM:    {args.csm}")
    if args.client:
        print(f"  Client: {args.client}")
    print("=" * 70)
    print()

    # Load settings
    settings = load_settings(args.config)

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

    # Get active CSMs
    active_csms = {
        name: path for name, path in settings.csm_sources.sources.items()
        if str(path) != "UPDATE_THIS_PATH"
        and (args.csm is None or name == args.csm)
    }

    log_message(f"    CSMs to process: {', '.join(active_csms.keys())}", log_file)
    print()

    total_success = 0
    total_errors = 0

    for csm_name, csm_source in active_csms.items():
        # Source: CSM's M: drive folder with the month subfolder
        src = Path(csm_source) / month
        # Staging: 01-Data-Ready for Formatting/CSM/YYYY.MM
        staging = staging_base / csm_name / month
        # Output: 02-Data-Ready for Analysis/CSM/YYYY.MM
        output = output_base / csm_name / month

        log_message(f"  {csm_name}:", log_file)
        log_message(f"    Source:  {src}", log_file)
        log_message(f"    Staging: {staging}", log_file)
        log_message(f"    Output:  {output}", log_file)

        success, errors = process_csm(csm_name, str(src), str(staging), str(output), log_file, args.client)
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
