"""GET /api/modules lists the unified section registry; POST /api/run?module=
validates the module up front and passes --section to the analysis subprocess."""

from __future__ import annotations

from fastapi.testclient import TestClient

_FAKE_SECTIONS = [
    {"section_id": "txn.merchant", "product": "txn", "display_name": "Merchant Analysis",
     "slide_code": "MERCH", "module_count": None},
    {"section_id": "ars.dctr", "product": "ars", "display_name": "Dctr",
     "slide_code": "", "module_count": 5},
]


def test_modules_endpoint_returns_registry(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "_list_sections", lambda: _FAKE_SECTIONS)
    client = TestClient(app_module.app)
    data = client.get("/api/modules").json()
    assert {m["section_id"] for m in data} == {"txn.merchant", "ars.dctr"}


def test_run_rejects_unknown_module(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "_list_sections", lambda: _FAKE_SECTIONS)
    client = TestClient(app_module.app)
    resp = client.post("/api/run", params={
        "csm": "TestCSM", "month": "2026.06", "client_id": "1776",
        "module": "txn.bogus",
    })
    assert resp.status_code == 400
    assert "unknown module" in resp.json()["detail"].lower()


def test_run_accepts_known_module_past_validation(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "_list_sections", lambda: _FAKE_SECTIONS)
    client = TestClient(app_module.app)
    resp = client.post("/api/run", params={
        "csm": "TestCSM", "month": "2026.06", "client_id": "1776",
        "module": "txn.merchant",
    })
    # Passes module validation; then fails on the missing analysis run.py in
    # the fixture tree (500) -- i.e. not blocked at the module gate.
    assert resp.status_code != 400


def test_run_rejects_unknown_module_in_batch(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "_list_sections", lambda: _FAKE_SECTIONS)
    client = TestClient(app_module.app)
    resp = client.post("/api/run", params={
        "csm": "TestCSM", "month": "2026.06", "client_id": "1776",
        "modules": "txn.merchant,txn.bogus",
    })
    assert resp.status_code == 400
    assert "bogus" in resp.json()["detail"].lower()


def test_run_accepts_known_modules_batch_past_validation(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "_list_sections", lambda: _FAKE_SECTIONS)
    client = TestClient(app_module.app)
    resp = client.post("/api/run", params={
        "csm": "TestCSM", "month": "2026.06", "client_id": "1776",
        "modules": "txn.merchant,ars.dctr",
    })
    # Both known -> passes the batch module gate (fails later on missing run.py).
    assert resp.status_code != 400


def test_list_sections_reads_static_json_and_recovers(app_module, monkeypatch, tmp_path):
    """The empty-picker fix: /api/modules reads a static sections.json (no
    subprocess, can't hang). A missing file returns [] and is NOT cached, so a
    regenerate + Retry recovers."""
    app = app_module
    app._SECTIONS_CACHE.clear()
    sj = tmp_path / "sections.json"
    monkeypatch.setattr(app, "SECTIONS_JSON", sj)

    assert app._list_sections() == []          # missing file -> empty, not cached
    sj.write_text('[{"section_id":"txn.merchant","product":"txn",'
                  '"display_name":"Merchant","slide_code":"MERCH","module_count":null}]')
    got = app._list_sections()                 # regenerated -> recovers
    assert got and got[0]["section_id"] == "txn.merchant"
