"""Tests for the SLIDE_MANIFEST.xlsx loader -- output.manifest (#129).

Not to be confused with pipeline.manifest (test_manifest.py), which is the
run-manifest from #121.
"""

from __future__ import annotations

import sys
from pathlib import Path

import openpyxl
import pytest

# Make ars_analysis importable from 00-Scripts (mirrors run.py wiring)
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))
import types

if "ars_analysis" not in sys.modules:
    _pkg = types.ModuleType("ars_analysis")
    _pkg.__path__ = [str(_SCRIPTS_DIR)]
    sys.modules["ars_analysis"] = _pkg

from ars_analysis.output.manifest import (  # noqa: E402
    ManifestDecisions,
    _normalize_decision,
    load_manifest_decisions,
)


def _make_workbook(tmp_path: Path, sheets: dict[str, list[tuple]]) -> Path:
    """Build a tiny SLIDE_MANIFEST.xlsx fixture with the expected schema."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    header = (
        "Slide #", "Slide ID", "Title Pattern", "Chart Type",
        "Layout #", "Layout Name", "Slide Type",
        "Keep? (Y/N)", "Your Layout Choice", "Notes",
    )
    for sheet_name, rows in sheets.items():
        ws = wb.create_sheet(sheet_name)
        ws.append(header)
        for slide_id, keep in rows:
            ws.append((1, slide_id, "title", "chart", 2, "CONTENT", "screenshot", keep, None, None))
    path = tmp_path / "SLIDE_MANIFEST.xlsx"
    wb.save(path)
    return path


class TestNormalizeDecision:
    def test_y_variants(self):
        assert _normalize_decision("Y") == "Y"
        assert _normalize_decision("y") == "Y"
        assert _normalize_decision(" yes ") == "Y"
        assert _normalize_decision("KEEP") == "Y"

    def test_a_variants(self):
        assert _normalize_decision("A") == "A"
        assert _normalize_decision("aux") == "A"
        assert _normalize_decision("APPENDIX") == "A"
        assert _normalize_decision("support") == "A"

    def test_n_variants(self):
        assert _normalize_decision("N") == "N"
        assert _normalize_decision("no") == "N"
        assert _normalize_decision("DROP") == "N"
        assert _normalize_decision("skip") == "N"

    def test_blank_and_unknown(self):
        assert _normalize_decision(None) is None
        assert _normalize_decision("") is None
        assert _normalize_decision("   ") is None
        assert _normalize_decision("maybe") is None


class TestLoader:
    def test_missing_file_returns_empty(self):
        d = load_manifest_decisions(path="/nonexistent/SLIDE_MANIFEST.xlsx")
        assert isinstance(d, ManifestDecisions)
        assert d.is_empty
        assert d.path_used is None

    def test_reads_decisions_per_sheet(self, tmp_path: Path):
        path = _make_workbook(tmp_path, {
            "ARS - Overview": [
                ("A1", "Y"),
                ("A2", "N"),
                ("A3", "A"),
                ("A4", None),
            ],
            "TXN - General": [
                ("TXN-GEN-01", "y"),
                ("TXN-GEN-02", "drop"),
            ],
        })
        d = load_manifest_decisions(path=path)
        assert d.main_ids == frozenset({"A1", "TXN-GEN-01"})
        assert d.aux_ids == frozenset({"A3"})
        assert d.drop_ids == frozenset({"A2", "TXN-GEN-02"})
        assert d.undecided_ids == frozenset({"A4"})
        assert not d.is_empty

    def test_skip_reference_sheets(self, tmp_path: Path):
        path = _make_workbook(tmp_path, {
            "Key": [("KEY-1", "Y")],
            "Layout Reference": [("LR-1", "N")],
            "Support Deck": [("SUP-1", "A")],
            "ARS - Overview": [("A1", "Y")],
        })
        d = load_manifest_decisions(path=path)
        assert d.main_ids == frozenset({"A1"})
        assert d.aux_ids == frozenset()
        assert d.drop_ids == frozenset()

    def test_empty_workbook_is_no_op(self, tmp_path: Path):
        path = _make_workbook(tmp_path, {
            "ARS - Overview": [("A1", None), ("A2", None)],
        })
        d = load_manifest_decisions(path=path)
        assert d.is_empty
        assert d.undecided_ids == frozenset({"A1", "A2"})

    def test_summary_includes_path(self, tmp_path: Path):
        path = _make_workbook(tmp_path, {
            "ARS - Overview": [("A1", "Y"), ("A2", "N")],
        })
        d = load_manifest_decisions(path=path)
        s = d.summary()
        assert "main=1" in s
        assert "dropped=1" in s
        assert str(path) in s

    def test_summary_when_missing(self):
        d = load_manifest_decisions(path="/nonexistent/x.xlsx")
        assert d.summary() == "SLIDE MANIFEST: not found (default = keep all slides)"


class TestWithRepoTemplate:
    def test_template_loads_without_error(self):
        repo_root = Path(__file__).resolve().parents[3]
        template = repo_root / "SLIDE_MANIFEST.template.xlsx"
        if not template.exists():
            pytest.skip("Repo template not present at expected path")
        d = load_manifest_decisions(path=template)
        assert d.error is None
        total = len(d.main_ids) + len(d.aux_ids) + len(d.drop_ids) + len(d.undecided_ids)
        assert total > 0
