"""Locks the owner's mailer deck shape (2026-06-14): every wave is a two-slide
block (A13 summary + A16.7 combo); the separate A12 swipes/spend slides are
dropped (the combo replaces them); the most recent MAIN_MAILER_MONTHS waves stay
in the main deck and older waves go to the 'Mailer Performance' ancillary deck.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))
if "ars_analysis" not in sys.modules:
    _pkg = types.ModuleType("ars_analysis")
    _pkg.__path__ = [str(_SCRIPTS_DIR)]
    sys.modules["ars_analysis"] = _pkg

from ars_analysis.output.deck_builder import _consolidate_mailer, MAIN_MAILER_MONTHS  # noqa: E402


def _r(slide_id: str) -> SimpleNamespace:
    return SimpleNamespace(slide_id=slide_id)


def _waves(months: list[str]) -> list:
    results = []
    for m in months:
        results += [_r(f"A13.{m}"), _r(f"A16.7.{m}"),
                    _r(f"A12.{m}.Swipes"), _r(f"A12.{m}.Spend")]
    return results


def test_recent_waves_in_main_older_in_ancillary():
    # 8 waves, newest first; cap is MAIN_MAILER_MONTHS (6) -> 6 main, 2 ancillary
    months = ["Apr26", "Feb26", "Dec25", "Oct25", "Aug25", "Jun25", "Apr25", "Feb25"]
    results = _waves(months) + [_r("A13.Agg")]
    main, ancillary = _consolidate_mailer(results)
    main_ids = [r.slide_id for r in main]
    anc_ids = [r.slide_id for r in ancillary]

    for m in months[:MAIN_MAILER_MONTHS]:
        assert f"A13.{m}" in main_ids and f"A16.7.{m}" in main_ids, m
        assert f"A13.{m}" not in anc_ids, m
    for m in months[MAIN_MAILER_MONTHS:]:
        assert f"A13.{m}" in anc_ids and f"A16.7.{m}" in anc_ids, m
        assert f"A13.{m}" not in main_ids, m

    assert "A13.Agg" in main_ids                      # aggregate stays in main
    # combo replaces swipes/spend -- no A12 slides anywhere
    assert not any(sid.startswith("A12.") for sid in main_ids + anc_ids)


def test_every_wave_kept_as_summary_plus_combo():
    """No wave dropped: every wave appears once as summary + combo across both decks."""
    months = ["Apr26", "Mar26", "Feb26", "Jan26", "Dec25", "Nov25",
              "Oct25", "Sep25", "Aug25", "Jul25", "Jun25", "May25"]
    main, ancillary = _consolidate_mailer(_waves(months))
    all_ids = [r.slide_id for r in (main + ancillary)]
    for m in months:
        assert f"A13.{m}" in all_ids, m
        assert f"A16.7.{m}" in all_ids, m
    assert not any(sid.startswith("A12.") for sid in all_ids)


def test_few_waves_all_stay_in_main():
    """When waves <= cap, the ancillary deck is empty."""
    main, ancillary = _consolidate_mailer(_waves(["Apr26", "Feb26", "Dec25"]))
    assert ancillary == []
    main_ids = [r.slide_id for r in main]
    assert "A13.Apr26" in main_ids and "A13.Dec25" in main_ids
