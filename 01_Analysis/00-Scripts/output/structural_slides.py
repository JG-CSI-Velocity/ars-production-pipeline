"""Auto-built structural slides (autonomous decks design §C).

Replaces ``blank`` placeholder ``SlideContent`` objects in the preamble + close
of the deck with data-driven builds. POC scope: ``build_cover()`` only.
The other four builders (dashboard, agenda, section openings, takeaways) are
stubs that return ``None`` so callers can wire them now and the long-tail plan
fills them in without touching deck_builder again.

Any builder that returns ``None`` triggers today's blank-placeholder behavior
upstream in ``deck_builder._build_preamble_slides`` -- non-breaking by design.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from ars_analysis.output.deck_builder import (
    LAYOUT_TITLE_RPE,
    SlideContent,
)


# Structural copy bank. POC ships the cover default inline; the markdown at
# docs/structural_templates.md is reference-only until the long-tail plan
# wires a parser. Bring _FALLBACK_COVER_SUBLINE back when that lands.
_DEFAULT_COVER_SUBLINE = "Account Revenue Solution"


def build_cover(
    *, client_name: str, title_date: str, ctx_results: dict | None
) -> SlideContent | None:
    """Build the deck cover slide.

    Picks a one-sentence lead-finding subline from
    ``ctx_results['value_summary']['lead_finding']`` when available; otherwise
    falls back to the static "Account Revenue Solution" subline (today's
    behavior).
    """
    ctx_results = ctx_results or {}
    lead = None
    vs = ctx_results.get("value_summary", {})
    if isinstance(vs, dict):
        lead = vs.get("lead_finding") or vs.get("subline")
    subline = lead or _DEFAULT_COVER_SUBLINE
    return SlideContent(
        slide_type="title",
        title=f"{client_name}\n{subline} | {title_date}",
        layout_index=LAYOUT_TITLE_RPE,
    )


def build_dashboard(ctx_results: dict | None) -> SlideContent | None:
    """Stub -- long-tail plan implements 3 KPI tiles + 3 lead-finding bullets."""
    return None


def build_agenda(ctx_results: dict | None) -> SlideContent | None:
    """Stub -- long-tail plan implements per-section headline-finding bullets."""
    return None


def build_section_opening(
    *, section_key: str, section_results: list[Any]
) -> SlideContent | None:
    """Stub -- long-tail plan implements 3-bullet section opening from top slides."""
    return None


def build_takeaways(ctx_results: dict | None) -> SlideContent | None:
    """Stub -- long-tail plan implements top-3-by-dollar-magnitude with verbs."""
    return None
