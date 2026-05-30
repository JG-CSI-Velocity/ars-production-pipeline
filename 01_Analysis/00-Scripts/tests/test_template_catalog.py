"""Tests for output/template_catalog.py (autonomous decks POC)."""
from __future__ import annotations

from pathlib import Path

from ars_analysis.output import template_catalog


def test_load_returns_empty_when_dir_missing(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"
    catalog = template_catalog.load_catalog(catalog_dir=missing)
    assert catalog == {}


def test_load_returns_empty_when_dir_empty(tmp_path: Path) -> None:
    empty = tmp_path / "empty_catalog"
    empty.mkdir()
    catalog = template_catalog.load_catalog(catalog_dir=empty)
    assert catalog == {}
