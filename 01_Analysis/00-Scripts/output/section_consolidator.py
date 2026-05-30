"""Section dashboard consolidator (Phase T2.3 / issue #152).

Merges three-slide "dashboard" patterns into a single 2-up combo slide
per section. Net effect: main deck shrinks below 25 slides; the
displaced detail slides route to the aux deck via the existing
``ctx.auxiliary_slide_ids`` mechanism.

How patterns are declared
=========================
Each section can register one or more combo patterns in
``COMBO_PATTERNS``. A pattern names:

  * the slide IDs that get folded in (typically a KPI slide, a bar
    chart, and a donut/pie),
  * the ``merged_id`` for the resulting combo slide (used by the
    quality gate + Excel review summary so the combo is identifiable),
  * an optional ``title`` override (otherwise the first slide's title
    wins),
  * which slide_id supplies the **left top** "hero" image, **left
    bottom** chart, and **right** chart -- the 2-up layout SLIDE_DESIGN
    §3 calls for.

Pipeline integration
====================
``deck_builder.build_deck`` calls ``SectionConsolidator.consolidate``
once per section after the per-section ``_section_main`` slice is
assembled. The consolidator returns a ``(kept, deferred)`` pair: kept
are the slides that ship in the main deck (combo + any unaffected
slides); deferred are the original individual slides that should ship
in the aux deck instead. The caller folds ``deferred`` into
``_section_appendix[section_key]`` so the aux mechanism handles them.

When a combo can't be assembled (any of the source slides is missing
or unsuccessful), the consolidator passes the slides through untouched
rather than producing a half-rendered combo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger


# ---------------------------------------------------------------------------
# Pattern declarations
# ---------------------------------------------------------------------------


@dataclass
class ComboPattern:
    """Describes one 2-up merge pattern."""

    section: str
    merged_id: str                # e.g. "DCTR-COMBO-1"
    hero_id: str                  # source slide for the top-left KPI/hero
    left_id: str                  # source slide for the bottom-left chart
    right_id: str                 # source slide for the right chart
    title_override: str | None = None


# Initial set -- conservative, focused on the highest-impact sections.
# Operators can extend this dict from a per-client config later (T3.x).
COMBO_PATTERNS: dict[str, list[ComboPattern]] = {
    "dctr": [
        ComboPattern(
            section="dctr",
            merged_id="DCTR-COMBO-1",
            hero_id="A7.1",       # baseline DCTR KPI
            left_id="A7.7",       # branch ranking
            right_id="A7.8",      # 12-month trend
            title_override="Debit card take rate: current, by branch, and trajectory",
        ),
        ComboPattern(
            section="dctr",
            merged_id="DCTR-COMBO-2",
            hero_id="A7.2",       # peer comparison
            left_id="A11.1",      # value: closing-the-gap
            right_id="DCTR-9",    # branch detail table
            title_override="DCTR vs peer, opportunity, and where to focus",
        ),
    ],
    "rege": [
        ComboPattern(
            section="rege",
            merged_id="REGE-COMBO-1",
            hero_id="A8.1",       # opt-in rate KPI
            left_id="A11.2",      # value: revenue impact
            right_id="A8.6",      # opt-in trajectory
            title_override="Reg E opt-in: current rate, revenue impact, and trend",
        ),
    ],
    "value": [
        # value distributes into dctr/rege per the denominator framework,
        # so no standalone value combos by design.
    ],
    "attrition": [
        ComboPattern(
            section="attrition",
            merged_id="ATTR-COMBO-1",
            hero_id="A9.1",       # overall attrition KPI
            left_id="A9.5",       # driver breakdown
            right_id="A9.10",     # prevention opportunity
            title_override="Attrition: rate, drivers, and prevention upside",
        ),
    ],
    "mailer": [
        ComboPattern(
            section="mailer",
            merged_id="MAIL-COMBO-1",
            hero_id="A12.1",      # campaign reach KPI
            left_id="A13.1",      # response rate
            right_id="A16.1",     # ROI
            title_override="Mailer program: reach, response, ROI",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Consolidator
# ---------------------------------------------------------------------------


@dataclass
class ConsolidationResult:
    """What the consolidator returns to build_deck."""

    main: list[Any] = field(default_factory=list)
    deferred: list[Any] = field(default_factory=list)
    log: list[str] = field(default_factory=list)


class SectionConsolidator:
    """Apply :data:`COMBO_PATTERNS` for one section.

    The caller passes the ordered list of ``SlideContent`` objects for a
    section. The consolidator returns a :class:`ConsolidationResult`:
    ``main`` is what ships in the main deck (combo + non-consolidated
    slides), ``deferred`` is what should ship in the aux deck.
    """

    @staticmethod
    def _index_by_slide_id(slides: list[Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for s in slides:
            sid = getattr(s, "slide_id", None) or _infer_slide_id_from_title(s)
            if sid:
                out[sid] = s
        return out

    @classmethod
    def consolidate(cls, section_key: str, slides: list[Any]) -> ConsolidationResult:
        result = ConsolidationResult(main=list(slides))
        patterns = COMBO_PATTERNS.get(section_key, [])
        if not patterns or not slides:
            return result

        index = cls._index_by_slide_id(slides)
        consumed: set[str] = set()

        # Build any patterns that have all source slides available, in
        # declaration order.
        for pattern in patterns:
            sources = [pattern.hero_id, pattern.left_id, pattern.right_id]
            available = [sid for sid in sources if sid in index]
            if len(available) < 3:
                result.log.append(
                    f"{pattern.merged_id}: skipped (sources {sources} missing {set(sources)-set(available)})"
                )
                continue
            combo = _build_combo_slide(pattern, index)
            if combo is None:
                result.log.append(f"{pattern.merged_id}: skipped (combo build returned None)")
                continue

            # Replace the first source slide with the combo and remove the
            # other two from the main flow (they go to deferred).
            insertion_point = next(
                i for i, s in enumerate(result.main)
                if getattr(s, "slide_id", None) == pattern.hero_id
            )
            result.main[insertion_point] = combo
            for sid in (pattern.left_id, pattern.right_id):
                originals = [s for s in result.main if getattr(s, "slide_id", None) == sid]
                for s in originals:
                    result.main.remove(s)
                    result.deferred.append(s)
                consumed.add(sid)
            consumed.add(pattern.hero_id)
            result.log.append(
                f"{pattern.merged_id}: merged {pattern.hero_id} + {pattern.left_id} + {pattern.right_id}"
            )

        return result


def _build_combo_slide(pattern: ComboPattern, index: dict[str, Any]) -> Any | None:
    """Construct a combo SlideContent.

    Imported lazily so this module doesn't cycle with deck_builder.
    """
    from ars_analysis.output.deck_builder import SlideContent, LAYOUT_TWO_CONTENT

    hero = index.get(pattern.hero_id)
    left = index.get(pattern.left_id)
    right = index.get(pattern.right_id)
    if hero is None or left is None or right is None:
        return None

    hero_images = list(getattr(hero, "images", None) or [])
    left_images = list(getattr(left, "images", None) or [])
    right_images = list(getattr(right, "images", None) or [])
    images = hero_images[:1] + left_images[:1] + right_images[:1]

    title = pattern.title_override or getattr(hero, "title", pattern.merged_id)
    # Merge KPIs from the hero slide; left + right contribute their first
    # KPI as a side note so the populator (T2.2) can pick them up.
    kpis = dict(getattr(hero, "kpis", None) or {})
    for src in (left, right):
        src_kpis = getattr(src, "kpis", None) or {}
        for k, v in list(src_kpis.items())[:1]:
            kpis.setdefault(f"{getattr(src, 'slide_id', '?')}: {k}", v)

    return SlideContent(
        slide_type="combo_2up",
        title=title,
        images=images or None,
        kpis=kpis or None,
        layout_index=LAYOUT_TWO_CONTENT,
        notes_text=getattr(hero, "notes_text", None),
        section_key=pattern.section,
    )


def _infer_slide_id_from_title(slide: Any) -> str:
    """Best-effort recovery if a SlideContent didn't carry an explicit
    slide_id (some legacy code paths don't). Returns "" if nothing can
    be inferred so the consolidator just leaves the slide alone.
    """
    title = getattr(slide, "title", "") or ""
    # Look for a leading "A7.5" / "DCTR-9" / "S1" / etc. token.
    import re
    m = re.match(r"^\s*([A-Z]+[\d.\-A-Za-z]*)\b", title)
    return m.group(1) if m else ""
