"""Integration tests for html_review.builder."""

from pathlib import Path

from html_review.builder import build_html
from html_review.model import ClientMeta
from html_review.tests.fixtures.tiny_deck import tiny_deck


def test_build_html_produces_index_with_3_blocks(tmp_path):
    results = tiny_deck(tmp_path)
    client = ClientMeta(
        id="1615", display_name="Cape & Coast Bank",
        month="2026-04", month_display="April 2026", run_date="2026-04-17",
    )
    out_dir = tmp_path / "out"
    html_path = build_html(results, client, out_dir, embed_images=False)

    assert html_path == out_dir / "index.html"
    text = html_path.read_text()

    # Structure sanity
    assert text.startswith("<!DOCTYPE html>")
    assert "Cape &amp; Coast Bank" in text or "Cape & Coast Bank" in text
    # 3 analysis wrappers
    assert text.count('class="analysis-wrapper"') == 3
    # 1 block has excel_data with 2 sheets -> <select> rendered
    assert 'class="sheet-select"' in text
    # 2 of the 3 blocks have tables -> 2 <details> elements
    assert text.count("<details") == 2


def test_build_html_embed_images_inlines_png(tmp_path):
    results = tiny_deck(tmp_path)
    client = ClientMeta(id="1615", display_name="Cape", month="2026-04",
                        month_display="April 2026", run_date="2026-04-17")
    out_dir = tmp_path / "out"
    html_path = build_html(results, client, out_dir, embed_images=True)
    text = html_path.read_text()
    assert "data:image/png;base64," in text


def test_build_html_no_embed_copies_pngs_to_assets(tmp_path):
    results = tiny_deck(tmp_path)
    client = ClientMeta(id="1615", display_name="Cape", month="2026-04",
                        month_display="April 2026", run_date="2026-04-17")
    out_dir = tmp_path / "out"
    build_html(results, client, out_dir, embed_images=False)
    assets = out_dir / "assets"
    assert assets.exists()
    pngs = list(assets.glob("*.png"))
    assert len(pngs) >= 1
