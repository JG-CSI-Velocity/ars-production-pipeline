"""Structural lint: rendered HTML has the required markers and no regressions."""

from pathlib import Path

from html_review.builder import build_html
from html_review.model import ClientMeta
from html_review.tests.fixtures.tiny_deck import tiny_deck


def _build(tmp_path: Path) -> str:
    results = tiny_deck(tmp_path)
    client = ClientMeta(id="1615", display_name="Cape", month="2026-04",
                        month_display="April 2026", run_date="2026-04-17")
    path = build_html(results, client, tmp_path / "out", embed_images=True)
    return path.read_text()


def test_no_unresolved_jinja_markers(tmp_path):
    text = _build(tmp_path)
    assert "{{" not in text, "unresolved jinja expression"
    assert "{%" not in text, "unresolved jinja statement"


def test_selection_tray_markup_present(tmp_path):
    text = _build(tmp_path)
    assert 'id="selection-count"' in text
    assert 'id="btn-export"' in text
    assert 'id="btn-clear"' in text


def test_print_css_embedded(tmp_path):
    text = _build(tmp_path)
    assert "@media print" in text
    assert "body.exporting" in text


def test_no_external_script_or_stylesheet_tags(tmp_path):
    text = _build(tmp_path)
    assert 'src="http' not in text, "external script reference -- should be inlined"
    assert 'href="http' not in text, "external stylesheet reference -- should be inlined"


def test_sidebar_lists_sections_in_canonical_order(tmp_path):
    # tiny_deck has 'attrition' (x2) and 'mailer' (x1). Order should follow
    # SECTION_ORDER: attrition (position 4) then mailer (position 6).
    text = _build(tmp_path)
    attrition_idx = text.find("#section-attrition")
    mailer_idx = text.find("#section-mailer")
    assert attrition_idx != -1 and mailer_idx != -1
    assert attrition_idx < mailer_idx
