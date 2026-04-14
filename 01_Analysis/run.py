r"""Step 2: Run ARS analysis on a formatted ODD file and generate PowerPoint.

Usage:
    python run.py --month 2026.03 --csm JamesG --client 1200
    python run.py "path\to\formatted-ODD.xlsx"
    python run.py "path\to\ODD.xlsx" --output-dir M:\ARS\01_Analysis\01_Completed_Analysis

Auto-finds the formatted ODD in 00_Formatting\02-Data-Ready for Analysis
when --month, --csm, and --client are provided.
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime
from pathlib import Path


class TeeLogger:
    """Write everything to both terminal and a log file."""

    def __init__(self, log_path):
        self.terminal = sys.stdout
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_file = open(log_path, "w", encoding="utf-8")
        self.log_path = log_path
        self._closed = False

    def write(self, message):
        try:
            self.terminal.write(message)
        except Exception:
            pass
        if not self._closed:
            try:
                self.log_file.write(message)
                self.log_file.flush()
            except Exception:
                pass

    def flush(self):
        try:
            self.terminal.flush()
        except Exception:
            pass
        if not self._closed:
            try:
                self.log_file.flush()
            except Exception:
                pass

    def close(self):
        self._closed = True
        try:
            self.log_file.close()
        except Exception:
            pass


# Add 00-Scripts to path so imports work
_scripts_dir = Path(__file__).parent / "00-Scripts"
sys.path.insert(0, str(_scripts_dir))

# Rewire imports: the code uses "from ars_analysis.X import Y"
# but we have the modules in 00-Scripts/. Create the package alias.
import importlib
import types

_ars_pkg = types.ModuleType("ars_analysis")
_ars_pkg.__path__ = [str(_scripts_dir)]
_ars_pkg.__package__ = "ars_analysis"
sys.modules["ars_analysis"] = _ars_pkg


def _resolve_csm_name(csm_input, base_path):
    """Fuzzy match CSM name: 'James' matches 'JamesG' folder."""
    if not base_path.exists():
        return csm_input
    for d in base_path.iterdir():
        if d.is_dir() and d.name.lower().startswith(csm_input.lower()):
            return d.name
    return csm_input


def _find_odd_file(csm, month, client_id):
    """Auto-find the formatted ODD file from the standard path structure."""
    if os.name == "nt":
        base = Path(r"M:\ARS\00_Formatting\02-Data-Ready for Analysis")
    else:
        base = Path("/Volumes/M/ARS/00_Formatting/02-Data-Ready for Analysis")

    # Fuzzy match CSM name
    csm = _resolve_csm_name(csm, base)

    client_dir = base / csm / month / client_id
    if not client_dir.exists():
        return None

    xlsx_files = list(client_dir.glob("*.xlsx"))
    if xlsx_files:
        return xlsx_files[0]
    return None


def main():
    parser = argparse.ArgumentParser(description="Step 2: Run ARS Analysis + Generate PPTX")
    parser.add_argument("odd_file", type=str, nargs="?", default=None,
                        help="Path to formatted ODD Excel file (or use --month/--csm/--client)")
    parser.add_argument("--month", type=str, default=None,
                        help="Month in YYYY.MM format (used with --csm and --client)")
    parser.add_argument("--csm", type=str, default=None,
                        help="CSM name (used with --month and --client)")
    parser.add_argument("--client", type=str, default=None,
                        help="Client ID (used with --month and --csm)")
    parser.add_argument("--client-name", type=str, default=None,
                        help="Client name (auto-detected from filename if not provided)")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: same folder as ODD file)")
    parser.add_argument("--config", type=str, default=None,
                        help="Path to clients_config.json")
    parser.add_argument("--template", type=str, default=None,
                        help="Path to PPTX template")
    parser.add_argument("--skip-pptx", action="store_true",
                        help="Skip PowerPoint generation (Excel only)")
    parser.add_argument("--product", type=str, default="ars",
                        choices=["ars", "txn", "combined"],
                        help="Analysis product: ars (default), txn (transaction only), combined (both)")
    args = parser.parse_args()

    # Resolve fuzzy CSM name early so logs and paths all use the same name
    if args.csm:
        if os.name == "nt":
            _csm_base = Path(r"M:\ARS\00_Formatting\02-Data-Ready for Analysis")
        else:
            _csm_base = Path("/Volumes/M/ARS/00_Formatting/02-Data-Ready for Analysis")
        args.csm = _resolve_csm_name(args.csm, _csm_base)

    # Start logging to file: 04_Logs/CSM/month/clientID_YYYYMMDD_HHMMSS.log
    _log_csm = args.csm or "unknown"
    _log_month = args.month or datetime.now().strftime("%Y.%m")
    _log_client = args.client or "all"
    _log_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if os.name == "nt":
        _log_dir = Path(r"M:\ARS\04_Logs") / _log_csm / _log_month
    else:
        _log_dir = Path("/Volumes/M/ARS/04_Logs") / _log_csm / _log_month
    _log_path = _log_dir / f"{_log_client}_{_log_timestamp}.log"
    try:
        _tee = TeeLogger(_log_path)
        sys.stdout = _tee
        sys.stderr = _tee
    except OSError:
        pass  # can't write to M: drive, just use terminal

    # Resolve the ODD file path
    if args.odd_file:
        odd_path = Path(args.odd_file)
    elif args.month and args.csm and args.client:
        # Auto-find from standard path structure
        odd_path_found = _find_odd_file(args.csm, args.month, args.client)
        if odd_path_found:
            odd_path = odd_path_found
            print(f"  Found: {odd_path}")
        else:
            print(f"  ERROR: No formatted ODD file found for {args.csm}/{args.month}/{args.client}")
            if os.name == "nt":
                print(f"  Looked in: M:\\ARS\\00_Formatting\\02-Data-Ready for Analysis\\{args.csm}\\{args.month}\\{args.client}\\")
            sys.exit(1)
    else:
        print("  ERROR: Provide either a file path or --month --csm --client")
        print("  Examples:")
        print('    python run.py --month 2026.03 --csm JamesG --client 1200')
        print('    python run.py "path\\to\\formatted-ODD.xlsx"')
        sys.exit(1)

    if not odd_path.exists():
        print(f"  ERROR: File not found: {odd_path}")
        sys.exit(1)

    # Auto-detect client ID and name from filename
    # Expected: 1200-2026-03-Guardians Credit Union-ODD.xlsx
    client_id = args.client
    client_name = args.client_name

    if not client_id:
        parts = odd_path.stem.split("-")
        if parts and parts[0].strip().isdigit():
            client_id = parts[0].strip()
        else:
            # Try parent folder name
            client_id = odd_path.parent.name if odd_path.parent.name.isdigit() else "0000"

    if not client_name and client_id:
        parts = odd_path.stem.split("-")
        if len(parts) >= 4:
            client_name = "-".join(parts[3:-1]).strip()
    if not client_name:
        client_name = f"Client {client_id}"

    # Derive CSM and month -- prefer args, fall back to path parsing
    csm_name = args.csm or ""
    month = args.month or ""

    if not csm_name or not month:
        try:
            client_dir = odd_path.parent
            month_dir = client_dir.parent
            csm_dir = month_dir.parent

            if not client_id and client_dir.name.isdigit():
                client_id = client_dir.name
            if not month and "." in month_dir.name and month_dir.name[:4].isdigit():
                month = month_dir.name
            if not csm_name:
                csm_name = csm_dir.name if csm_dir.name not in ("02-Data-Ready for Analysis",) else ""
        except Exception:
            pass

    if not month:
        month = datetime.now().strftime("%Y.%m")

    # Output directories:
    #   Excel/charts -> 01_Analysis/01_Completed_Analysis/CSM/month/clientID/
    #   PPTX         -> 02_Presentations/CSM/month/clientID/
    if args.output_dir:
        output_dir = Path(args.output_dir)
        pptx_dir = output_dir  # same place if manually specified
    else:
        if os.name == "nt":
            analysis_base = Path(r"M:\ARS\01_Analysis\01_Completed_Analysis")
            pptx_base = Path(r"M:\ARS\02_Presentations")
        else:
            analysis_base = Path("/Volumes/M/ARS/01_Analysis/01_Completed_Analysis")
            pptx_base = Path("/Volumes/M/ARS/02_Presentations")

        if csm_name:
            output_dir = analysis_base / csm_name / month / client_id
            pptx_dir = pptx_base / csm_name / month / client_id
        else:
            output_dir = analysis_base / month / client_id
            pptx_dir = pptx_base / month / client_id

    output_dir.mkdir(parents=True, exist_ok=True)
    pptx_dir.mkdir(parents=True, exist_ok=True)

    # Config file
    config_path = args.config
    if not config_path:
        # Try known locations
        candidates = [
            Path(r"M:\ARS\03_Config\clients_config.json"),
            Path(r"M:\ARS\Config\clients_config.json"),
            Path(__file__).parent.parent / "03_Config" / "clients_config.json",
            Path(__file__).parent.parent / "Config" / "clients_config.json",
        ]
        for candidate in candidates:
            try:
                if candidate.exists():
                    config_path = str(candidate)
                    break
            except OSError:
                continue

        # Last resort: scan for it
        if not config_path and os.name == "nt":
            import glob
            found = glob.glob(r"M:\ARS\*\*clients_config*")
            if not found:
                found = glob.glob(r"M:\ARS\Config\*config*")
            if found:
                config_path = found[0]

    # Check if client is excluded
    if config_path:
        try:
            _all_clients = json.loads(Path(config_path).read_text(encoding="utf-8"))
            _client_cfg = _all_clients.get(client_id, {})
            if _client_cfg.get("exclude", False):
                _reason = _client_cfg.get("exclude_reason", "excluded")
                print(f"  Skipping client {client_id} -- {_reason}")
                sys.exit(0)
        except Exception:
            pass

    print()
    print("=" * 70)
    print("  STEP 2: ARS ANALYSIS + POWERPOINT GENERATION")
    print("=" * 70)
    print(f"  Client:    {client_id} - {client_name}")
    print(f"  CSM:       {csm_name or 'unknown'}")
    print(f"  Month:     {month}")
    print(f"  ODD File:  {odd_path}")
    print(f"  Output:    {output_dir}")
    print(f"  Config:    {config_path or 'None (using defaults)'}")
    print(f"  Template:  {args.template or 'auto-detect from M: drive'}")
    print("=" * 70)
    print()

    # Build the shared PipelineContext
    from shared.context import PipelineContext

    # Parse month arg into a date for the pipeline context
    _month_parts = month.split(".")
    _analysis_date = datetime(int(_month_parts[0]), int(_month_parts[1]), 1).date()

    ctx = PipelineContext(
        client_id=client_id,
        client_name=client_name,
        csm=csm_name,
        analysis_date=_analysis_date,
        output_dir=output_dir,
        input_files={"oddd": str(odd_path)},
        client_config={
            "config_path": config_path,
            "client_id": client_id,
        },
    )

    # Progress callback
    def on_progress(msg):
        print(f"  {msg}")

    ctx.progress_callback = on_progress

    # Run the pipeline based on --product flag
    product = args.product

    if product == "txn":
        from runner import run_txn
        print("  Starting TXN pipeline...")
        print()
        runner_fn = run_txn
    elif product == "combined":
        from runner import run_combined
        print("  Starting combined ARS + TXN pipeline...")
        print()
        runner_fn = run_combined
    else:
        from runner import run_ars
        print("  Starting ARS pipeline...")
        print()
        runner_fn = run_ars

    try:
        results = runner_fn(ctx)

        # Move PPTX files to 02_Presentations
        import gc
        import shutil
        gc.collect()  # release any file handles held by python-pptx/matplotlib

        pptx_files = [f for f in output_dir.iterdir() if f.suffix == '.pptx']
        for pf in pptx_files:
            dest = pptx_dir / pf.name
            for _attempt in range(3):
                try:
                    shutil.copy2(pf, dest)
                    pf.unlink()
                    break
                except PermissionError:
                    if _attempt < 2:
                        import time
                        print(f"    File locked, retrying in 2s... ({pf.name})")
                        time.sleep(2)
                        gc.collect()
                    else:
                        print(f"    WARNING: Could not move {pf.name} (file locked)")
                        print(f"    PPTX remains at: {pf}")
                        print(f"    Copy it manually to: {dest}")

        print()
        print("=" * 70)
        print("  STEP 2 COMPLETE")
        print("=" * 70)
        print(f"    Results:        {len(results)} slides generated")
        print(f"    Analysis:       {output_dir}")
        print(f"    Presentations:  {pptx_dir}")
        print()

        # List output files
        print("    Excel/Data:")
        for f in output_dir.iterdir():
            if f.suffix in ('.xlsx', '.json') and client_id in f.name:
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"      {f.name} ({size_mb:.1f} MB)")

        print("    PowerPoint:")
        for f in pptx_dir.iterdir():
            if f.suffix == '.pptx':
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"      {f.name} ({size_mb:.1f} MB)")

        print("=" * 70)
        print()

        # Log location
        if '_tee' in dir() and hasattr(_tee, 'log_path'):
            print(f"  Full log saved to: {_tee.log_path}")
            print()

    except Exception as e:
        print()
        print("=" * 70)
        print(f"  ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
