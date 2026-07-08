"""module_counts must derive its section list from the unified registry, not a
hardcoded list that drifted (it had omitted ICS_cohort and invented 'ics')."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_module_counts_uses_registry(app_module, monkeypatch):
    # Point at the real analytics tree so script counts resolve.
    from pathlib import Path
    real_analytics = Path(app_module.__file__).resolve().parent.parent \
        / "01_Analysis" / "00-Scripts" / "analytics"
    if not real_analytics.exists():
        import pytest
        pytest.skip("analytics tree not available")

    fake = [
        {"section_id": "ars.dctr", "product": "ars"},
        {"section_id": "txn.merchant", "product": "txn"},
        {"section_id": "txn.ICS_cohort", "product": "txn"},  # was omitted before
    ]
    monkeypatch.setattr(app_module, "_list_sections", lambda: fake)
    client = TestClient(app_module.app)
    data = client.get("/api/module_counts").json()

    # ICS_cohort (48 scripts on disk) is now counted; both txn folders exist.
    assert data["txn_sections"] == 2
    assert data["txn_scripts"] > 40
    assert data["ars_modules"] > 0
