"""Tests for the SLIDE_MANIFEST.xlsx editor functions (read_manifest_rows,
write_manifest_decisions) -- Wave 4 follow-up.

Mirrors the fixture pattern in test_slide_manifest.py.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import openpyxl
import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))
if "ars_analysis" not in sys.modules:
    _pkg = types.ModuleType("ars_analysis")
    _pkg.__path__ = [str(_SCRIPTS_DIR)]
    sys.modules["ars_analysis"] = _pkg

from ars_analysis.output.manifest import (  # noqa: E402
    ManifestRow,
    load_manifest_decisions,
    read_manifest_rows,
    write_manifest_decisions,
)


def _make_workbook(tmp_path: Path) -> Path:
    """Build a SLIDE_MANIFEST.xlsx fixture with two sheets + decisions."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    header = (
        "Slide #", "Slide ID", "Title", "Chart Type",
        "Layout #", "Layout Name", "Slide Type",
        "Keep? (Y/N)", "Your Layout Choice", "Notes",
    )
    sheets = {
        "ARS - DCTR": [
            ("DCTR-1", "DCTR Overall",   "Y"),
            ("DCTR-2", "Open vs Eligible", ""),
            ("DCTR-7", "Branch DCTR",     "A"),
            ("DCTR-X", "Drop me",         "N"),
        ],
        "ARS - RegE": [
            ("REGE-1", "Reg E Overall",   "Y"),
        ],
        # Skipped sheet (per _SKIP_SHEETS) should be ignored
        "Key": [
            ("IGNORED", "Should not appear", "Y"),
        ],
    }
    for sheet_name, rows in sheets.items():
        ws = wb.create_sheet(sheet_name)
        ws.append(header)
        for sid, title, keep in rows:
            ws.append((1, sid, title, "chart", 2, "CONTENT", "screenshot", keep, None, None))
    path = tmp_path / "SLIDE_MANIFEST.xlsx"
    wb.save(path)
    return path


def test_read_manifest_rows_returns_every_section_row(tmp_path, monkeypatch):
    path = _make_workbook(tmp_path)
    monkeypatch.setenv("SLIDE_MANIFEST_PATH", str(path))

    rows = read_manifest_rows()
    sids = {r.slide_id for r in rows}
    # 4 from DCTR + 1 from RegE; Key sheet skipped
    assert sids == {"DCTR-1", "DCTR-2", "DCTR-7", "DCTR-X", "REGE-1"}
    assert "IGNORED" not in sids


def test_read_manifest_rows_carries_title_and_decision(tmp_path, monkeypatch):
    path = _make_workbook(tmp_path)
    monkeypatch.setenv("SLIDE_MANIFEST_PATH", str(path))

    by_id = {r.slide_id: r for r in read_manifest_rows()}
    assert by_id["DCTR-1"].title == "DCTR Overall"
    assert by_id["DCTR-1"].decision == "Y"
    assert by_id["DCTR-2"].decision == ""
    assert by_id["DCTR-7"].decision == "A"
    assert by_id["DCTR-X"].decision == "N"
    assert by_id["DCTR-1"].sheet == "ARS - DCTR"
    assert by_id["REGE-1"].sheet == "ARS - RegE"


def test_read_manifest_rows_missing_file_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("SLIDE_MANIFEST_PATH", str(tmp_path / "nope.xlsx"))
    assert read_manifest_rows() == []


def test_write_manifest_decisions_updates_existing(tmp_path, monkeypatch):
    path = _make_workbook(tmp_path)
    monkeypatch.setenv("SLIDE_MANIFEST_PATH", str(path))

    updated = write_manifest_decisions({
        "DCTR-1": "A",      # flip Y -> A
        "DCTR-2": "Y",      # blank -> Y
        "DCTR-7": "N",      # A -> N
        "DCTR-X": "",       # N -> blank
        "REGE-1": "Y",      # already Y (still counts as updated)
    })
    assert updated == 5

    decisions = load_manifest_decisions()
    assert "DCTR-2" in decisions.main_ids
    assert "DCTR-1" in decisions.aux_ids
    assert "DCTR-7" in decisions.drop_ids
    assert "DCTR-X" in decisions.undecided_ids
    assert "REGE-1" in decisions.main_ids


def test_write_manifest_decisions_normalizes_aliases(tmp_path, monkeypatch):
    path = _make_workbook(tmp_path)
    monkeypatch.setenv("SLIDE_MANIFEST_PATH", str(path))

    write_manifest_decisions({
        "DCTR-1": "keep",      # -> Y
        "DCTR-2": "appendix",  # -> A
        "DCTR-7": "drop",      # -> N
    })
    decisions = load_manifest_decisions()
    assert "DCTR-1" in decisions.main_ids
    assert "DCTR-2" in decisions.aux_ids
    assert "DCTR-7" in decisions.drop_ids


def test_write_manifest_decisions_no_updates_returns_zero(tmp_path, monkeypatch):
    path = _make_workbook(tmp_path)
    monkeypatch.setenv("SLIDE_MANIFEST_PATH", str(path))
    assert write_manifest_decisions({}) == 0


def test_write_manifest_decisions_ignores_unknown_slide_ids(tmp_path, monkeypatch):
    path = _make_workbook(tmp_path)
    monkeypatch.setenv("SLIDE_MANIFEST_PATH", str(path))

    updated = write_manifest_decisions({"DOES-NOT-EXIST": "Y"})
    assert updated == 0
