"""Tests for SLIDE_MANIFEST.xlsx sync (ensure_manifest_rows, sheet_for_slide).

Mirrors the fixture pattern in test_slide_manifest_editor.py.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import openpyxl

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))
if "ars_analysis" not in sys.modules:
    _pkg = types.ModuleType("ars_analysis")
    _pkg.__path__ = [str(_SCRIPTS_DIR)]
    sys.modules["ars_analysis"] = _pkg

from ars_analysis.output.manifest import (  # noqa: E402
    ensure_manifest_rows,
    load_manifest_decisions,
    read_manifest_rows,
    sheet_for_slide,
    write_manifest_decisions,
)


def _make_workbook(tmp_path: Path) -> Path:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    header = (
        "Slide #", "Slide ID", "Title", "Chart Type",
        "Layout #", "Layout Name", "Slide Type",
        "Keep? (Y/N)", "Your Layout Choice", "Notes",
    )
    ws = wb.create_sheet("TXN - Competition")
    ws.append(header)
    ws.append((1, "TXN-COMP-01", "Competitive Landscape", "bubble", 8, "CUSTOM", "screenshot", "Y", None, None))
    path = tmp_path / "SLIDE_MANIFEST.xlsx"
    wb.save(path)
    return path


def test_sheet_for_slide_txn_codes():
    assert sheet_for_slide("TXN-COMP-12") == "TXN - Competition"
    assert sheet_for_slide("TXN-GEN-01") == "TXN - General"
    assert sheet_for_slide("TXN-MCC-05") == "TXN - MCC Code"
    assert sheet_for_slide("TXN-EXEC-02") == "TXN - Executive"
    # Unknown code still routes to a TXN sheet rather than vanishing
    assert sheet_for_slide("TXN-NEWSEC-01") == "TXN - Newsec"


def test_sheet_for_slide_ars_prefixes():
    assert sheet_for_slide("A7.6a") == "ARS - DCTR"
    assert sheet_for_slide("DCTR-1") == "ARS - DCTR"
    assert sheet_for_slide("A8.1") == "ARS - RegE"
    assert sheet_for_slide("A9.3") == "ARS - Attrition"
    assert sheet_for_slide("A11.1") == "ARS - Value"
    assert sheet_for_slide("A13.Jan26") == "ARS - Mailer"
    assert sheet_for_slide("A18.1") == "ARS - Insights"
    assert sheet_for_slide("S1") == "ARS - Insights"
    assert sheet_for_slide("A1b") == "ARS - Overview"


def test_ensure_manifest_rows_appends_only_missing(tmp_path, monkeypatch):
    path = _make_workbook(tmp_path)
    monkeypatch.setenv("SLIDE_MANIFEST_PATH", str(path))

    manifest_path, added = ensure_manifest_rows([
        {"slide_id": "TXN-COMP-01", "title": "already there"},
        {"slide_id": "TXN-COMP-02", "title": "Threat Quadrant"},
        {"slide_id": "TXN-GEN-01", "title": "Portfolio Overview"},
    ])
    assert manifest_path == str(path)
    assert added == 2

    rows = {r.slide_id: r for r in read_manifest_rows()}
    assert set(rows) == {"TXN-COMP-01", "TXN-COMP-02", "TXN-GEN-01"}
    # Existing decision untouched, new rows blank (= undecided)
    assert rows["TXN-COMP-01"].decision == "Y"
    assert rows["TXN-COMP-02"].decision == ""
    # New rows land on the right per-section sheets
    assert rows["TXN-COMP-02"].sheet == "TXN - Competition"
    assert rows["TXN-GEN-01"].sheet == "TXN - General"
    assert rows["TXN-GEN-01"].title == "Portfolio Overview"


def test_ensure_manifest_rows_is_idempotent(tmp_path, monkeypatch):
    path = _make_workbook(tmp_path)
    monkeypatch.setenv("SLIDE_MANIFEST_PATH", str(path))

    slides = [{"slide_id": "TXN-COMP-02", "title": "Threat Quadrant"}]
    _, first = ensure_manifest_rows(slides)
    _, second = ensure_manifest_rows(slides)
    assert first == 1
    assert second == 0


def test_ensure_manifest_rows_creates_workbook(tmp_path, monkeypatch):
    target = tmp_path / "SLIDE_MANIFEST.xlsx"
    monkeypatch.setenv("SLIDE_MANIFEST_PATH", str(target))
    assert not target.exists()

    manifest_path, added = ensure_manifest_rows([
        {"slide_id": "TXN-COMP-02", "title": "Threat Quadrant"},
        {"slide_id": "A7.1", "title": "DCTR Penetration"},
    ])
    assert manifest_path == str(target)
    assert added == 2
    assert target.exists()

    rows = {r.slide_id: r.sheet for r in read_manifest_rows()}
    assert rows == {"TXN-COMP-02": "TXN - Competition", "A7.1": "ARS - DCTR"}


def test_synced_rows_are_editable_and_loadable(tmp_path, monkeypatch):
    """Round-trip: sync -> write decisions -> load_manifest_decisions."""
    target = tmp_path / "SLIDE_MANIFEST.xlsx"
    monkeypatch.setenv("SLIDE_MANIFEST_PATH", str(target))

    ensure_manifest_rows([
        {"slide_id": "TXN-COMP-02", "title": "Threat Quadrant"},
        {"slide_id": "TXN-COMP-03", "title": "Wallet Share"},
        {"slide_id": "TXN-GEN-01", "title": "Portfolio Overview"},
    ])
    assert write_manifest_decisions({
        "TXN-COMP-02": "Y",
        "TXN-COMP-03": "A",
        "TXN-GEN-01": "N",
    }) == 3

    decisions = load_manifest_decisions()
    assert "TXN-COMP-02" in decisions.main_ids
    assert "TXN-COMP-03" in decisions.aux_ids
    assert "TXN-GEN-01" in decisions.drop_ids
