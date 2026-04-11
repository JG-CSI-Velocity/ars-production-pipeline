r"""Real Preview -- generates per-section PPTX from actual client data.

Runs the real pipeline (load → subsets → analyze) for one section at a time,
then builds a PPTX with only that section's slides.  This gives you real
charts, real KPIs, and real titles so you can review formatting accurately.

Usage:
    python real_preview.py --odd "path\to\ODD.xlsx" --section dctr
    python real_preview.py --odd "path\to\ODD.xlsx" --section mailer
    python real_preview.py --odd "path\to\ODD.xlsx" --section all
    python real_preview.py --odd "path\to\ODD.xlsx" --list

    # With explicit config + template:
    python real_preview.py --odd "path\to\ODD.xlsx" --section dctr \
        --config "M:\ARS\03_Config\clients_config.json" \
        --template "M:\ARS\02_Presentations\2025-CSI-PPT-Template.pptx"

    # Auto-find ODD from standard path:
    python real_preview.py --month 2026.03 --csm JamesG --client 1585 --section dctr

Sections: overview, dctr, rege, attrition, value, mailer, insights
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup -- same as run.py
# ---------------------------------------------------------------------------
_scripts_dir = Path(__file__).parent / "00-Scripts"
sys.path.insert(0, str(_scripts_dir))

import types as _types

_ars_pkg = _types.ModuleType("ars_analysis")
_ars_pkg.__path__ = [str(_scripts_dir)]
_ars_pkg.__package__ = "ars_analysis"
sys.modules["ars_analysis"] = _ars_pkg

# ---------------------------------------------------------------------------
# Section → module ID mapping (mirrors runner.py _UI_KEY_TO_PREFIXES)
# ---------------------------------------------------------------------------
SECTION_MODULES: dict[str, list[str]] = {
    "overview": ["overview.stat_codes", "overview.product_codes", "overview.eligibility"],
    "dctr": ["dctr.penetration", "dctr.trends", "dctr.branches", "dctr.funnel", "dctr.overlays"],
    "rege": ["rege.status", "rege.branches", "rege.dimensions"],
    "attrition": ["attrition.rates", "attrition.dimensions", "attrition.impact"],
    "value": ["value.analysis"],
    "mailer": [
        "mailer.insights", "mailer.response", "mailer.impact",
        "mailer.cohort", "mailer.reach",
    ],
    "insights": [
        "insights.synthesis", "insights.conclusions", "insights.effectiveness",
        "insights.branch_scorecard", "insights.dormant",
    ],
}

ALL_SECTIONS = list(SECTION_MODULES.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_csm_name(csm_input: str, base_path: Path) -> str:
    if not base_path.exists():
        return csm_input
    for d in base_path.iterdir():
        if d.is_dir() and d.name.lower().startswith(csm_input.lower()):
            return d.name
    return csm_input


def _find_odd_file(csm: str, month: str, client_id: str) -> Path | None:
    if os.name == "nt":
        base = Path(r"M:\ARS\00_Formatting\02-Data-Ready for Analysis")
    else:
        base = Path("/Volumes/M/ARS/00_Formatting/02-Data-Ready for Analysis")
    csm = _resolve_csm_name(csm, base)
    client_dir = base / csm / month / client_id
    if not client_dir.exists():
        return None
    xlsx_files = list(client_dir.glob("*.xlsx"))
    return xlsx_files[0] if xlsx_files else None


def _parse_client_from_filename(odd_path: Path) -> tuple[str, str]:
    """Extract (client_id, client_name) from ODD filename."""
    parts = odd_path.stem.split("-")
    client_id = parts[0].strip() if parts and parts[0].strip().isdigit() else "0000"
    client_name = ""
    if len(parts) >= 4:
        client_name = "-".join(parts[3:-1]).strip()
    return client_id, client_name or f"Client {client_id}"


def _load_client_config(config_path: str | None, client_id: str) -> dict:
    """Load client config from JSON file."""
    if not config_path:
        # Try known locations
        candidates = [
            Path(r"M:\ARS\03_Config\clients_config.json"),
            Path(r"M:\ARS\Config\clients_config.json"),
            Path(__file__).parent.parent / "03_Config" / "clients_config.json",
        ]
        for c in candidates:
            try:
                if c.exists():
                    config_path = str(c)
                    break
            except OSError:
                continue

    if not config_path or not Path(config_path).exists():
        print(f"  WARNING: No config file found, using defaults")
        return {}

    all_clients = json.loads(Path(config_path).read_text())
    if client_id in all_clients:
        return all_clients[client_id]
    if len(all_clients) == 1:
        return next(iter(all_clients.values()))
    print(f"  WARNING: Client {client_id} not in config ({len(all_clients)} clients available)")
    return {}


def _resolve_template(template_arg: str | None) -> Path | None:
    """Find the PPTX template."""
    if template_arg and Path(template_arg).exists():
        return Path(template_arg)

    if os.name == "nt":
        candidates = glob.glob(r"M:\ARS\02_Presentations\*Template*.pptx")
    else:
        candidates = glob.glob("/Volumes/M/ARS/02_Presentations/*Template*.pptx")

    if candidates:
        return Path(candidates[0])

    fallback = _scripts_dir / "output" / "template" / "2025-CSI-PPT-Template.pptx"
    if fallback.exists():
        return fallback

    return None


def _ensure_list(value: object) -> list[str]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        return [value]
    return []


def _safe_float(value: object, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Core: run one section and build its PPTX
# ---------------------------------------------------------------------------

def run_section(
    section: str,
    odd_path: Path,
    client_id: str,
    client_name: str,
    month: str,
    ccfg: dict,
    template_path: Path,
    output_dir: Path,
) -> Path | None:
    """Run analysis for one section and build a standalone PPTX."""

    from types import SimpleNamespace

    from ars_analysis.analytics.registry import get_module, load_all_modules
    from ars_analysis.output.deck_builder import (
        LAYOUT_SECTION_ALT,
        DeckBuilder,
        SlideContent,
        _result_to_slide,
    )
    from ars_analysis.pipeline.context import ClientInfo, OutputPaths
    from ars_analysis.pipeline.context import PipelineContext as ARSContext
    from ars_analysis.pipeline.steps.load import step_load_file
    from ars_analysis.pipeline.steps.subsets import step_subsets

    # Ensure modules are registered
    load_all_modules()

    # Build context
    client_info = ClientInfo(
        client_id=client_id,
        client_name=client_name,
        month=month,
        eligible_stat_codes=_ensure_list(ccfg.get("EligibleStatusCodes", [])),
        eligible_prod_codes=_ensure_list(ccfg.get("EligibleProductCodes", [])),
        eligible_mailable=_ensure_list(ccfg.get("EligibleMailCode", [])),
        nsf_od_fee=_safe_float(ccfg.get("NSF_OD_Fee", 0)),
        ic_rate=_safe_float(ccfg.get("ICRate", 0)),
        dc_indicator=ccfg.get("DCIndicator", "DC Indicator"),
        reg_e_opt_in=_ensure_list(ccfg.get("RegEOptInCode", [])),
        reg_e_column=ccfg.get("RegEColumn", ""),
        data_start_date=ccfg.get("DataStartDate"),
    )

    section_output = output_dir / section
    section_output.mkdir(parents=True, exist_ok=True)

    paths = OutputPaths.from_dir(section_output)

    ctx = ARSContext(
        client=client_info,
        paths=paths,
        progress_callback=lambda msg: print(f"    {msg}"),
    )

    _branch_map = ccfg.get("BranchMapping") or ccfg.get("branch_mapping")
    ctx.settings = SimpleNamespace(
        paths=SimpleNamespace(template_path=template_path),
        branch_mapping=_branch_map if isinstance(_branch_map, dict) else None,
    )

    # Step 1: Load data
    print(f"    Loading data...")
    t0 = time.perf_counter()
    step_load_file(ctx, odd_path)
    print(f"    Loaded in {time.perf_counter() - t0:.1f}s "
          f"({len(ctx.data)} rows)" if ctx.data is not None else "    Load failed")

    # Step 2: Create subsets
    print(f"    Creating subsets...")
    step_subsets(ctx)

    # Step 3: Run only the modules for this section
    # Always run overview first (other sections depend on it)
    module_ids = list(SECTION_MODULES.get("overview", []))
    if section != "overview":
        module_ids.extend(SECTION_MODULES.get(section, []))

    print(f"    Running modules: {', '.join(module_ids)}")
    t0 = time.perf_counter()

    for mid in module_ids:
        try:
            mod_cls = get_module(mid)
        except Exception:
            print(f"      WARNING: Module {mid} not found, skipping")
            continue

        mod = mod_cls()
        errors = mod.validate(ctx)
        if errors:
            print(f"      SKIP {mid}: {'; '.join(errors)}")
            continue

        try:
            results = mod.run(ctx)
            ctx.results[mid] = results
            ctx.all_slides.extend(results)
            ok_count = sum(1 for r in results if getattr(r, "success", False))
            chart_count = sum(
                1 for r in results
                if getattr(r, "chart_path", None) and Path(getattr(r, "chart_path", "")).exists()
            )
            print(f"      {mid}: {len(results)} results ({ok_count} ok, {chart_count} charts)")
        except Exception as exc:
            print(f"      FAIL {mid}: {type(exc).__name__}: {exc}")

    elapsed = time.perf_counter() - t0
    print(f"    Analysis done in {elapsed:.1f}s ({len(ctx.all_slides)} total slides)")

    if not ctx.all_slides:
        print(f"    No slides produced -- skipping PPTX")
        return None

    # Step 4: Build per-section PPTX
    # Convert AnalysisResult -> SlideContent, preserving slide IDs in titles
    # so you can map each slide back to its module
    slide_contents: list[SlideContent] = []

    # Add section divider
    import calendar
    try:
        month_num = int(month.split(".")[1]) if "." in month else 1
        year = month.split(".")[0] if "." in month else ""
        month_name = calendar.month_name[month_num]
        subtitle = f"{client_name} | {month_name} {year}"
    except (ValueError, IndexError):
        subtitle = client_name

    from ars_analysis.output.deck_builder import _SECTION_LABELS
    section_label = _SECTION_LABELS.get(section, section.title())
    slide_contents.append(SlideContent(
        slide_type="section",
        title=f"{section_label}\n{subtitle}",
        layout_index=LAYOUT_SECTION_ALT,
    ))

    # Convert each result
    for result in ctx.all_slides:
        # Skip overview slides unless we're previewing overview
        result_id = getattr(result, "slide_id", "")
        result_module = getattr(result, "module_id", "") or ""

        # Determine if this result belongs to the current section
        is_overview = any(result_module.startswith(m) or result_id.startswith(("A1", "A3"))
                         for m in SECTION_MODULES.get("overview", []))
        if section != "overview" and is_overview:
            continue

        sc = _result_to_slide(result, ctx_results=ctx.results)
        if sc:
            # Prepend slide ID to title for easy mapping
            original_title = sc.title
            sc.title = f"[{result_id}] {original_title}"
            # Store original in notes for reference
            if not sc.notes_text:
                sc.notes_text = f"Slide ID: {result_id}\nModule: {result_module}\nOriginal title: {original_title}"
            slide_contents.append(sc)

    if len(slide_contents) <= 1:  # only the divider
        print(f"    No chart slides to build PPTX")
        return None

    # Build PPTX
    pptx_path = output_dir / f"real_preview_{section}.pptx"
    print(f"    Building PPTX: {pptx_path.name} ({len(slide_contents)} slides)...")

    try:
        builder = DeckBuilder(str(template_path))
        builder.build(slide_contents, str(pptx_path))
        print(f"    Saved: {pptx_path}")
        return pptx_path
    except Exception as exc:
        print(f"    PPTX build failed: {exc}")
        import traceback
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Real Preview -- per-section PPTX from actual client data"
    )
    parser.add_argument("--odd", type=str, default=None,
                        help="Path to formatted ODD Excel file")
    parser.add_argument("--month", type=str, default=None,
                        help="Month (YYYY.MM) -- used with --csm and --client to auto-find ODD")
    parser.add_argument("--csm", type=str, default=None,
                        help="CSM name (used with --month and --client)")
    parser.add_argument("--client", type=str, default=None,
                        help="Client ID")
    parser.add_argument("--client-name", type=str, default=None,
                        help="Client name (auto-detected from filename if not provided)")
    parser.add_argument("--section", type=str, default=None,
                        help="Section to preview: " + ", ".join(ALL_SECTIONS) + ", or 'all'")
    parser.add_argument("--list", action="store_true",
                        help="List available sections and their modules")
    parser.add_argument("--config", type=str, default=None,
                        help="Path to clients_config.json")
    parser.add_argument("--template", type=str, default=None,
                        help="Path to PPTX template")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: ./real_preview_output)")
    args = parser.parse_args()

    if args.list:
        print("Available sections:")
        for name, mods in SECTION_MODULES.items():
            print(f"  {name}:")
            for m in mods:
                print(f"    - {m}")
        return

    # Resolve ODD file
    if args.odd:
        odd_path = Path(args.odd)
    elif args.month and args.csm and args.client:
        odd_path = _find_odd_file(args.csm, args.month, args.client)
        if not odd_path:
            print(f"ERROR: No ODD file found for {args.csm}/{args.month}/{args.client}")
            sys.exit(1)
        print(f"  Found ODD: {odd_path}")
    else:
        print("ERROR: Provide --odd <path> or --month --csm --client")
        sys.exit(1)

    if not odd_path.exists():
        print(f"ERROR: File not found: {odd_path}")
        sys.exit(1)

    # Resolve client info
    client_id = args.client
    client_name = args.client_name
    if not client_id or not client_name:
        auto_id, auto_name = _parse_client_from_filename(odd_path)
        client_id = client_id or auto_id
        client_name = client_name or auto_name

    # Resolve month
    month = args.month
    if not month:
        # Try to parse from path: .../2026.03/...
        for part in odd_path.parts:
            if "." in part and part[:4].isdigit():
                month = part
                break
    if not month:
        from datetime import datetime
        month = datetime.now().strftime("%Y.%m")

    # Load config
    ccfg = _load_client_config(args.config, client_id)

    # Resolve template
    template_path = _resolve_template(args.template)
    if not template_path:
        print("ERROR: PPTX template not found. Use --template to specify.")
        sys.exit(1)

    # Output dir
    output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).parent / "real_preview_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Validate section
    if not args.section:
        print("ERROR: Specify --section <name> or --section all (or --list to see options)")
        sys.exit(1)

    sections = ALL_SECTIONS if args.section == "all" else [args.section.strip().lower()]
    for s in sections:
        if s not in SECTION_MODULES:
            print(f"ERROR: Unknown section '{s}'. Options: {', '.join(ALL_SECTIONS)}")
            sys.exit(1)

    # Print header
    print()
    print("=" * 70)
    print("  REAL PREVIEW")
    print("=" * 70)
    print(f"  Client:    {client_id} - {client_name}")
    print(f"  Month:     {month}")
    print(f"  ODD:       {odd_path}")
    print(f"  Template:  {template_path}")
    print(f"  Output:    {output_dir}")
    print(f"  Sections:  {', '.join(sections)}")
    print("=" * 70)
    print()

    # Run each section
    results = {}
    for section in sections:
        print(f"  [{section.upper()}]")
        t0 = time.perf_counter()
        pptx = run_section(
            section=section,
            odd_path=odd_path,
            client_id=client_id,
            client_name=client_name,
            month=month,
            ccfg=ccfg,
            template_path=template_path,
            output_dir=output_dir,
        )
        elapsed = time.perf_counter() - t0
        results[section] = pptx
        status = f"OK ({elapsed:.0f}s)" if pptx else f"NO OUTPUT ({elapsed:.0f}s)"
        print(f"  [{section.upper()}] {status}")
        print()

    # Summary
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    for section, pptx in results.items():
        if pptx:
            size_kb = pptx.stat().st_size / 1024
            print(f"    {section:12s}  {pptx.name} ({size_kb:.0f} KB)")
        else:
            print(f"    {section:12s}  (no output)")
    print("=" * 70)
    print()
    print(f"  Output directory: {output_dir}")
    print()


if __name__ == "__main__":
    main()
