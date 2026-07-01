"""The HTML review must render with the same brand as the deck.

It once shipped its own navy (#0F2A4A) and Fraunces/Inter fonts while the PPTX
used CSI navy (#00274C) + Montserrat -- so a reviewer saw two different identities
flipping between the preview and the deck. These tests lock the surfaces together.
"""

from __future__ import annotations

from pathlib import Path

from html_review.builder import build_html, _brand_root_css
from html_review.model import ClientMeta
from html_review.tests.fixtures.tiny_deck import tiny_deck


def _build(tmp_path: Path) -> str:
    results = tiny_deck(tmp_path)
    client = ClientMeta(id="1615", display_name="Cape", month="2026-04",
                        month_display="April 2026", run_date="2026-04-17")
    return build_html(results, client, tmp_path / "out", embed_images=True).read_text()


def test_brand_root_uses_csi_navy_and_montserrat():
    css = _brand_root_css()
    assert "--navy:#00274C" in css
    assert "Montserrat" in css
    assert "Fraunces" not in css and "Inter" not in css


def test_rendered_html_carries_brand_root(tmp_path):
    html = _build(tmp_path)
    assert "--navy:#00274C" in html
    assert "Montserrat" in html


def test_rendered_html_drops_old_editorial_fonts(tmp_path):
    html = _build(tmp_path)
    # The Google Fonts link and static :root must no longer pull Fraunces/Inter.
    assert "family=Fraunces" not in html
    assert "family=Inter" not in html
