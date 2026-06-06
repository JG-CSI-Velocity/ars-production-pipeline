"""Tests for GET /api/run_quality/{csm}/{month}/{client_id}."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_run_quality_returns_empty_shape_for_unknown_client(app_module):
    client = TestClient(app_module.app)
    r = client.get("/api/run_quality/Nobody/2026.04/0000")
    assert r.status_code == 200
    body = r.json()
    # Endpoint never 404s -- it returns empty fields so the UI can degrade.
    assert body["scorecard_md"] == ""
    assert body["rates_audit_rows"] == []
    assert body["denom_violations"] == 0
    assert body["anomaly_flags"] == []
    assert body["manifest_status"] == "unknown"


def test_run_quality_surfaces_scorecard_and_violations(app_module, completed_run):
    client = TestClient(app_module.app)
    r = client.get(
        f"/api/run_quality/{completed_run['csm']}/{completed_run['month']}/{completed_run['client_id']}"
    )
    assert r.status_code == 200
    body = r.json()

    # Scorecard markdown surfaced verbatim
    assert "Run Scorecard" in body["scorecard_md"]
    assert body["scorecard_path"].endswith("run_scorecard.md")

    # rates_audit.csv parsed into a list of dicts
    assert body["rates_audit_path"].endswith("rates_audit.csv")
    assert len(body["rates_audit_rows"]) == 3
    sids = {row["slide_id"] for row in body["rates_audit_rows"]}
    assert sids == {"DCTR-1", "RegE-1", "Mystery-1"}

    # One violation (Mystery-1 has framework_compliant=False)
    assert body["denom_violations"] == 1

    # Anomaly flags pulled from run_manifest.json sections
    assert any(
        f["section"] == "dctr" and "fallback" in f["message"]
        for f in body["anomaly_flags"]
    )
    assert body["manifest_status"] == "ok"


def test_run_quality_handles_missing_rates_audit(app_module, completed_run):
    # Drop rates_audit.csv; scorecard + manifest still present
    (completed_run["dir"] / "rates_audit.csv").unlink()
    client = TestClient(app_module.app)
    r = client.get(
        f"/api/run_quality/{completed_run['csm']}/{completed_run['month']}/{completed_run['client_id']}"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["rates_audit_rows"] == []
    assert body["denom_violations"] == 0
    assert "Run Scorecard" in body["scorecard_md"]  # scorecard still works
