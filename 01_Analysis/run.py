"""Step 2: Run ARS analysis on a formatted ODD file and generate PowerPoint.

Usage:
    python run.py <odd_file>
    python run.py <odd_file> --client-id 1200 --client-name "Guardians CU"
    python run.py <odd_file> --output-dir M:\ARS\Presentations

The ODD file should be the formatted Excel from Step 1
(e.g., 02-Data-Ready for Analysis/JamesG/2026.03/1200/1200-ODD.xlsx)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add step2-analysis to path so ars_analysis imports resolve locally
sys.path.insert(0, str(Path(__file__).parent))

# Rewire imports: the code uses "from ars_analysis.X import Y"
# but we have the modules flat in this directory. Create the package alias.
import importlib
import types

# Build a virtual ars_analysis package from our local files
_step2_dir = Path(__file__).parent
_ars_pkg = types.ModuleType("ars_analysis")
_ars_pkg.__path__ = [str(_step2_dir)]
_ars_pkg.__package__ = "ars_analysis"
sys.modules["ars_analysis"] = _ars_pkg


def main():
    parser = argparse.ArgumentParser(description="Step 2: Run ARS Analysis + Generate PPTX")
    parser.add_argument("odd_file", type=str,
                        help="Path to formatted ODD Excel file")
    parser.add_argument("--client-id", type=str, default=None,
                        help="Client ID (auto-detected from filename if not provided)")
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

    odd_path = Path(args.odd_file)
    if not odd_path.exists():
        print(f"  ERROR: File not found: {odd_path}")
        sys.exit(1)

    # Auto-detect client ID and name from filename
    # Expected: 1200-2026-03-Guardians Credit Union-ODD.xlsx
    client_id = args.client_id
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

    # Derive CSM and month from the input path
    # Expected: .../02-Data-Ready for Analysis/CSM/YYYY.MM/ClientID/filename.xlsx
    csm_name = ""
    month = ""
    try:
        # Walk up: parent=ClientID, grandparent=month, great-grandparent=CSM
        client_dir = odd_path.parent
        month_dir = client_dir.parent
        csm_dir = month_dir.parent

        if client_dir.name.isdigit():
            client_id = client_id or client_dir.name
        if "." in month_dir.name and month_dir.name[:4].isdigit():
            month = month_dir.name
        csm_name = csm_dir.name if csm_dir.name not in ("02-Data-Ready for Analysis",) else ""
    except Exception:
        pass

    if not month:
        month = datetime.now().strftime("%Y.%m")

    # Output directory: M:\ARS\01_Analysis\CSM\YYYY.MM\ClientID\
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        analysis_base = Path(r"M:\ARS\01_Analysis\02_Completed_Analysis") if os.name == "nt" else Path("/Volumes/M/ARS/01_Analysis/02_Completed_Analysis")
        if csm_name:
            output_dir = analysis_base / csm_name / month / client_id
        else:
            output_dir = analysis_base / month / client_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Config file
    config_path = args.config
    if not config_path:
        # Try known locations
        for candidate in [
            Path(r"M:\ARS\Config\clients_config.json"),
            _step2_dir.parent / "step1-formatting" / "configs" / "clients_config.json",
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

        print()
        print("=" * 70)
        print("  STEP 2 COMPLETE")
        print("=" * 70)
        print(f"    Results: {len(results)} slides generated")
        print(f"    Output:  {output_dir}")

        # List output files
        for f in output_dir.iterdir():
            if f.suffix in ('.pptx', '.xlsx', '.json') and client_id in f.name:
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"    {f.name} ({size_mb:.1f} MB)")

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
