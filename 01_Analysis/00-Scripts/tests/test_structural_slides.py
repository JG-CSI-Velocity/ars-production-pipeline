"""Tests for output/structural_slides.py (autonomous decks design §C)."""
from __future__ import annotations

from ars_analysis.output import structural_slides


def test_build_cover_returns_slide_with_lead_finding_subline():
    sc = structural_slides.build_cover(
        client_name="Guardians CU",
        title_date="May 2026",
        ctx_results={"value_summary": {"lead_finding": "DCTR gap to peer is the largest revenue lever this cycle."}},
    )
    assert sc is not None
    assert "Guardians CU" in sc.title
    assert "May 2026" in sc.title
    assert "DCTR gap to peer" in sc.title


def test_build_cover_falls_back_when_lead_finding_missing():
    sc = structural_slides.build_cover(
        client_name="Guardians CU",
        title_date="May 2026",
        ctx_results={},
    )
    assert sc is not None
    assert "Guardians CU" in sc.title
    assert "May 2026" in sc.title
    # Fallback subline still present from the structural template bank.
    assert "Account Revenue Solution" in sc.title or "Performance review" in sc.title


def test_build_dashboard_is_stub_returning_none():
    assert structural_slides.build_dashboard(ctx_results={}) is None


def test_build_agenda_is_stub_returning_none():
    assert structural_slides.build_agenda(ctx_results={}) is None


def test_build_section_opening_is_stub_returning_none():
    assert structural_slides.build_section_opening(section_key="dctr", section_results=[]) is None


def test_build_takeaways_is_stub_returning_none():
    assert structural_slides.build_takeaways(ctx_results={}) is None


def test_preamble_ars_uses_structural_cover():
    """The P01 master title slide must come from build_cover() when ctx_results
    contains a lead finding; falls back to the static subline otherwise."""
    from ars_analysis.output.deck_builder import _build_preamble_slides

    slides_with_finding = _build_preamble_slides(
        client_name="Guardians CU",
        month="2026.05",
        product_mode="ars",
        ctx_results={
            "value_summary": {
                "lead_finding": "DCTR gap to peer is the largest revenue lever this cycle."
            }
        },
    )
    assert "DCTR gap to peer" in slides_with_finding[0].title

    slides_no_finding = _build_preamble_slides(
        client_name="Guardians CU",
        month="2026.05",
        product_mode="ars",
        ctx_results={},
    )
    assert "Account Revenue Solution" in slides_no_finding[0].title
