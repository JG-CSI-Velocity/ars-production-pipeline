"""Deck assembler -- composes sections into a complete presentation.

This replaces the monolithic build_deck() function from deck_builder.py.
It iterates SECTION_REGISTRY, delegates consolidation to each section,
and feeds the resulting SlideContent list to DeckBuilder for rendering.

Usage:
    from deck_assembler import build_deck
    output_path = build_deck(ctx)
"""

from __future__ import annotations

import calendar
from pathlib import Path

from sections import SECTION_REGISTRY, default_consolidate
from sections._base import SectionSpec, LAYOUT_CUSTOM, LAYOUT_TITLE, LAYOUT_SECTION, LAYOUT_TWO_CONTENT
from sections.preamble import build_preamble_slides, build_executive_kpi

# These imports come from 01_Analysis/00-Scripts/output/.
# On the work PC, ensure the analysis package is on sys.path or installed.
import sys
_ANALYSIS_SCRIPTS = Path(__file__).resolve().parent.parent / "01_Analysis" / "00-Scripts"
if str(_ANALYSIS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_ANALYSIS_SCRIPTS))

from output.deck_builder import DeckBuilder, SlideContent
from output.headlines import generate_headline, insights_key
from output.notes import generate_notes


# Fallback template (ships with the analysis package)
_FALLBACK_TEMPLATE = _ANALYSIS_SCRIPTS / "output" / "template" / "2025-CSI-PPT-Template.pptx"


# ---------------------------------------------------------------------------
# Grouping: assign each slide result to a section
# ---------------------------------------------------------------------------

def _build_prefix_map(registry: list[SectionSpec]) -> dict[str, str]:
    """Build prefix -> section_key mapping from all registered sections."""
    prefix_map = {}
    for spec in registry:
        for prefix in spec.prefixes:
            prefix_map[prefix.lower()] = spec.key
    return prefix_map


def _get_section(slide_id: str, prefix_map: dict[str, str]) -> str:
    """Determine which section owns a slide ID."""
    prefix = slide_id.split("-")[0].split(".")[0].lower()
    return prefix_map.get(prefix, "other")


def _group_by_section(results: list, registry: list[SectionSpec]) -> dict[str, list]:
    """Group AnalysisResult objects by section key."""
    prefix_map = _build_prefix_map(registry)
    sections: dict[str, list] = {}
    for r in results:
        sid = getattr(r, "slide_id", "")
        section = _get_section(sid, prefix_map)
        sections.setdefault(section, []).append(r)
    return sections


# ---------------------------------------------------------------------------
# Result -> SlideContent conversion
# ---------------------------------------------------------------------------

def _build_layout_map(registry: list[SectionSpec]) -> dict[str, tuple[int, str]]:
    """Merge all section layout maps into one lookup."""
    merged = {}
    for spec in registry:
        merged.update(spec.layout_map)
    return merged


def _find_prefix_fallback(slide_id: str, registry: list[SectionSpec]) -> tuple[int, str]:
    """Try each section's prefix_fallback for dynamic slide IDs."""
    for spec in registry:
        if spec.prefix_fallback:
            result = spec.prefix_fallback(slide_id)
            if result:
                return result
    return (LAYOUT_CUSTOM, "screenshot")


