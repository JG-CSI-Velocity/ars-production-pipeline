"""Tests for output/template_catalog.py (autonomous decks POC)."""
from __future__ import annotations

import textwrap
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


def test_load_parses_multiple_families_in_one_file(tmp_path: Path) -> None:
    d = tmp_path / "catalog"
    d.mkdir()
    (d / "dctr.md").write_text(textwrap.dedent("""
        # DCTR

        ## Family: `dctr.activation_baseline`
        - **section:** `dctr`
        - **branch_if:** `dctr_1.rate`
        - **branches:**
          - `>= 0.55` → strong
        - **fallback:** "First family fallback."

        ### strong / variant 1 (data_first)
        - **template:** "First family strong."
        - **placeholders:**
          | Slot | Path | Format |
          |---|---|---|
          | `r` | `dctr_1.rate` | `pct` |

        ## Family: `dctr.peer_comparison`
        - **section:** `dctr`
        - **branch_if:** `dctr_peer.gap_pp`
        - **branches:**
          - `>= 0` → ahead
        - **fallback:** "Second family fallback."

        ### ahead / variant 1 (data_first)
        - **template:** "Second family ahead."
        - **placeholders:**
          | Slot | Path | Format |
          |---|---|---|
          | `g` | `dctr_peer.gap_pp` | `pp` |
        """).lstrip(), encoding="utf-8")
    catalog = template_catalog.load_catalog(catalog_dir=d)
    assert set(catalog.keys()) == {"dctr.activation_baseline", "dctr.peer_comparison"}
    fam1 = catalog["dctr.activation_baseline"]
    fam2 = catalog["dctr.peer_comparison"]
    assert fam1.fallback == "First family fallback."
    assert fam2.fallback == "Second family fallback."
    assert list(fam1.variants.keys()) == ["strong"]
    assert list(fam2.variants.keys()) == ["ahead"]
    # No state leakage: fam2 must NOT see fam1's branches or variants.
    assert [label for _, label in fam2.branches] == ["ahead"]
    assert "strong" not in fam2.variants


def test_select_variant_uses_strong_branch_when_rate_above_threshold(tmp_path: Path) -> None:
    d = _write_mini_catalog(tmp_path)
    catalog = template_catalog.load_catalog(catalog_dir=d)
    fam = catalog["dctr.activation_baseline"]
    v = template_catalog.select_variant_from_family(
        fam, ctx_results={"dctr_1": {"rate": 0.62}}, client_id="1615"
    )
    assert v is not None
    assert v.branch == "strong"


def test_select_variant_uses_opportunity_branch_when_rate_below_threshold(tmp_path: Path) -> None:
    d = _write_mini_catalog(tmp_path)
    catalog = template_catalog.load_catalog(catalog_dir=d)
    fam = catalog["dctr.activation_baseline"]
    v = template_catalog.select_variant_from_family(
        fam, ctx_results={"dctr_1": {"rate": 0.20}}, client_id="1615"
    )
    assert v is not None
    assert v.branch == "opportunity"


def test_select_variant_is_stable_across_calls(tmp_path: Path) -> None:
    """Same client + family must always pick the same variant — repeatable reruns."""
    d = _write_mini_catalog(tmp_path)
    catalog = template_catalog.load_catalog(catalog_dir=d)
    fam = catalog["dctr.activation_baseline"]
    ctx = {"dctr_1": {"rate": 0.62}}
    picks = {template_catalog.select_variant_from_family(fam, ctx, "1615").angle for _ in range(10)}
    assert len(picks) == 1


def test_select_variant_returns_none_when_branch_value_missing(tmp_path: Path) -> None:
    d = _write_mini_catalog(tmp_path)
    catalog = template_catalog.load_catalog(catalog_dir=d)
    fam = catalog["dctr.activation_baseline"]
    v = template_catalog.select_variant_from_family(fam, ctx_results={}, client_id="1615")
    assert v is None
