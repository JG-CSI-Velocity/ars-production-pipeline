r"""Run the Slide Sampler -- generates per-section review PPTXs from existing analysis.

Does NOT re-run analysis. Reads charts from a completed analysis run and builds
one small PPTX per section, each slide stamped with metadata.

Usage:
    python run_sampler.py --month 2026.04 --csm JamesG --client 1615
    python run_sampler.py --month 2026.04 --csm JamesG --client 1615 --section mailer
    python run_sampler.py --list-sections
"""

import argparse
import os
import sys
from pathlib import Path
import types
import json

# Same path setup as run.py -- alias wired by the one canonical bootstrap.
_scripts_dir = Path(__file__).parent / "00-Scripts"
sys.path.insert(0, str(_scripts_dir))

import ars_bootstrap

ars_bootstrap.ensure_ars_analysis()

_config_dir = Path(__file__).resolve().parent.parent / "03_Config"
sys.path.insert(0, str(_config_dir))


def _find_analysis_dir(csm, month, client_id):
    """Find the completed analysis directory with charts."""
    if os.name == "nt":
        base = Path(r"M:\ARS\01_Analysis\01_Completed_Analysis")
    else:
        base = Path("/Volumes/M/ARS/01_Analysis/01_Completed_Analysis")

    direct = base / csm / month / client_id
    if direct.exists():
        return direct

    # Fuzzy CSM match
    if base.exists():
        for d in base.iterdir():
            if d.is_dir() and d.name.lower().startswith(csm.lower()):
                candidate = d / month / client_id
                if candidate.exists():
                    return candidate
    return None


def _find_pptx_dir(csm, month, client_id):
    """Get the presentations output directory."""
    if os.name == "nt":
        base = Path(r"M:\ARS\02_Presentations")
    else:
        base = Path("/Volumes/M/ARS/02_Presentations")
    return base / csm / month / client_id


def _find_config():
    """Find clients_config.json."""
    candidates = [
        Path(r"M:\ARS\03_Config\clients_config.json"),
        Path(__file__).parent.parent / "03_Config" / "clients_config.json",
    ]
    for c in candidates:
        try:
            if c.exists():
                return str(c)
        except OSError:
            continue
    return None


def _load_client_name(client_id, config_path):
    """Get client name from config."""
    if not config_path:
        return f"Client {client_id}"
    try:
        cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
        return cfg.get(client_id, {}).get("ClientName", f"Client {client_id}")
    except Exception:
        return f"Client {client_id}"


