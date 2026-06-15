"""Locks the owner's mailer deck shape (2026-06-11): two main slides per
month -- the A13 summary and its A16.7 combo trajectory -- with the
separate A12 Swipes / Spend slides archived to the appendix.
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

from ars_analysis.output.deck_builder import _consolidate_mailer  # noqa: E402


def _r(slide_id: str) -> SimpleNamespace:
    return SimpleNamespace(slide_id=slide_id)


def test_month_groups_carry_summary_and_combo_only():
    results = [
        _r("A13.Jan26"), _r("A16.7.Jan26"),
        _r("A12.Jan26.Swipes"), _r("A12.Jan26.Spend"),
        _r("A13.Nov25"), _r("A16.7.Nov25"),
        _r("A12.Nov25.Swipes"), _r("A12.Nov25.Spend"),
        _r("A13.Sep25"), _r("A16.7.Sep25"),
        _r("A12.Sep25.Swipes"), _r("A12.Sep25.Spend"),
        _r("A13.Agg"),
    ]
    main, appendix = _consolidate_mailer(results)
    main_ids = [r.slide_id for r in main]
    appendix_ids = [r.slide_id for r in appendix]

    # Two most recent months in main: summary then combo, no A12 metrics
    assert main_ids == [
        "A13.Jan26", "A16.7.Jan26",
        "A13.Nov25", "A16.7.Nov25",
        "A13.Agg",
    ]
    # Older month -> appendix as the same two slides. A12 swipes/spend are
    # dropped entirely (the combo replaces them), nowhere in the deck.
    assert appendix_ids == ["A13.Sep25", "A16.7.Sep25"]
    all_ids = main_ids + appendix_ids
    assert not any(sid.startswith("A12.") for sid in all_ids)


def test_every_mailer_kept_as_summary_plus_combo():
    """No month dropping: every mailer is summary + combo, swipes/spend dropped."""
    months = ["Apr26", "Mar26", "Feb26", "Jan26", "Dec25", "Nov25",
              "Oct25", "Sep25", "Aug25", "Jul25", "Jun25", "May25"]
    results = []
    for m in months:
        results += [_r(f"A13.{m}"), _r(f"A16.7.{m}"),
                    _r(f"A12.{m}.Swipes"), _r(f"A12.{m}.Spend")]
    main, appendix = _consolidate_mailer(results)
    all_ids = [r.slide_id for r in (main + appendix)]
    # Every month appears as exactly its summary + combo
    for m in months:
        assert f"A13.{m}" in all_ids, m
        assert f"A16.7.{m}" in all_ids, m
    # No swipes/spend slides survive anywhere
    assert not any(sid.startswith("A12.") for sid in all_ids)
