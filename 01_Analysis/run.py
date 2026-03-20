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


def _find_odd_file(csm, month, client_id):
    """Auto-find the formatted ODD file from the standard path structure."""
    if os.name == "nt":
        base = Path(r"M:\ARS\00_Formatting\02-Data-Ready for Analysis")
    else:
        base = Path("/Volumes/M/ARS/00_Formatting/02-Data-Ready for Analysis")

    client_dir = base / csm / month / client_id
    if not client_dir.exists():
        return None

    # Find Excel files in the client folder
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
    args = parser.parse_args()

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
        for candidate in [
            Path(r"M:\ARS\Config\clients_config.json"),
            Path(__file__).parent.parent / "00_Formatting" / "configs" / "clients_config.json",
        ]:
            if candidate.exists():
                config_path = str(candidate)
                break

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

    ctx = PipelineContext(
        client_id=client_id,
        client_name=client_name,
        csm="",
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

    # Run the ARS pipeline
    from runner import run_ars

    print("  Starting ARS pipeline...")
    print()

    try:
        results = run_ars(ctx)

        # Move PPTX files to 02_Presentations
        import shutil
        pptx_files = [f for f in output_dir.iterdir() if f.suffix == '.pptx']
        for pf in pptx_files:
            dest = pptx_dir / pf.name
            shutil.copy2(pf, dest)
            pf.unlink()  # remove from analysis output

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