def main():
    parser = argparse.ArgumentParser(description="Build per-section sampler PPTXs from existing analysis")
    parser.add_argument("--month", type=str, default=None, help="Month in YYYY.MM format")
    parser.add_argument("--csm", type=str, default=None, help="CSM name")
    parser.add_argument("--client", type=str, default=None, help="Client ID")
    parser.add_argument("--section", type=str, default=None,
                        help="Only build this section (e.g., mailer, dctr, rege)")
    parser.add_argument("--list-sections", action="store_true",
                        help="List available sections and exit")
    args = parser.parse_args()

    if args.list_sections:
        from ars_analysis.output.deck_builder import _SECTION_LABELS, SECTION_ORDER
        from ars_analysis.analytics.txn_wrapper import TXN_SECTIONS
        print("\nARS sections:")
        for key in SECTION_ORDER:
            label = _SECTION_LABELS.get(key, key)
            print(f"  {key:15s}  {label}")
        print("\nTXN sections:")
        for key, meta in sorted(TXN_SECTIONS.items(), key=lambda x: x[1].get("order", 999)):
            print(f"  txn.{key:20s}  {meta['display']}")
        print()
        return

    if not args.month or not args.csm or not args.client:
        parser.error("--month, --csm, and --client are required (unless using --list-sections)")

    month = args.month
    csm = args.csm
    client_id = args.client
    config_path = _find_config()
    client_name = _load_client_name(client_id, config_path)

    # Find completed analysis
    analysis_dir = _find_analysis_dir(csm, month, client_id)
    if not analysis_dir:
        print(f"\n  ERROR: No completed analysis found for {client_id} in {month}")
        print(f"  Run analysis first:")
        print(f"    cd M:\\ARS\\01_Analysis")
        print(f"    python run.py --month {month} --csm {csm} --client {client_id}")
        sys.exit(1)

    # Find charts
    chart_dir = analysis_dir / "charts"
    if not chart_dir.exists():
        chart_dir = analysis_dir  # charts might be in the root

    charts = sorted(chart_dir.glob("*.png"))
    if not charts:
        # Try finding PNGs anywhere in the analysis dir
        charts = sorted(analysis_dir.rglob("*.png"))

    if not charts:
        print(f"\n  ERROR: No chart images found in {analysis_dir}")
        print(f"  The analysis may not have generated charts.")
        sys.exit(1)

    pptx_dir = _find_pptx_dir(csm, month, client_id)
    pptx_dir.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 60)
    print("  SLIDE SAMPLER (from existing analysis)")
    print("=" * 60)
    print(f"  Client:    {client_id} - {client_name}")
    print(f"  CSM:       {csm}")
    print(f"  Month:     {month}")
    print(f"  Charts:    {len(charts)} found in {analysis_dir}")
    print(f"  Section:   {args.section or 'ALL (one PPTX per section)'}")
    print(f"  Output:    {pptx_dir}")
    print("=" * 60)
    print()

    # Group charts by section
    from ars_analysis.output.deck_builder import (
        DeckBuilder, SlideContent, _SECTION_LABELS, SECTION_ORDER,
        LAYOUT_SECTION, LAYOUT_SECTION_ALT, LAYOUT_CUSTOM,
        _FALLBACK_TEMPLATE,
    )
    from ars_analysis.analytics.txn_wrapper import TXN_SECTIONS

    # Find template
    template = _FALLBACK_TEMPLATE
    if not template.exists():
        print(f"  ERROR: Template not found at {template}")
        sys.exit(1)

    # --- ARS chart prefix mapping ---
    _PREFIX_TO_SECTION = {
        "A1": "overview", "A3": "overview",
        "DCTR": "dctr", "A7": "dctr",
        "A8": "rege",
        "A9": "attrition",
        "A11": "value",
        "A12": "mailer", "A13": "mailer", "A14": "mailer", "A15": "mailer",
        "A16": "mailer", "A17": "mailer",
        "A18": "insights", "A19": "insights", "A20": "insights",
        "S": "insights",
    }

    # --- TXN section names for prefix matching ---
    _TXN_SECTION_NAMES = set(TXN_SECTIONS.keys())  # general, merchant, mcc_code, etc.

    def _chart_section(chart_path):
        name = chart_path.stem
        name_upper = name.upper()

        # TXN charts: named like general_03_kpi_dashboard_01.png
        # or stored in subdirs like charts/general/general_03_kpi_01.png
        # Check if parent dir is a TXN section name
        if chart_path.parent.name in _TXN_SECTION_NAMES:
            return f"txn.{chart_path.parent.name}"

        # Check if filename starts with a TXN section name
        for sec_name in _TXN_SECTION_NAMES:
            if name.startswith(sec_name + "_") or name.startswith(f"txn_setup_{sec_name}"):
                return f"txn.{sec_name}"

        # ARS charts: named like A7.4_dctr_trajectory.png
        for prefix, section in sorted(_PREFIX_TO_SECTION.items(), key=lambda x: -len(x[0])):
            if name_upper.startswith(prefix):
                return section

        return "other"

    # Build section labels including TXN
    _ALL_LABELS = dict(_SECTION_LABELS)
    for sec_name, meta in TXN_SECTIONS.items():
        _ALL_LABELS[f"txn.{sec_name}"] = f"TXN: {meta['display']}"

    sections = {}
    for chart in charts:
        sec = _chart_section(chart)
        sections.setdefault(sec, []).append(chart)

    # Layout name lookup
    _LAYOUT_NAMES = {
        0: "TITLE_DARK", 1: "TITLE", 2: "CONTENT", 3: "CONTENT_ALT",
        4: "SECTION", 5: "SECTION_ALT", 6: "SECTION_GRAY", 7: "TITLE_VARIANT",
        8: "CUSTOM", 9: "TWO_CONTENT", 10: "COMPARISON", 11: "BLANK",
        12: "BULLETS", 13: "PICTURE", 16: "WIDE_TITLE",
        17: "TITLE_RPE", 18: "TITLE_ARS", 19: "TITLE_ICS",
    }

    # Layout options to show per chart -- each chart rendered in these layouts
    PREVIEW_LAYOUTS = [
        (LAYOUT_CUSTOM, "CUSTOM (8)", "screenshot"),
        (2, "CONTENT (2)", "screenshot"),        # LAYOUT_CONTENT
        (9, "TWO_CONTENT (9)", "screenshot"),     # LAYOUT_TWO_CONTENT
        (16, "WIDE_TITLE (16)", "screenshot"),    # LAYOUT_WIDE_TITLE
    ]

    # Also check SLIDE_LAYOUT_MAP for any chart-specific overrides
    from ars_analysis.output.deck_builder import SLIDE_LAYOUT_MAP

    # Build per-section PPTXs
    sections_to_build = [args.section.lower()] if args.section else list(sections.keys())

    for sec_key in sections_to_build:
        sec_charts = sections.get(sec_key, [])
        if not sec_charts:
            print(f"  {sec_key}: no charts found, skipping")
            continue

        label = _ALL_LABELS.get(sec_key, sec_key.replace("txn.", "TXN: ").title())

        slides = []

        # Title slide
        slides.append(SlideContent(
            slide_type="section",
            title=(
                f"SAMPLER: {label}\n"
                f"{client_id} - {client_name} | {month}\n"
                f"{len(sec_charts)} charts x {len(PREVIEW_LAYOUTS)} layouts = {len(sec_charts) * len(PREVIEW_LAYOUTS)} slides\n\n"
                f"Each chart shown in {len(PREVIEW_LAYOUTS)} layout options.\n"
                f"Note the layout name on each slide and pick your favorite."
            ),
            layout_index=LAYOUT_SECTION_ALT,
        ))

        # Each chart shown in multiple layouts
        for i, chart_path in enumerate(sec_charts):
            chart_name = chart_path.stem

            # Check if SLIDE_LAYOUT_MAP has a specific mapping for this chart
            mapped = SLIDE_LAYOUT_MAP.get(chart_name.split('_')[0], None)
            mapped_note = f" [MAPPED: layout {mapped[0]} ({_LAYOUT_NAMES.get(mapped[0], '?')})]" if mapped else ""

            # Divider for this chart
            slides.append(SlideContent(
                slide_type="section",
                title=(
                    f"CHART {i+1}/{len(sec_charts)}: {chart_name}\n"
                    f"Section: {sec_key.upper()}{mapped_note}\n\n"
                    f"The next {len(PREVIEW_LAYOUTS)} slides show this chart in different layouts.\n"
                    f"Pick which layout works best."
                ),
                layout_index=LAYOUT_SECTION,
            ))

            # Same chart in each layout option
            for layout_idx, layout_name, slide_type in PREVIEW_LAYOUTS:
                stamp = (
                    f"[{sec_key.upper()} {i+1}/{len(sec_charts)}] "
                    f"LAYOUT: {layout_name} | "
                    f"file: {chart_name}"
                )

                slides.append(SlideContent(
                    slide_type=slide_type,
                    title=f"{stamp}\n{chart_name.replace('_', ' ')}",
                    images=[str(chart_path)],
                    layout_index=layout_idx,
                ))

        # Build PPTX
        suffix = sec_key.upper()
        out_path = pptx_dir / f"{client_id}_{month}_SAMPLER_{suffix}.pptx"

        total_slides = len(sec_charts) * (len(PREVIEW_LAYOUTS) + 1) + 1  # charts * (layouts + divider) + title
        try:
            builder = DeckBuilder(str(template))
            builder.build(slides, str(out_path))
            print(f"  {sec_key:15s}  {len(sec_charts):3d} charts  {total_slides:4d} slides  ->  {out_path.name}")
        except Exception as exc:
            print(f"  {sec_key:15s}  ERROR: {exc}")

    print()
    print("=" * 60)
    print(f"  DONE! Sampler files in: {pptx_dir}")
    print()
    print(f"  Each slide has a stamp: [SECTION N/total] file:chart_name | layout:N")
    print(f"  Mark which slides to KEEP per section.")
    print("=" * 60)


if __name__ == "__main__":
    main()
