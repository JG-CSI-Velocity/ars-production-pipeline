"""Sample Deck Builder -- generates a SAMPLER PPTX with real data + labels.

Every slide from the real analysis gets built with its actual chart/data,
plus a label stamp showing: section, slide_id, layout name, slide type.

JG reviews the sampler, marks which slides to KEEP per section, and those
choices define what the master deck_builder produces.

Usage:
    cd M:\\ARS\\01_Analysis
    python -m ars_analysis.output.sample_deck_builder --month 2026.04 --csm JamesG --client 1776

Or run analysis first, then build sampler from existing results:
    python -m ars_analysis.output.sample_deck_builder --month 2026.04 --csm JamesG --client 1776 --results-only
"""

from __future__ import annotations

import calendar
from pathlib import Path

from loguru import logger

from ars_analysis.pipeline.context import PipelineContext
from ars_analysis.output.deck_builder import (
    DeckBuilder,
    SlideContent,
    _group_by_section,
    _result_to_slide,
    _SECTION_LABELS,
    SECTION_ORDER,
    LAYOUT_SECTION,
    LAYOUT_SECTION_ALT,
    LAYOUT_CUSTOM,
    LAYOUT_CONTENT,
)

# Layout name lookup
_LAYOUT_NAMES = {
    0: "TITLE_DARK", 1: "TITLE", 2: "CONTENT", 3: "CONTENT_ALT",
    4: "SECTION", 5: "SECTION_ALT", 6: "SECTION_GRAY", 7: "TITLE_VARIANT",
    8: "CUSTOM", 9: "TWO_CONTENT", 10: "COMPARISON", 11: "BLANK",
    12: "BULLETS", 13: "PICTURE", 14: "2_PICTURES", 15: "3_PICTURES",
    16: "WIDE_TITLE", 17: "TITLE_RPE", 18: "TITLE_ARS", 19: "TITLE_ICS",
}


def _stamp_title(original_title: str, section: str, idx: int, total: int, result) -> str:
    """Prepend a metadata stamp to the slide title."""
    slide_id = getattr(result, "slide_id", "?")
    layout_idx = getattr(result, "layout_index", LAYOUT_CUSTOM)
    layout_name = _LAYOUT_NAMES.get(layout_idx, str(layout_idx))
    slide_type = getattr(result, "slide_type", "screenshot")

    stamp = f"[{section.upper()} {idx+1}/{total}] id:{slide_id} | layout:{layout_idx} ({layout_name}) | type:{slide_type}"
    return f"{stamp}\n{original_title}"