def _result_to_slide(result, ctx_results: dict, layout_map: dict, registry: list) -> SlideContent | None:
    """Convert an AnalysisResult to a SlideContent."""
    # Handle pre-built dicts from preamble
    if isinstance(result, dict):
        return SlideContent(
            slide_type=result.get("slide_type", "blank"),
            title=result.get("title", ""),
            images=result.get("images"),
            kpis=result.get("kpis"),
            bullets=result.get("bullets"),
            layout_index=result.get("layout_index", LAYOUT_CUSTOM),
            notes_text=result.get("notes_text"),
        )

    # Handle merged slides (from default_consolidate)
    if getattr(result, "_is_merged", False):
        return SlideContent(
            slide_type=result.slide_type,
            title=result.title,
            images=result.images,
            layout_index=result.layout_index,
        )

    if not getattr(result, "success", True):
        return None

    chart_path = getattr(result, "chart_path", None)
    if not chart_path or not Path(chart_path).exists():
        return None

    slide_id = getattr(result, "slide_id", "")
    title = getattr(result, "title", "")
    kpis = getattr(result, "kpis", None)
    layout_idx = getattr(result, "layout_index", LAYOUT_CUSTOM)
    slide_type = getattr(result, "slide_type", "screenshot")

    # Look up layout from section maps
    if layout_idx == LAYOUT_CUSTOM and slide_type == "screenshot":
        mapped = layout_map.get(slide_id)
        if mapped:
            layout_idx, slide_type = mapped
        else:
            layout_idx, slide_type = _find_prefix_fallback(slide_id, registry)

    images = [str(chart_path)]
    extra = getattr(result, "extra_charts", None)
    if extra:
        images.extend(str(p) for p in extra if p and Path(p).exists())

    bullets = getattr(result, "bullets", None)

    # Generate headline and speaker notes
    notes_text = None
    if ctx_results and slide_id:
        key = insights_key(slide_id)
        insights = ctx_results.get(key, {}) if key else {}
        title = generate_headline(slide_id, insights, fallback_title=title)
        notes_text = generate_notes(slide_id, title, insights, kpis=kpis)

    return SlideContent(
        slide_type=slide_type,
        title=title,
        images=images,
        bullets=bullets,
        kpis=kpis,
        layout_index=layout_idx,
        notes_text=notes_text,
    )


# ---------------------------------------------------------------------------
# Section divider builder
# ---------------------------------------------------------------------------

