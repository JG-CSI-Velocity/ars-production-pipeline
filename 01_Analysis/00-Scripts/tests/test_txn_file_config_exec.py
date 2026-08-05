"""Executes txn_setup/02-file-config.py end to end over a synthetic layout.

Regression for the r2 audit's NameError find: the script's tail (summary
prints, warnings) ran on no test path, so a stale variable reference shipped
and branded every TXN run with a failed setup script. This test execs the
REAL file the way txn_wrapper does (env-driven), so any exec-time error on
the main path fails the suite.
"""

from __future__ import annotations

import io
import contextlib
import os
from pathlib import Path

import pytest

_SCRIPT = (Path(__file__).resolve().parents[1]
           / "analytics" / "txn_setup" / "02-file-config.py")


@pytest.fixture
def txn_layout(tmp_path, monkeypatch):
    """M:\\ARS-shaped tree with dated TXN files around the 2026.06 window."""
    client_dir = (tmp_path / "00_Formatting" / "02-Data-Ready for Analysis"
                  / "TXN Files" / "TestCSM" / "9999")
    client_dir.mkdir(parents=True)
    for name in (
        "9999-trans-06302026.txt",   # in window (report month)
        "9999-trans-07312025.txt",   # in window (oldest kept month)
        "9999-trans-06302025.txt",   # before window -> excluded
        "9999-trans-07312026.txt",   # after report month -> excluded
    ):
        (client_dir / name).write_text("h1\th2\n", encoding="utf-8")
    monkeypatch.setenv("CLIENT_ID", "9999")
    monkeypatch.setenv("CSM", "TestCSM")
    monkeypatch.setenv("MONTH", "2026.06")
    monkeypatch.setenv("ARS_LOCAL_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.chdir(tmp_path)  # ARS_BASE candidate resolution + no CWD litter
    # The script derives config, ARS_BASE, and sibling-module loads from its
    # own __file__ (parents[4] / parent.parent), so mirror the layout in
    # tmp_path: symlink the real sibling modules, return a phantom script
    # path inside the mirror.
    analytics_dir = tmp_path / "01_Analysis" / "00-Scripts" / "analytics"
    (analytics_dir / "txn_setup").mkdir(parents=True)
    real_analytics = _SCRIPT.parent.parent
    for sibling in ("txn_file_detection.py", "txn_cache.py"):
        (analytics_dir / sibling).symlink_to(real_analytics / sibling)
    return analytics_dir / "txn_setup" / "02-file-config.py"


def test_file_config_executes_and_windows_on_report_month(txn_layout):
    ns: dict = {"MONTH": "2026.06", "__file__": str(txn_layout)}
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(_SCRIPT.read_text(encoding="utf-8"),  # noqa: S102
                     str(_SCRIPT), "exec"), ns)

    # The whole script ran -- the summary print at the tail included.
    text = out.getvalue()
    assert "Trailing window:" in text
    assert "2025-07-01 to 2026-07-01" in text

    names = sorted(p.name for p in ns["files_to_load"])
    assert names == ["9999-trans-06302026.txt", "9999-trans-07312025.txt"]


def test_file_config_wall_clock_fallback_without_month(txn_layout, monkeypatch):
    monkeypatch.setenv("MONTH", "")
    ns: dict = {"__file__": str(txn_layout)}
    with contextlib.redirect_stdout(io.StringIO()) as out:
        exec(compile(_SCRIPT.read_text(encoding="utf-8"),  # noqa: S102
                     str(_SCRIPT), "exec"), ns)
    assert "anchoring the trailing" in out.getvalue()  # honest NOTE printed
