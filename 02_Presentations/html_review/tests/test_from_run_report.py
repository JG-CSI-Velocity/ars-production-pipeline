"""Tests for from_run_report.build_html_from_run_report."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from html_review.from_run_report import build_html_from_run_report, _section_for


def _png_bytes() -> bytes:
    # Minimal valid PNG (1x1 transparent)
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xfc"
        b"\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x82\x9a\xb1\xff\x00\x00\x00"
        b"\x00IEND\xaeB`\x82"
    )


def _stage_run(root: Path, csm: str, month: str, client_id: str):
    """Stage a fake completed-analysis directory with run_report.json + chart PNG."""
    analysis_dir = root / csm / month / client_id
    charts_dir = analysis_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    png_path = charts_dir / "dctr_1.png"
    png_path.write_bytes(_png_bytes())

    report_path = analysis_dir / f"{client_id}_{month}_run_report.json"
    report_path.write_text(json.dumps({
        "client_id": client_id,
        "month": month,
        "summary": {"total": 2, "ok": 1, "failed": 0, "no_chart": 1},
        "slides": [
            {
                "slide_id": "DCTR-1", "module_id": "dctr.penetration",
                "success": True, "has_chart": True, "has_excel": False,
                "error": "", "title": "DCTR Overall",
                "chart_path": str(png_path),
                "layout_index": 8, "slide_type": "screenshot",
            },
            {
                "slide_id": "REGE-1", "module_id": "rege.status",
                "success": True, "has_chart": False, "has_excel": False,
                "error": "", "title": "Reg E Overall",
                "chart_path": "", "layout_index": 8, "slide_type": "screenshot",
            },
        ],
    }))


def test_section_for_routes_known_prefixes():
    assert _section_for("DCTR-1", "dctr.penetration") == "dctr"
    assert _section_for("REGE-2", "rege.status") == "rege"
    assert _section_for("A9.11", "attrition.impact") == "attrition"
    assert _section_for("A11.1", "value.analysis") == "value"
    assert _section_for("A12.Jan26", "mailer.response") == "mailer"
    assert _section_for("S1", "insights.synthesis") == "insights"
    assert _section_for("A1.1", "overview.eligibility") == "overview"


def test_section_for_falls_back_to_overview_on_unknown(tmp_path):
    assert _section_for("XYZ-1", "unknown_module") == "overview"


def test_build_html_returns_none_when_no_report(tmp_path):
    analysis_root = tmp_path / "analysis"
    pres_root = tmp_path / "pres"
    analysis_root.mkdir()
    out = build_html_from_run_report(
        csm="Nobody", month="2026.04", client_id="9999",
        completed_analysis_root=analysis_root,
        presentations_root=pres_root,
    )
    assert out is None


def test_build_html_renders_index_for_real_run(tmp_path):
    analysis_root = tmp_path / "analysis"
    pres_root = tmp_path / "pres"
    _stage_run(analysis_root, "TestCSM", "2026.04", "1615")

    out = build_html_from_run_report(
        csm="TestCSM", month="2026.04", client_id="1615",
        completed_analysis_root=analysis_root,
        presentations_root=pres_root,
        embed_images=True,
        client_display_name="AcmeCU",
    )
    assert out is not None
    assert out.name == "index.html"
    assert out.parent.name == "html_review"
    assert out.parent.parent.name == "1615"

    html = out.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "AcmeCU" in html
    # DCTR section should render with the one chart
    assert "DCTR Overall" in html
    # Reg E slide has no chart but should still appear in the rege section
    assert "Reg E Overall" in html


def test_build_html_handles_missing_chart_path_with_glob_fallback(tmp_path):
    """When run_report.json's chart_path is empty but a matching PNG exists in charts/."""
    analysis_root = tmp_path / "analysis"
    pres_root = tmp_path / "pres"
    analysis_dir = analysis_root / "TestCSM" / "2026.04" / "1615"
    charts_dir = analysis_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    # File name contains the slide_id token "dctr_1" after normalization
    png = charts_dir / "dctr_1_overall.png"
    png.write_bytes(_png_bytes())

    report = analysis_dir / "1615_2026.04_run_report.json"
    report.write_text(json.dumps({
        "summary": {},
        "slides": [{
            "slide_id": "DCTR-1", "module_id": "dctr",
            "success": True, "has_chart": True, "has_excel": False,
            "error": "", "title": "DCTR Overall",
            "chart_path": "",  # MISSING -- forces fallback
            "layout_index": 8, "slide_type": "screenshot",
        }],
    }))

    out = build_html_from_run_report(
        csm="TestCSM", month="2026.04", client_id="1615",
        completed_analysis_root=analysis_root,
        presentations_root=pres_root,
        embed_images=True,
    )
    assert out is not None
    # Embedded data-URI confirms the fallback found the PNG
    html = out.read_text(encoding="utf-8")
    assert "data:image/png;base64," in html
