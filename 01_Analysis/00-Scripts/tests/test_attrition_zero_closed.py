"""Issue #239: a book with zero closed accounts must surface ONE clear signal.

Client 1217 ran "successfully" but 15 attrition slides failed, each with
"No closed accounts" -- one data condition (Date Closed all-NaT) fanned out into
15 look-alike failures. prepare_attrition_data now raises a single run-level WARN
so the operator sees the cause, not the symptoms. The numbers are unchanged.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from ars_analysis.analytics.attrition._helpers import prepare_attrition_data
from ars_analysis.pipeline.manifest import FlagLevel


class _StubManifest:
    def __init__(self):
        self.flags = []

    def flag(self, level, message):
        self.flags.append((level, message))


def _ctx(df, manifest=None):
    df = df.copy()
    df["Date Opened"] = pd.to_datetime(df["Date Opened"], errors="coerce")
    df["Date Closed"] = pd.to_datetime(df.get("Date Closed"), errors="coerce")
    return SimpleNamespace(data=df, results={}, manifest=manifest)


def test_zero_closed_raises_single_warn_flag():
    rows = [{"Date Opened": "2020-01-01", "Date Closed": None}] * 50  # all open
    manifest = _StubManifest()
    ctx = _ctx(pd.DataFrame(rows), manifest)

    _all, _open, closed = prepare_attrition_data(ctx)

    assert closed.empty
    assert len(manifest.flags) == 1
    level, msg = manifest.flags[0]
    assert level == FlagLevel.WARN
    assert "0 of 50 accounts" in msg
    assert "attrition section" in msg


def test_normal_book_with_closures_raises_no_flag():
    rows = [{"Date Opened": "2020-01-01", "Date Closed": None}] * 40
    rows += [{"Date Opened": "2020-01-01", "Date Closed": "2025-09-15"}] * 10
    manifest = _StubManifest()
    ctx = _ctx(pd.DataFrame(rows), manifest)

    _all, _open, closed = prepare_attrition_data(ctx)

    assert len(closed) == 10
    assert manifest.flags == []


def test_zero_closed_without_manifest_does_not_raise():
    rows = [{"Date Opened": "2020-01-01", "Date Closed": None}] * 3
    ctx = _ctx(pd.DataFrame(rows), manifest=None)
    _all, _open, closed = prepare_attrition_data(ctx)  # must not raise
    assert closed.empty
