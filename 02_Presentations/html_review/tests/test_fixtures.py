"""Smoke test: fixtures build without error."""

from html_review.tests.fixtures.tiny_deck import tiny_deck


def test_tiny_deck_builds(tmp_path):
    results = tiny_deck(tmp_path)
    assert len(results) == 3
    assert results[0].section == "attrition"
    assert results[1].excel_data is not None
    assert len(results[2].excel_data) == 2
