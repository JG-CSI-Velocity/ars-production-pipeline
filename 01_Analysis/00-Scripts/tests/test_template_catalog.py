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


import textwrap


def _write_mini_catalog(tmp_path: Path) -> Path:
    """Write a minimal DCTR section file with one family, two branches, two variants per branch."""
    d = tmp_path / "catalog"
    d.mkdir()
    (d / "dctr.md").write_text(textwrap.dedent("""
        # DCTR action titles

        ## Family: `dctr.activation_baseline`
        - **section:** `dctr`
        - **branch_if:** `dctr_1.rate`
        - **branches:**
          - `>= 0.55` → strong
          - `< 0.55` → opportunity
        - **fallback:** "DCTR performance snapshot."

        ### strong / variant 1 (data_first)
        - **template:** "DCTR at {dctr_rate} of {n_eligible} eligible — above the {peer_band} band."
        - **placeholders:**
          | Slot | Path | Format |
          |---|---|---|
          | `dctr_rate` | `dctr_1.rate` | `pct` |
          | `n_eligible` | `dctr_1.eligible_count` | `int` |
          | `peer_band` | `dctr_peer.upper_band_name` | `str` |

        ### strong / variant 2 (context_first)
        - **template:** "With {n_eligible} eligible accounts, DCTR at {dctr_rate} clears the {peer_band} bar."
        - **placeholders:**
          | Slot | Path | Format |
          |---|---|---|
          | `dctr_rate` | `dctr_1.rate` | `pct` |
          | `n_eligible` | `dctr_1.eligible_count` | `int` |
          | `peer_band` | `dctr_peer.upper_band_name` | `str` |

        ### opportunity / variant 1 (action_first)
        - **template:** "Closing the gap to peer median is the clearest near-term lever — DCTR sits at {dctr_rate}."
        - **placeholders:**
          | Slot | Path | Format |
          |---|---|---|
          | `dctr_rate` | `dctr_1.rate` | `pct` |
        """).lstrip(), encoding="utf-8")
    return d


def test_load_parses_one_family_with_two_branches(tmp_path: Path) -> None:
    d = _write_mini_catalog(tmp_path)
    catalog = template_catalog.load_catalog(catalog_dir=d)
    assert "dctr.activation_baseline" in catalog
    fam = catalog["dctr.activation_baseline"]
    assert fam.section == "dctr"
    assert fam.branch_path == "dctr_1.rate"
    assert [label for _, label in fam.branches] == ["strong", "opportunity"]
    assert fam.fallback == "DCTR performance snapshot."
    assert len(fam.variants["strong"]) == 2
    assert len(fam.variants["opportunity"]) == 1
    v = fam.variants["strong"][0]
    assert v.angle == "data_first"
    assert "{dctr_rate}" in v.template
    assert v.placeholders["dctr_rate"] == {"path": "dctr_1.rate", "format": "pct"}
