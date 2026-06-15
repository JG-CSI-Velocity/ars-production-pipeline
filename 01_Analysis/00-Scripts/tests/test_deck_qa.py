"""Tests for the deck QA gate.

Decks are synthesized in-memory so no client data is committed. Each test pins one
defect class that shipped in deck 1759 and must never regress silently again.
"""

from __future__ import annotations

from pptx import Presentation
from pptx.util import Inches

from ars_analysis.output import deck_qa as qa


def _blank_deck():
    prs = Presentation()
    prs._blank_layout = prs.slide_layouts[6]  # "Blank" — not a divider hint
    return prs


def _add_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _add_text(slide, text, left=1.0, top=1.0, width=6.0, height=1.0):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    box.text_frame.text = text
    return box


def _save(prs, tmp_path, name="deck.pptx"):
    path = tmp_path / name
    prs.save(str(path))
    return path


def test_clean_deck_passes(tmp_path):
    prs = _blank_deck()
    slide = _add_slide(prs)
    _add_text(slide, "Quarterly Results", top=0.5, height=0.8)
    _add_text(slide, "Revenue grew steadily across all segments.", top=2.0, width=8.0, height=1.5)
    report = qa.audit_deck(_save(prs, tmp_path))
    assert report["passed"]
    assert report["counts"]["CRITICAL"] == 0
    assert report["counts"]["MAJOR"] == 0


def test_leaked_template_token_is_critical(tmp_path):
    prs = _blank_deck()
    slide = _add_slide(prs)
    _add_text(slide, "Headline")
    _add_text(slide, "{overall_rate:.1f}% across {total_mailed:,} mailed", top=3.0, width=8.0)
    report = qa.audit_deck(_save(prs, tmp_path))
    codes = {f["code"] for f in report["findings"]}
    assert "leaked_token" in codes
    assert report["counts"]["CRITICAL"] >= 1
    assert not report["passed"]


def test_slide_count_explosion_flagged(tmp_path):
    prs = _blank_deck()
    for _ in range(qa.MAX_SLIDES + 1):
        _add_slide(prs)
    report = qa.audit_deck(_save(prs, tmp_path))
    assert any(f["code"] == "slide_count" for f in report["findings"])


def test_text_overflow_flagged(tmp_path):
    prs = _blank_deck()
    slide = _add_slide(prs)
    _add_text(slide, "Title", top=0.5)
    _add_text(slide, "x" * 120, top=2.0, width=1.4, height=0.4)  # the 1.4in mailer stat box
    report = qa.audit_deck(_save(prs, tmp_path))
    assert any(f["code"] == "text_overflow" for f in report["findings"])


def test_empty_body_flagged(tmp_path):
    prs = _blank_deck()
    slide = _add_slide(prs)
    _add_text(slide, "Deposit Trends", top=0.5)  # title only, no body, no chart
    report = qa.audit_deck(_save(prs, tmp_path))
    assert any(f["code"] == "empty_body" for f in report["findings"])


def test_operator_filled_slides_not_flagged(tmp_path):
    """Agenda / Exec Summary / Monthly Revenue / ARS Lift are blank by design."""
    prs = _blank_deck()
    for title in ("Agenda", "Executive Summary",
                  "Monthly Revenue – Last 12 Months", "ARS Lift Matrix"):
        _add_text(_add_slide(prs), title, top=0.5)
    report = qa.audit_deck(_save(prs, tmp_path))
    assert not any(f["code"] == "empty_body" for f in report["findings"])
