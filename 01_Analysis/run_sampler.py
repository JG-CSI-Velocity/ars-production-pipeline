r"""Run the Slide Sampler -- generates a review PPTX with real data + metadata stamps.

Usage:
    python run_sampler.py --month 2026.04 --csm JamesG --client 1615
    python run_sampler.py --month 2026.04 --csm JamesG --client 1615 --section mailer
    python run_sampler.py --month 2026.04 --csm JamesG --client 1615 --section dctr
    python run_sampler.py --month 2026.04 --csm JamesG --client 1615 --list-sections
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
    parser.add_argument("--section", type=str, default=None,
                        help="Only include this section (e.g., mailer, dctr, rege, attrition, insights)")
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

    print()
    print("=" * 60)
    print("  SLIDE SAMPLER")
    print(f"  Client:  {args.client}")
    print(f"  Month:   {args.month}")
    print(f"  CSM:     {args.csm}")
    if args.section:
        print(f"  Section: {args.section}")
    else:
        print(f"  Section: ALL")
    print("=" * 60)
    print()
    print("  Step 1: Running analysis (this takes several minutes)...")
    print()

    from ars_analysis.pipeline.runner import run_pipeline
    from ars_analysis.pipeline.context import PipelineContext

    ctx = PipelineContext(
        client=args.client,
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
    result = build_sample_deck(ctx, section_filter=args.section)

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
