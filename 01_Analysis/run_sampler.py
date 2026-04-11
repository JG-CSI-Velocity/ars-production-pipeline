r"""Run the Slide Sampler -- generates a review PPTX with real data + metadata stamps.

Usage:
    python run_sampler.py --month 2026.04 --csm JamesG --client 1615
    python run_sampler.py --month 2026.03 --csm JamesG --client 1776
"""

import argparse
import sys
import types
from pathlib import Path

# Same path setup as run.py -- create ars_analysis package alias
_scripts_dir = Path(__file__).parent / "00-Scripts"
sys.path.insert(0, str(_scripts_dir))

_ars_pkg = types.ModuleType("ars_analysis")
_ars_pkg.__path__ = [str(_scripts_dir)]
_ars_pkg.__package__ = "ars_analysis"
sys.modules["ars_analysis"] = _ars_pkg

# Config path
_config_dir = Path(__file__).resolve().parent.parent / "03_Config"
sys.path.insert(0, str(_config_dir))


def main():
    parser = argparse.ArgumentParser(description="Build slide sampler with real data")
    parser.add_argument("--month", required=True, help="Month in YYYY.MM format")
    parser.add_argument("--csm", required=True, help="CSM name")
    parser.add_argument("--client", required=True, help="Client ID")
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  SLIDE SAMPLER")
    print(f"  Client: {args.client}")
    print(f"  Month:  {args.month}")
    print(f"  CSM:    {args.csm}")
    print("=" * 60)
    print()
    print("  Step 1: Running analysis (this takes several minutes)...")
    print()

    from ars_analysis.pipeline.runner import run_pipeline
    from ars_analysis.pipeline.context import PipelineContext

    ctx = PipelineContext(
        client_id=args.client,
        month=args.month,
        csm=args.csm,
    )

    # Run full analysis but skip the normal deck generation
    run_pipeline(ctx, skip_generate=True)

    if not ctx.all_slides:
        print("  ERROR: No analysis results produced. Cannot build sampler.")
        sys.exit(1)

    print()
    print(f"  Analysis complete: {len(ctx.all_slides)} slide results")
    print(f"  Step 2: Building sampler PPTX...")
    print()

    from ars_analysis.output.sample_deck_builder import build_sample_deck
    result = build_sample_deck(ctx)

    if result:
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