def build_sample_deck(ctx: PipelineContext, section_filter: str | None = None) -> Path | None:
    """Build a sampler PPTX with real data -- every slide stamped with metadata.

    Args:
        ctx: PipelineContext with analysis results.
        section_filter: If set, only include this section (e.g., 'mailer', 'dctr').
    """
    if not ctx.all_slides:
        logger.warning("No slides to build sample deck from")
        return None

    from ars_analysis.output.deck_builder import _FALLBACK_TEMPLATE
    template = _FALLBACK_TEMPLATE
    if ctx.settings and hasattr(ctx.settings, "paths"):
        cfg_template = getattr(ctx.settings.paths, "template_path", None)
        if cfg_template and Path(cfg_template).exists():
            template = Path(cfg_template)

    if not template.exists():
        logger.warning("Template not found: {name}", name=template.name)
        return None

    sections = _group_by_section(ctx.all_slides)
    _ctx_results = getattr(ctx, 'results', {}) or {}

    # Handle both shared context (client_name attr) and ARS context (client.client_name)
    client_name = getattr(ctx, 'client_name', None) or getattr(getattr(ctx, 'client', None), 'client_name', 'Unknown')
    _month_raw = getattr(ctx, 'analysis_date', None)
    if _month_raw:
        month = _month_raw.strftime("%Y.%m")
    else:
        month = getattr(getattr(ctx, 'client', None), 'month', '')

    try:
        month_num = int(month.split(".")[1]) if "." in month else 1
        year = month.split(".")[0] if "." in month else ""
        month_name = calendar.month_name[month_num]
        subtitle = f"{client_name} | {month_name} {year}"
    except (ValueError, IndexError):
        subtitle = client_name

    all_slides: list[SlideContent] = []

    # Title slide
    all_slides.append(SlideContent(
        slide_type="title",
        title=f"SLIDE SAMPLER\n{subtitle}",
        layout_index=0,
    ))

    # Summary slide
    summary_lines = [f"SLIDE SAMPLER -- Review each slide, note which to KEEP\n"]
    total_all = 0
    for section_key in SECTION_ORDER:
        results = sections.get(section_key, [])
        if results:
            label = _SECTION_LABELS.get(section_key, section_key.title())
            summary_lines.append(f"{label}: {len(results)} slides")
            total_all += len(results)
    other = sections.get("other", [])
    if other:
        summary_lines.append(f"Uncategorized: {len(other)} slides")
        total_all += len(other)
    summary_lines.append(f"\nTOTAL: {total_all} slides")

    all_slides.append(SlideContent(
        slide_type="section",
        title="\n".join(summary_lines),
        layout_index=LAYOUT_SECTION,
    ))

    # Each section (filtered if --section flag used)
    for section_key in SECTION_ORDER:
        if section_filter and section_key != section_filter.lower():
            continue
        results = sections.get(section_key, [])
        if not results:
            continue

        label = _SECTION_LABELS.get(section_key, section_key.title())

        # Section divider
        all_slides.append(SlideContent(
            slide_type="section",
            title=f"SECTION: {label}\n{len(results)} slides\n\nReview each slide. Note which to KEEP.",
            layout_index=LAYOUT_SECTION_ALT,
        ))

        # Each real slide with stamped title
        for i, result in enumerate(results):
            sc = _result_to_slide(result, ctx_results=_ctx_results)
            if sc:
                sc.title = _stamp_title(sc.title, section_key, i, len(results), result)
                all_slides.append(sc)
            else:
                # Slide couldn't render (no chart, failed, etc.) -- show placeholder
                slide_id = getattr(result, "slide_id", "?")
                title_text = getattr(result, "title", "untitled")
                all_slides.append(SlideContent(
                    slide_type="section",
                    title=f"[{section_key.upper()} {i+1}/{len(results)}] id:{slide_id}\nCOULD NOT RENDER\n{title_text}",
                    layout_index=LAYOUT_SECTION,
                ))

    # Other/uncategorized (skip if filtering to a specific section)
    if not section_filter:
        other = sections.get("other", [])
        if other:
            all_slides.append(SlideContent(
                slide_type="section",
                title=f"UNCATEGORIZED\n{len(other)} slides",
                layout_index=LAYOUT_SECTION_ALT,
            ))
            for i, result in enumerate(other):
                sc = _result_to_slide(result, ctx_results=_ctx_results)
                if sc:
                    sc.title = _stamp_title(sc.title, "other", i, len(other), result)
                    all_slides.append(sc)

    # Build PPTX -- handle both ARS internal context and shared context
    if hasattr(ctx, 'pptx_dir'):
        output_dir = ctx.pptx_dir
    elif hasattr(ctx, 'paths') and hasattr(ctx.paths, 'pptx_dir'):
        output_dir = ctx.paths.pptx_dir
    else:
        output_dir = Path(getattr(ctx, 'output_dir', Path('output')))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get client ID and month from whichever context type we have
    _cid = getattr(ctx, 'client_id', None) or getattr(getattr(ctx, 'client', None), 'client_id', 'unknown')
    _month = getattr(ctx, 'analysis_date', None)
    if _month:
        _month = _month.strftime("%Y.%m")
    else:
        _month = getattr(getattr(ctx, 'client', None), 'month', 'unknown')

    suffix = f"_{section_filter.upper()}" if section_filter else ""
    output_path = output_dir / f"{_cid}_{_month}_SAMPLER{suffix}.pptx"

    try:
        builder = DeckBuilder(str(template))
        builder.build(all_slides, str(output_path))
        logger.info("Sample deck: {path} ({n} slides)", path=output_path.name, n=len(all_slides))
        print(f"\n  SAMPLER: {output_path}")
        print(f"  Total slides: {len(all_slides)}")
        print(f"  Real data slides: {total_all}")
        print(f"\n  Review each slide. The stamp at the top shows:")
        print(f"    [SECTION N/total] id:slide_id | layout:N (NAME) | type:TYPE")
        print(f"\n  Mark which slides to KEEP per section.\n")
        return output_path
    except Exception as exc:
        logger.error("Sample deck build failed: {err}", err=exc)
        return None


if __name__ == "__main__":
    import argparse
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    parser = argparse.ArgumentParser(description="Build sampler deck with real data + labels")
    parser.add_argument("--month", required=True, help="Month in YYYY.MM format")
    parser.add_argument("--csm", required=True, help="CSM name")
    parser.add_argument("--client", required=True, help="Client ID")
    parser.add_argument("--results-only", action="store_true",
                        help="Skip analysis, build from existing results")
    args = parser.parse_args()

    from ars_analysis.pipeline.runner import run_pipeline
    from ars_analysis.pipeline.context import PipelineContext

    ctx = PipelineContext(
        client_id=args.client,
        month=args.month,
        csm=args.csm,
    )

    if not args.results_only:
        print(f"\n  Running analysis for {args.client} ({args.month})...")
        print(f"  This may take several minutes.\n")
        run_pipeline(ctx, skip_generate=True)
    else:
        print(f"\n  Loading existing results for {args.client} ({args.month})...\n")
        # Load existing results from completed analysis
        from ars_analysis.pipeline.steps.load import step_load
        from ars_analysis.pipeline.steps.analyze import step_analyze
        step_load(ctx)
        step_analyze(ctx)

    if not ctx.all_slides:
        print("  ERROR: No analysis results. Cannot build sampler.")
        sys.exit(1)

    result = build_sample_deck(ctx)
    if result:
        print(f"  Open the PPTX and mark your keepers!")
    else:
        print("  ERROR: Sampler build failed.")
        sys.exit(1)
