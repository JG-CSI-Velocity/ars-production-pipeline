r"""Run the Slide Sampler -- generates a review PPTX with real data + metadata stamps.

Modeled on run.py -- uses the same path resolution, context creation, and analysis
pipeline. Builds a SAMPLER PPTX instead of the production deck.

Usage:
    python run_sampler.py --month 2026.04 --csm JamesG --client 1615
    python run_sampler.py --month 2026.04 --csm JamesG --client 1615 --section mailer
    python run_sampler.py --list-sections
"""

import argparse
import glob
import os
import sys
from datetime import datetime
from pathlib import Path
import types

# Same path setup as run.py
_scripts_dir = Path(__file__).parent / "00-Scripts"
sys.path.insert(0, str(_scripts_dir))

_ars_pkg = types.ModuleType("ars_analysis")
_ars_pkg.__path__ = [str(_scripts_dir)]
_ars_pkg.__package__ = "ars_analysis"
sys.modules["ars_analysis"] = _ars_pkg

_config_dir = Path(__file__).resolve().parent.parent / "03_Config"
sys.path.insert(0, str(_config_dir))


def _find_odd_file(csm, month, client_id):
    """Find the formatted ODD file for a client (same logic as run.py)."""
    if os.name == "nt":
        base = Path(r"M:\ARS\00_Formatting\02-Data-Ready for Analysis")
    else:
        base = Path("/Volumes/M/ARS/00_Formatting/02-Data-Ready for Analysis")

    # Try exact path
    client_dir = base / csm / month / client_id
    if client_dir.exists():
        xlsx = list(client_dir.glob("*.xlsx"))
        if xlsx:
            return xlsx[0]

    # Fuzzy CSM match
    if base.exists():
        for d in base.iterdir():
            if d.is_dir() and d.name.lower().startswith(csm.lower()):
                client_dir = d / month / client_id
                if client_dir.exists():
                    xlsx = list(client_dir.glob("*.xlsx"))
                    if xlsx:
                        return xlsx[0]
    return None


def _find_config():
    """Find clients_config.json."""
    candidates = [
        Path(r"M:\ARS\03_Config\clients_config.json"),
        Path(r"M:\ARS\Config\clients_config.json"),
        Path(__file__).parent.parent / "03_Config" / "clients_config.json",
    ]
    for c in candidates:
        try:
            if c.exists():
                return str(c)
        except OSError:
            continue
    return None


def main():
    parser = argparse.ArgumentParser(description="Build slide sampler with real data")
    parser.add_argument("--month", type=str, default=None, help="Month in YYYY.MM format")
    parser.add_argument("--csm", type=str, default=None, help="CSM name")
    parser.add_argument("--client", type=str, default=None, help="Client ID")
    parser.add_argument("--section", type=str, default=None,
                        help="Only include this section (e.g., mailer, dctr, rege)")
    parser.add_argument("--list-sections", action="store_true",
                        help="List available sections and exit")
    args = parser.parse_args()

    if args.list_sections:
        from ars_analysis.output.deck_builder import _SECTION_LABELS, SECTION_ORDER
        print("\nAvailable sections:")
        for key in SECTION_ORDER:
            label = _SECTION_LABELS.get(key, key)
            print(f"  {key:15s}  {label}")
        print()
        return

    if not args.month or not args.csm or not args.client:
        parser.error("--month, --csm, and --client are required (unless using --list-sections)")

    month = args.month
    csm = args.csm
    client_id = args.client

    # Find the formatted ODD file
    odd_path = _find_odd_file(csm, month, client_id)
    if not odd_path:
        print(f"\n  ERROR: No formatted ODD file found for {client_id} in {month}")
        print(f"  Run formatting first:")
        print(f"    cd M:\\ARS\\00_Formatting")
        print(f"    python run.py --month {month} --csm {csm} --client {client_id}")
        sys.exit(1)

    # Extract client name from filename
    parts = odd_path.stem.split("-")
    client_name = "-".join(parts[3:-1]).strip() if len(parts) >= 4 else f"Client {client_id}"

    # Output directories
    if os.name == "nt":
        analysis_base = Path(r"M:\ARS\01_Analysis\01_Completed_Analysis")
        pptx_base = Path(r"M:\ARS\02_Presentations")
    else:
        analysis_base = Path("/Volumes/M/ARS/01_Analysis/01_Completed_Analysis")
        pptx_base = Path("/Volumes/M/ARS/02_Presentations")

    output_dir = analysis_base / csm / month / client_id
    pptx_dir = pptx_base / csm / month / client_id
    output_dir.mkdir(parents=True, exist_ok=True)
    pptx_dir.mkdir(parents=True, exist_ok=True)

    config_path = _find_config()

    print()
    print("=" * 60)
    print("  SLIDE SAMPLER")
    print("=" * 60)
    print(f"  Client:  {client_id} - {client_name}")
    print(f"  CSM:     {csm}")
    print(f"  Month:   {month}")
    print(f"  ODD:     {odd_path}")
    print(f"  Section: {args.section or 'ALL'}")
    print("=" * 60)
    print()

    # Build context (same as run.py)
    from shared.context import PipelineContext

    ctx = PipelineContext(
        client_id=client_id,
        client_name=client_name,
        csm=csm,
        output_dir=output_dir,
        input_files={"oddd": str(odd_path)},
        client_config={
            "config_path": config_path,
            "client_id": client_id,
        },
    )

    # Redirect pptx output
    ctx.pptx_dir = pptx_dir

    def on_progress(msg):
        print(f"  {msg}")

    ctx.progress_callback = on_progress

    # Run analysis
    print("  Running analysis...")
    print()

    from runner import run_ars
    run_ars(ctx)

    if not ctx.all_slides:
        print("  ERROR: No analysis results. Cannot build sampler.")
        sys.exit(1)

    print()
    print(f"  Analysis complete: {len(ctx.all_slides)} slide results")
    print(f"  Building sampler PPTX...")
    print()

    # Build sampler
    from ars_analysis.output.sample_deck_builder import build_sample_deck
    result = build_sample_deck(ctx, section_filter=args.section)

    if result:
        print()
        print("=" * 60)
        print(f"  DONE!")
        print(f"  Open: {result}")
        print()
        print(f"  Each slide has a stamp at the top:")
        print(f"    [SECTION N/total] id:slide_id | layout:N (NAME) | type:TYPE")
        print()
        print(f"  Mark which slides to KEEP per section.")
        print("=" * 60)
    else:
        print("  ERROR: Sampler build failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