def _section_divider(label: str, subtitle: str = "", layout_index: int = LAYOUT_TITLE) -> SlideContent:
    """Create a section divider slide."""
    full_title = f"{label}\n{subtitle}" if subtitle else label
    return SlideContent(slide_type="section", title=full_title, layout_index=layout_index)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_deck(ctx) -> Path | None:
    """Build a PowerPoint deck from analysis results.

    Composes sections from SECTION_REGISTRY in SCR narrative arc order:
    1. Build preamble (13 intro slides)
    2. For each section: consolidate, convert, add divider
    3. Collect appendix slides
    4. Render via DeckBuilder
    """
    if not ctx.all_slides:
        return None

    # Resolve template
    template = _FALLBACK_TEMPLATE
    if ctx.settings and hasattr(ctx.settings, "paths"):
        cfg_template = getattr(ctx.settings.paths, "template_path", None)
        if cfg_template and Path(cfg_template).exists():
            template = Path(cfg_template)

    if not template.exists():
        return None

    _notify = ctx.progress_callback
    ctx_results = ctx.results if ctx else {}

    # Build unified layout map from all sections
    layout_map = _build_layout_map(SECTION_REGISTRY)

    # Group slides by section
    grouped = _group_by_section(ctx.all_slides, SECTION_REGISTRY)

    # Build section subtitle
    client_name = ctx.client.client_name
    month = ctx.client.month
    try:
        month_num = int(month.split(".")[1]) if "." in month else 1
        year = month.split(".")[0] if "." in month else ""
        month_name = calendar.month_name[month_num]
        section_subtitle = f"{client_name} | {month_name} {year}"
    except (ValueError, IndexError):
        section_subtitle = client_name

    def _convert_list(items):
        converted = []
        for item in items:
            sc = _result_to_slide(item, ctx_results, layout_map, SECTION_REGISTRY)
            if sc:
                converted.append(sc)
        return converted

    if _notify:
        _notify("Building deck: consolidating slides...")

    # Process each section
    analysis_slides: list[SlideContent] = []
    all_appendix: list[SlideContent] = []

    for spec in SECTION_REGISTRY:
        raw = list(grouped.get(spec.key, []))

        # Absorb slides from donor sections
        for slide_id, donor_key in spec.absorb_ids.items():
            donor = grouped.get(donor_key, [])
            absorbed = [r for r in donor if getattr(r, "slide_id", "") == slide_id]
            raw.extend(absorbed)

        # Filter skip IDs
        raw = [r for r in raw if getattr(r, "slide_id", "") not in spec.skip_ids]

        if not raw:
            continue

        # Consolidate
        if spec.consolidate:
            main, appendix = spec.consolidate(raw)
        else:
            main, appendix = default_consolidate(raw, spec.merges, spec.appendix_ids)

        # Convert to SlideContent
        main_sc = _convert_list(main)
        appendix_sc = _convert_list(appendix)

        if main_sc:
            analysis_slides.append(
                _section_divider(spec.label, subtitle=section_subtitle,
                                 layout_index=spec.divider_layout)
            )
            analysis_slides.extend(main_sc)

        all_appendix.extend(appendix_sc)

    # Summary placeholder
    analysis_slides.append(
        _section_divider("Summary & Key Takeaways", layout_index=LAYOUT_SECTION)
    )

    # Appendix
    other_slides = _convert_list(grouped.get("other", []))
    if all_appendix or other_slides:
        analysis_slides.append(
            _section_divider("Appendix", subtitle=section_subtitle)
        )
        analysis_slides.extend(all_appendix)
        analysis_slides.extend(other_slides)

    # Build preamble
    preamble_dicts = build_preamble_slides(client_name, month)

    # P02 stays as Agenda (no dashboard replacement)

    # Wire preamble placeholders to actual mailer results
    # Use FIRST mailer (sorted ascending) not most recent
    mailer_results = grouped.get("mailer", [])
    mailer_by_id = {getattr(r, "slide_id", ""): r for r in mailer_results}

    _swipes = next(
        (mailer_by_id[k] for k in sorted(mailer_by_id)
         if k.startswith("A12.") and "swipe" in k.lower()),
        None,
    )
    _spend = next(
        (mailer_by_id[k] for k in sorted(mailer_by_id)
         if k.startswith("A12.") and "spend" in k.lower()),
        None,
    )
    _count_trend = mailer_by_id.get("A13.5")

    # Wire results but preserve preamble slide titles
    _preamble_titles = {
        7: "ARS Mailer Revisit \u2013 Swipes",
        8: "ARS Mailer Revisit \u2013 Spend",
        11: "Program Responses to Date",
    }
    for idx, result in [(7, _swipes), (8, _spend), (11, _count_trend)]:
        if result and idx < len(preamble_dicts):
            sc = _result_to_slide(result, ctx_results, layout_map, SECTION_REGISTRY)
            if sc:
                sc.title = _preamble_titles.get(idx, sc.title)
                preamble_dicts[idx] = sc

    # Convert preamble dicts to SlideContent
    preamble_slides = []
    for item in preamble_dicts:
        if isinstance(item, SlideContent):
            preamble_slides.append(item)
        elif isinstance(item, dict):
            sc = _result_to_slide(item, ctx_results, layout_map, SECTION_REGISTRY)
            if sc:
                preamble_slides.append(sc)

    # Combine
    final_slides = preamble_slides + analysis_slides

    if not final_slides:
        return None

    if _notify:
        _notify(f"Building deck: {len(final_slides)} slides...")

    # Render
    ctx.paths.pptx_dir.mkdir(parents=True, exist_ok=True)
    output_path = ctx.paths.pptx_dir / f"{ctx.client.client_id}_{ctx.client.month}_deck.pptx"

    try:
        builder = DeckBuilder(str(template))
        builder.build(final_slides, str(output_path))
        ctx.export_log.append(str(output_path))
        if _notify:
            _notify(f"Deck saved: {output_path.name} ({len(final_slides)} slides)")
        return output_path
    except Exception as exc:
        if _notify:
            _notify(f"Deck build failed: {exc}")
        return None
