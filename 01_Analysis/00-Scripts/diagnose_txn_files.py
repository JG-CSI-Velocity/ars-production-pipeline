"""
TXN File Diagnostic
===================
Finds malformed lines in the raw transaction CSVs that crash pandas
with ``Error tokenizing data. C error: Expected N fields...''.

Run from the work machine (Windows) where M: is mapped:

    python 01_Analysis/00-Scripts/diagnose_txn_files.py --csm JamesG --client 1441

Output: prints, per file, whether it loads cleanly. For files that
fail, prints the raw text of the offending line(s) and 2 lines of
context above and below so the malformation is visible. Does NOT
modify any data -- this is a read-only investigation.

Why this script exists
----------------------
The pipeline runs `pd.read_csv` with default ``on_bad_lines='error'''
which raises on the FIRST malformed line and gives no filename
context. That makes a single-row error look like the whole pipeline
is broken. This script isolates the problem so the source CSV can
be fixed at its origin (rather than skipped silently in the loader).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path


def find_ars_base() -> Path:
    candidates = [
        Path(r"M:\ARS"),
        Path("/Volumes/M/ARS"),
    ]
    for p in candidates:
        if p.exists():
            return p
    raise SystemExit("ERROR: could not locate ARS base (tried M:\\ARS and /Volumes/M/ARS)")


def detect_separator(filepath: Path) -> str:
    """Match the loader's logic: .csv => comma, anything else => tab."""
    return "," if filepath.suffix.lower() == ".csv" else "\t"


def diagnose_file(filepath: Path, expected_columns: int = 13, sep: str | None = None) -> dict:
    """Walk every line of `filepath`, count fields, return a report."""
    if sep is None:
        sep = detect_separator(filepath)

    report = {
        "file": filepath.name,
        "size_mb": filepath.stat().st_size / (1024 * 1024),
        "sep": "TAB" if sep == "\t" else "COMMA",
        "total_lines": 0,
        "header_field_count": None,
        "bad_lines": [],   # list of (lineno, field_count, raw_text)
    }

    # Read with the csv module (matches pandas's underlying tokenizer
    # closely enough to catch the same defects: stray separators,
    # unmatched quotes, embedded newlines).
    with filepath.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.reader(fh, delimiter=sep)
        for lineno, row in enumerate(reader, start=1):
            report["total_lines"] = lineno
            if lineno == 1:
                # First line is the header in production files
                report["header_field_count"] = len(row)
                continue
            # Pipeline expects 13 columns; tolerate 12 (a known FNB
            # variant per the 1776 log) and flag everything else.
            if len(row) not in (expected_columns, expected_columns - 1):
                report["bad_lines"].append(
                    (lineno, len(row), sep.join(row[:5]) + (" ..." if len(row) > 5 else ""))
                )
                if len(report["bad_lines"]) >= 20:
                    # Stop early -- 20 examples is enough to characterize
                    # the pattern and avoids huge logs on systemic errors.
                    break
    return report


def fetch_context(filepath: Path, lineno: int, around: int = 2) -> list[tuple[int, str]]:
    """Return (line_number, raw_text) tuples for `around` lines on each
    side of `lineno`, plus `lineno` itself. Read raw -- do NOT csv-parse,
    so we see the actual bytes that confused the parser."""
    out: list[tuple[int, str]] = []
    lo = max(1, lineno - around)
    hi = lineno + around
    with filepath.open("r", encoding="utf-8", errors="replace") as fh:
        for current, line in enumerate(fh, start=1):
            if current < lo:
                continue
            if current > hi:
                break
            out.append((current, line.rstrip("\n")))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csm", required=True, help="CSM folder name (e.g. JamesG)")
    parser.add_argument("--client", required=True, help="Client ID (e.g. 1441)")
    parser.add_argument("--expected-columns", type=int, default=13)
    parser.add_argument("--context", type=int, default=2,
                        help="Raw lines to show on each side of bad line (default 2)")
    args = parser.parse_args()

    ars_base = find_ars_base()
    txn_dir = ars_base / "00_Formatting" / "02-Data-Ready for Analysis" / "TXN Files" / args.csm / args.client
    if not txn_dir.exists():
        print(f"ERROR: TXN directory not found: {txn_dir}")
        return 1

    files = sorted(
        list(txn_dir.glob("*.csv"))
        + list(txn_dir.glob("*.txt"))
        + [p for p in txn_dir.iterdir() if p.is_dir() and p.name.isdigit() for q in p.iterdir() if q.suffix.lower() in (".csv", ".txt")]
    )
    if not files:
        print(f"ERROR: no .csv or .txt files in {txn_dir}")
        return 1

    print()
    print("=" * 78)
    print(f"  TXN FILE DIAGNOSTIC -- {args.csm} / client {args.client}")
    print(f"  Path: {txn_dir}")
    print(f"  Files: {len(files)}  Expected columns: {args.expected_columns}")
    print("=" * 78)

    overall_bad = 0
    for fp in files:
        print()
        report = diagnose_file(fp, expected_columns=args.expected_columns)
        size_str = f"{report['size_mb']:.0f} MB"
        line_str = f"{report['total_lines']:,}"
        if not report["bad_lines"]:
            print(f"  OK   {fp.name}  ({size_str}, {line_str} lines, header={report['header_field_count']} cols, {report['sep']})")
            continue

        overall_bad += 1
        print(f"  BAD  {fp.name}  ({size_str}, {line_str} lines, header={report['header_field_count']} cols, {report['sep']})")
        print(f"       {len(report['bad_lines'])} malformed line(s) (showing first {min(len(report['bad_lines']), 10)}):")
        for lineno, n_fields, preview in report["bad_lines"][:10]:
            delta = n_fields - args.expected_columns
            sign = "+" if delta > 0 else ""
            print(f"         line {lineno:>7}: {n_fields} fields ({sign}{delta} vs expected)  preview: {preview[:100]}")

        # For the FIRST bad line in this file, also show raw context
        if report["bad_lines"]:
            first_bad_lineno = report["bad_lines"][0][0]
            print(f"       Raw context around line {first_bad_lineno}:")
            for lno, raw in fetch_context(fp, first_bad_lineno, around=args.context):
                marker = " >>> " if lno == first_bad_lineno else "     "
                # Clip very long lines so the report stays readable
                shown = raw if len(raw) <= 240 else (raw[:237] + "...")
                print(f"         {marker}{lno:>7}: {shown}")

    print()
    print("=" * 78)
    if overall_bad == 0:
        print("  All files parsed cleanly. No malformed lines detected.")
    else:
        print(f"  {overall_bad} of {len(files)} file(s) have malformed lines.")
        print()
        print("  WHAT TO DO:")
        print("    1. Open each BAD file in a text editor (notepad++ or VS Code).")
        print("    2. Jump to the line numbers shown above.")
        print("    3. Inspect the offending row -- common causes:")
        print("       * Stray comma INSIDE a merchant name (e.g. ``SMITH, JOHN'')")
        print("       * Unmatched double-quote (`` not closed before EOL)")
        print("       * Embedded newline inside a field (line continuation)")
        print("    4. Fix the source row, save the file, re-run the pipeline.")
        print()
        print("  If the same kind of malformation appears in EVERY monthly file,")
        print("  the bug is upstream in the report-generation system that produces")
        print("  these CSVs -- raise it with whoever maintains that system.")
    print("=" * 78)
    return 0 if overall_bad == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
