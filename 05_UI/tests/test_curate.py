"""Tests for GET /api/curate and POST /api/manifest/sync (Curate panel backend)."""

from __future__ import annotations

import json

import openpyxl
import pytest
from fastapi.testclient import TestClient


CSM, MONTH, CLIENT = "TestCSM", "2026.04", "9999"


@pytest.fixture
def run_with_report(app_module, tmp_path):
    """Completed run with run_report.json + one real chart PNG."""
    run_dir = app_module.COMPLETED_ANALYSIS / CSM / MONTH / CLIENT
    charts = run_dir / "charts"
    charts.mkdir(parents=True, exist_ok=True)
    chart_png = charts / "txn_comp_01_landscape.png"
    # 1x1 transparent PNG
    chart_png.write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000d4944415478da63fcffff3f030005fe02fea73581460000000049454e44ae426082"
    ))
    report = {
        "slides": [
            {"slide_id": "TXN-COMP-01", "module_id": "competition", "success": True,
             "has_chart": True, "has_excel": False, "error": "", "title": "Competitive Landscape",
             "chart_path": str(chart_png)},
            {"slide_id": "TXN-COMP-02", "module_id": "competition", "success": True,
             "has_chart": False, "has_excel": True, "error": "", "title": "Threat Quadrant",
             "chart_path": ""},
            {"slide_id": "A7.1", "module_id": "dctr", "success": False,
             "has_chart": False, "has_excel": False, "error": "boom", "title": "DCTR Penetration",
             "chart_path": ""},
        ]
    }
    (run_dir / f"{CLIENT}_{MONTH}_run_report.json").write_text(json.dumps(report))
    return {"dir": run_dir, "chart": chart_png}


@pytest.fixture
def with_manifest(app_module, tmp_path, monkeypatch):
    """SLIDE_MANIFEST.xlsx that already lists one of the run's slides."""
    path = tmp_path / "SLIDE_MANIFEST.xlsx"
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("TXN - Competition")
    ws.append((
        "Slide #", "Slide ID", "Title", "Chart Type", "Layout #",
        "Layout Name", "Slide Type", "Keep? (Y/N)", "Your Layout Choice", "Notes",
    ))
    ws.append((1, "TXN-COMP-01", "Competitive Landscape", None, None, None, None, "Y", None, None))
    wb.save(path)
    monkeypatch.setenv("SLIDE_MANIFEST_PATH", str(path))
    return path


def test_curate_groups_slides_and_joins_decisions(app_module, run_with_report, with_manifest):
    client = TestClient(app_module.app)
    r = client.get(f"/api/curate/{CSM}/{MONTH}/{CLIENT}")
    assert r.status_code == 200
    body = r.json()

    assert body["total_slides"] == 3
    assert body["missing_from_manifest"] == 2  # COMP-02 and A7.1
    assert body["counts"] == {"main": 1, "aux": 0, "drop": 0, "blank": 2}

    sections = {s["name"]: s["slides"] for s in body["sections"]}
    assert set(sections) == {"TXN - Competition", "ARS - DCTR"}

    by_id = {s["slide_id"]: s for sec in sections.values() for s in sec}
    assert by_id["TXN-COMP-01"]["decision"] == "Y"
    assert by_id["TXN-COMP-01"]["in_manifest"] is True
    assert by_id["TXN-COMP-01"]["has_chart"] is True
    assert "/api/download?path=" in by_id["TXN-COMP-01"]["thumb_url"]
    assert by_id["TXN-COMP-02"]["in_manifest"] is False
    assert by_id["TXN-COMP-02"]["thumb_url"] is None
    assert by_id["A7.1"]["error"] == "boom"


def test_curate_thumb_url_serves_the_png(app_module, run_with_report, with_manifest):
    client = TestClient(app_module.app)
    body = client.get(f"/api/curate/{CSM}/{MONTH}/{CLIENT}").json()
    thumb = next(
        s["thumb_url"]
        for sec in body["sections"] for s in sec["slides"]
        if s["thumb_url"]
    )
    img = client.get(thumb)
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/png"
    # inline=true must not force a download
    assert "attachment" not in img.headers.get("content-disposition", "")


def test_curate_404_without_run_report(app_module):
    client = TestClient(app_module.app)
    r = client.get(f"/api/curate/{CSM}/{MONTH}/none")
    assert r.status_code == 404


def test_manifest_sync_appends_missing_rows(app_module, run_with_report, with_manifest):
    client = TestClient(app_module.app)
    r = client.post(f"/api/manifest/sync/{CSM}/{MONTH}/{CLIENT}")
    assert r.status_code == 200
    assert r.json()["added"] == 2

    # Second sync is a no-op
    assert client.post(f"/api/manifest/sync/{CSM}/{MONTH}/{CLIENT}").json()["added"] == 0

    # Now every slide is editable and the curate view reflects it
    body = client.get(f"/api/curate/{CSM}/{MONTH}/{CLIENT}").json()
    assert body["missing_from_manifest"] == 0
    r2 = client.post("/api/manifest", json={"updates": {"TXN-COMP-02": "A", "A7.1": "N"}})
    assert r2.json()["updated"] == 2
    body = client.get(f"/api/curate/{CSM}/{MONTH}/{CLIENT}").json()
    assert body["counts"] == {"main": 1, "aux": 1, "drop": 1, "blank": 0}


def test_manifest_sync_creates_workbook_when_missing(app_module, run_with_report, tmp_path, monkeypatch):
    target = tmp_path / "fresh" / "SLIDE_MANIFEST.xlsx"
    target.parent.mkdir()
    monkeypatch.setenv("SLIDE_MANIFEST_PATH", str(target))

    client = TestClient(app_module.app)
    r = client.post(f"/api/manifest/sync/{CSM}/{MONTH}/{CLIENT}")
    assert r.status_code == 200
    assert r.json() == {"path": str(target), "added": 3}
    assert target.exists()
