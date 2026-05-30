"""Regression test for the flat-catalog parser in action_title_populator.

Pins the _KV_RE fix: the populator must correctly extract the `section` field
from the canonical flat catalog at docs/action_title_templates.md, which uses
``- **section:** `overview` `` (colon inside the bold).
"""
from __future__ import annotations

from ars_analysis.output.action_title_populator import load_catalog


def test_flat_catalog_section_field_populates():
    """The populator's parser must read `section` from real catalog markdown."""
    catalog = load_catalog()
    block = catalog.get("overview.portfolio_snapshot")
    assert block is not None, "overview.portfolio_snapshot missing from flat catalog"
    assert block.section == "overview"
