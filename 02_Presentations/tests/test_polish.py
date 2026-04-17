"""Integration tests for polish.py against the three committed fixtures."""

from pathlib import Path

from polish import audit_deck, write_report

FIXTURES = Path(__file__).parent / "fixtures"


def test_pristine_audit_yields_no_flags_on_content_slides():
    # Title slide (slide index 1 / 1-based) is exempt -- title headlines
    # are inherently non-consultative and are not meant to be scored.
    result = audit_deck(FIXTURES / "pristine.pptx")
    assert result.deck_level.client_name_present is True
    content_slides = [s for s in result.slides if s.index > 1]
    assert all(s.flagged is False for s in content_slides), (
        "Pristine content slides should not flag: "
        + ", ".join(f"slide {s.index}" for s in content_slides if s.flagged)
    )


def test_moderately_broken_audit_flags_fragment_and_missing_annotation():
    result = audit_deck(FIXTURES / "moderately_broken.pptx")
    flagged = [s for s in result.slides if s.flagged]
    assert len(flagged) >= 2


def test_badly_broken_audit_flags_all_content_slides():
    result = audit_deck(FIXTURES / "badly_broken.pptx")
    flagged = [s for s in result.slides if s.flagged]
    assert len(flagged) >= 2


def test_write_report_produces_markdown(tmp_path):
    result = audit_deck(FIXTURES / "pristine.pptx")
    report_path = tmp_path / "polish_report.md"
    write_report(result, report_path)
    text = report_path.read_text()
    assert text.startswith("# Polish Report")
    assert "Slides:" in text
