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
    # Every A12 Swipes/Spend slide is archived, plus the older month's group
    assert set(appendix_ids) == {
        "A12.Jan26.Swipes", "A12.Jan26.Spend",
        "A12.Nov25.Swipes", "A12.Nov25.Spend",
        "A12.Sep25.Swipes", "A12.Sep25.Spend",
        "A13.Sep25", "A16.7.Sep25",
    }
