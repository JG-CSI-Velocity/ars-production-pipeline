"""Base types and utilities for deck sections."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# Layout constants are imported from the analysis output module.
# Re-exported here so section modules can import from one place.
LAYOUT_TITLE_DARK = 0
LAYOUT_TITLE = 1
LAYOUT_CONTENT = 2
LAYOUT_CONTENT_ALT = 3
LAYOUT_SECTION = 4
LAYOUT_SECTION_ALT = 5
LAYOUT_SECTION_GRAY = 6
LAYOUT_TITLE_VARIANT = 7
LAYOUT_CUSTOM = 8
LAYOUT_TWO_CONTENT = 9
LAYOUT_COMPARISON = 10
LAYOUT_BLANK = 11
LAYOUT_BULLETS = 12
LAYOUT_PICTURE = 13
LAYOUT_2_PICTURES = 14
LAYOUT_3_PICTURES = 15
LAYOUT_WIDE_TITLE = 16
LAYOUT_TITLE_RPE = 17
LAYOUT_TITLE_ARS = 18
LAYOUT_TITLE_ICS = 19
LAYOUT_MAIL_SUMMARY = 20     # 01_mail_summary -- mailer response + spend/swipe slides


@dataclass
class SectionSpec:
    """Everything the assembler needs to build one section of the deck.

    Each section module defines a register() function that returns one of these.
    The assembler iterates SECTION_REGISTRY in order, building section dividers
    and slides from the spec.
    """

    # Identity
    key: str                          # e.g. "dctr" -- matches analytics folder
    label: str                        # e.g. "How Active Are Debit Cards?"
    divider_layout: int = LAYOUT_TITLE

    # Ownership: which slide ID prefixes belong to this section
    prefixes: list[str] = field(default_factory=list)

    # Layout mapping: slide_id -> (layout_index, slide_type)
    layout_map: dict[str, tuple[int, str]] = field(default_factory=dict)

    # Prefix-based fallback for dynamic slide IDs (e.g. A12.Nov25.Swipes)
    prefix_fallback: Callable[[str], tuple[int, str] | None] | None = None

    # Consolidation rules
    merges: list[tuple[str, str, str]] = field(default_factory=list)
    appendix_ids: set[str] = field(default_factory=set)
    skip_ids: set[str] = field(default_factory=set)

    # Custom consolidation: (results) -> (main, appendix)
    # If None, default_consolidate is used with merges/appendix_ids.
    consolidate: Callable | None = None

    # Absorb slides from another section (slide_id -> donor_section_key)
    absorb_ids: dict[str, str] = field(default_factory=dict)


def default_consolidate(slides, merges, appendix_ids):
    """Merge paired slides and separate appendix slides.

    Returns (main_slides, appendix_slides).
    """
    from dataclasses import dataclass as _dc

    merge_at = {}
    skip_ids = set()
    by_id = {getattr(r, "slide_id", ""): r for r in slides}

    for left_id, right_id, title in merges:
        left = by_id.get(left_id)
        right = by_id.get(right_id)
        if left and right:
            images = []
            chart = getattr(left, "chart_path", None)
            if chart and hasattr(chart, "exists") and chart.exists():
                images.append(str(chart))
            chart = getattr(right, "chart_path", None)
            if chart and hasattr(chart, "exists") and chart.exists():
                images.append(str(chart))

            # Return a lightweight merged record
            @_dc
            class _Merged:
                slide_id: str = left_id
                title: str = title
                images: list = field(default_factory=list)
                slide_type: str = "multi_screenshot"
                layout_index: int = LAYOUT_TWO_CONTENT
                _is_merged: bool = True

            merged = _Merged(
                slide_id=left_id,
                title=title,
                images=images,
            )
            merge_at[left_id] = merged
            skip_ids.add(left_id)
            skip_ids.add(right_id)

    result = []
    appendix_out = []
    for r in slides:
        sid = getattr(r, "slide_id", "")
        if sid in merge_at:
            result.append(merge_at[sid])
        elif sid in skip_ids:
            continue
        elif sid in appendix_ids:
            appendix_out.append(r)
        else:
            result.append(r)

    return result, appendix_out
