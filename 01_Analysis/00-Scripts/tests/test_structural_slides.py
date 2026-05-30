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
