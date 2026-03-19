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


def process_csm(csm_name, src_directory, dst_directory, log_file=None):
    """Process all ODD files for a single CSM.

    1. Unzip any ZIPs in the source directory
    2. Rename CSVs (truncate after 'ODD')
    3. Convert CSVs to Excel
    4. Run 7-step formatting on each Excel file
    5. Save formatted output to destination
    """
    if not os.path.exists(src_directory):
        log_message(f"  {csm_name}: Source not found: {src_directory}", log_file)
        return 0, 0

    unzipped_dir = os.path.join(src_directory, "unzipped")
    processed_csv_dir = os.path.join(src_directory, "processed")
    processed_excel_dir = os.path.join(dst_directory, "Processed")

    os.makedirs(dst_directory, exist_ok=True)
    os.makedirs(unzipped_dir, exist_ok=True)
    os.makedirs(processed_csv_dir, exist_ok=True)
    os.makedirs(processed_excel_dir, exist_ok=True)

    success_count = 0
    error_count = 0

    # Step 1: Unzip ZIPs
    zip_files = [f for f in os.listdir(src_directory) if f.endswith('.zip')]
    if zip_files:
        log_message(f"  {csm_name}: Found {len(zip_files)} ZIP file(s)", log_file)

    for item in zip_files:
        item_path = os.path.join(src_directory, item)
        if zipfile.is_zipfile(item_path):
            with zipfile.ZipFile(item_path, 'r') as zip_ref:
                zip_ref.extractall(src_directory)
            shutil.move(item_path, os.path.join(unzipped_dir, item))
            log_message(f"    Extracted: {item}", log_file)

    # Step 2: Rename CSVs (truncate after 'ODD')
    csv_files = [f for f in os.listdir(src_directory) if f.endswith('.csv')]
    renamed_csv_files = []
    for csv_file in csv_files:
        odd_position = csv_file.find('ODD')
        if odd_position != -1:
            new_name = csv_file[:odd_position + 3] + '.csv'
            new_path = os.path.join(src_directory, new_name)
            original_path = os.path.join(src_directory, csv_file)
            if original_path != new_path:
                os.rename(original_path, new_path)
                log_message(f"    Renamed: {csv_file} -> {new_name}", log_file)
            renamed_csv_files.append(new_name)
        else:
            renamed_csv_files.append(csv_file)

    # Step 3: Convert CSVs to Excel
    for csv_file in renamed_csv_files:
        try:
            csv_path = os.path.join(src_directory, csv_file)
            df = pd.read_csv(csv_path, skiprows=4, low_memory=False)

            if df.empty:
                log_message(f"    Skipping empty file: {csv_file}", log_file)
                continue

            # Drop first column if it's an index column
            if df.columns[0].startswith("Unnamed") or df.iloc[:, 0].dtype == "int64":
                df = df.drop(columns=[df.columns[0]])

            excel_filename = os.path.splitext(csv_file)[0] + '.xlsx'
            excel_path = os.path.join(dst_directory, excel_filename)
            df.to_excel(excel_path, index=False, engine='openpyxl')

            shutil.move(csv_path, os.path.join(processed_csv_dir, csv_file))
            log_message(f"    Converted: {csv_file} -> {excel_filename}", log_file)

        except Exception as e:
            log_message(f"    ERROR converting {csv_file}: {e}", log_file)
            error_count += 1

    # Step 4: Format Excel files (7-step pipeline)
    excel_files = [f for f in os.listdir(dst_directory)
                   if f.endswith('.xlsx') and 'formatted' not in f.lower()]
    if excel_files:
        log_message(f"  {csm_name}: Formatting {len(excel_files)} Excel file(s)", log_file)

    for item in excel_files:
        try:
            file_path = os.path.join(dst_directory, item)
            df = pd.read_excel(file_path)

            if df.empty:
                log_message(f"    Skipping empty: {item}", log_file)
                continue

            log_message(f"    Formatting: {item} ({len(df):,} rows, {len(df.columns)} cols)", log_file)

            # Run the canonical 7-step formatting
            df = format_odd(df)

            # Save formatted file
            df.to_excel(file_path, index=False, engine='openpyxl')
            shutil.move(file_path, os.path.join(processed_excel_dir, item))

            log_message(f"    Done: {item} -> {processed_excel_dir}", log_file)
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
    parser.add_argument("--config", type=str, default=None,
                        help="Path to ars_config.json")
    args = parser.parse_args()

    month = args.month or datetime.now().strftime("%Y.%m")

    print()
    print("=" * 70)
    print("  STEP 1: FORMAT ODD FILES")
    print(f"  Month: {month}")
    print("=" * 70)
    print()

    # Load settings
    settings = load_settings(args.config)

    # Destination for formatted files
    dst_base = settings.paths.watch_root

    # Log file
    log_dir = dst_base / month
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = str(log_dir / "formatting_log.txt")

    log_message(f"  Config loaded:", log_file)
    log_message(f"    Destination: {dst_base}", log_file)

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
        # Destination: 02-Data-Ready for Analysis/YYYY.MM
        dst = dst_base / month

        log_message(f"  {csm_name}:", log_file)
        log_message(f"    Source: {src}", log_file)
        log_message(f"    Dest:   {dst}", log_file)

        success, errors = process_csm(csm_name, str(src), str(dst), log_file)
        total_success += success
        total_errors += errors

    # Summary
    print()
    print("=" * 70)
    log_message(f"  STEP 1 COMPLETE", log_file)
    log_message(f"    Formatted: {total_success} files", log_file)
    if total_errors:
        log_message(f"    Errors:    {total_errors}", log_file)
    log_message(f"    Output:    {dst_base / month}", log_file)
    log_message(f"    Log:       {log_file}", log_file)
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
