"""start_run must reject products with no analysis backend up front (400),
instead of launching a run that dies ~20 min in on argparse. The Deposits
('dep') card is advertised in the UI but has no backend yet.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_run_rejects_unsupported_product(app_module):
    client = TestClient(app_module.app)
    resp = client.post("/api/run", params={
        "csm": "TestCSM", "month": "2026.06", "client_id": "1776", "product": "dep",
    })
    assert resp.status_code == 400
    assert "not available" in resp.json()["detail"].lower()


def test_run_rejects_garbage_product(app_module):
    client = TestClient(app_module.app)
    resp = client.post("/api/run", params={
        "csm": "TestCSM", "month": "2026.06", "client_id": "1776", "product": "banana",
    })
    assert resp.status_code == 400


def test_run_accepts_supported_product_past_validation(app_module):
    """A supported product passes validation; in the fixture tree it then fails
    at the missing analysis run.py (500) -- proving 'txn' is not blocked at the
    validation gate."""
    client = TestClient(app_module.app)
    resp = client.post("/api/run", params={
        "csm": "TestCSM", "month": "2026.06", "client_id": "1776", "product": "txn",
    })
    assert resp.status_code != 400


def test_products_marks_dep_unavailable(app_module):
    client = TestClient(app_module.app)
    products = client.get("/api/products").json()
    assert products["dep"].get("available") is False
    assert products["ars"].get("available", True) is not False
