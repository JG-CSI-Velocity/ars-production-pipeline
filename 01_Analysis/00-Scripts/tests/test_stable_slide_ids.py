"""Stable slide ids are keyed to the producing script, not section-wide capture
order, so adding/removing one script doesn't renumber the rest (which desynced
SLIDE_MANIFEST.xlsx / slide_specs between full and scoped runs). Opt-in per
section; default stays positional so unmigrated decks are unchanged."""

from __future__ import annotations

from pathlib import Path

from ars_analysis.analytics.txn_wrapper import _stable_slide_id


def test_stable_id_keyed_to_script():
    p = Path("/x/merchant_08_merchant_volatility_02.png")
    assert _stable_slide_id("MERCH", "merchant", p) == "TXN-MERCH-08_merchant_volatility_02"


def test_stable_id_survives_sibling_removal():
    # Two scripts; removing the FIRST would shift positional NN but not these.
    a = Path("/x/merchant_07_merchant_growth_01.png")
    b = Path("/x/merchant_13_merchant_new_entrants_01.png")
    id_a = _stable_slide_id("MERCH", "merchant", a)
    id_b = _stable_slide_id("MERCH", "merchant", b)
    assert id_a == "TXN-MERCH-07_merchant_growth_01"
    assert id_b == "TXN-MERCH-13_merchant_new_entrants_01"
    # Independent of each other's presence/order.
    assert id_a != id_b


def test_stable_id_handles_missing_prefix():
    p = Path("/x/oddname_01.png")
    assert _stable_slide_id("MERCH", "merchant", p) == "TXN-MERCH-oddname_01"
