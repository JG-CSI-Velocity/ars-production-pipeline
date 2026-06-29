"""Concurrency guard for pipeline runs (#232).

Multiple runs for the same client collide on the one output folder and
run_manifest.json (Windows os.replace -> WinError 5) and garble each other's
logs. The guard refuses a second run for the same {csm, month, client, product}
while one is in progress, while still allowing the ars+txn companion run and
other clients. These tests exercise the pure guard logic directly so they do
not need the FastAPI TestClient (and its httpx dependency).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException


def _running(csm, month, client_id, product, started=None):
    return {
        "status": "running",
        "csm": csm,
        "month": month,
        "client_id": client_id,
        "product": product,
        "started": (started or datetime.now()).isoformat(),
    }


def test_allows_run_when_none_active(app_module):
    app_module.runs.clear()
    # Should not raise.
    app_module._reject_if_run_active("Dan", "2026.06", "1800", "ars")


def test_blocks_duplicate_same_target(app_module):
    app_module.runs.clear()
    app_module.runs["r1"] = _running("Dan", "2026.06", "1800", "ars")
    with pytest.raises(HTTPException) as exc:
        app_module._reject_if_run_active("Dan", "2026.06", "1800", "ars")
    assert exc.value.status_code == 409
    assert "already in progress" in exc.value.detail


def test_allows_companion_product(app_module):
    """ars + txn for the same client is a deliberate parallel run, not a clash."""
    app_module.runs.clear()
    app_module.runs["r1"] = _running("Dan", "2026.06", "1800", "ars")
    app_module._reject_if_run_active("Dan", "2026.06", "1800", "txn")  # no raise


def test_allows_other_client(app_module):
    app_module.runs.clear()
    app_module.runs["r1"] = _running("Dan", "2026.06", "1800", "ars")
    app_module._reject_if_run_active("Dan", "2026.06", "1801", "ars")  # no raise


def test_completed_run_does_not_block(app_module):
    app_module.runs.clear()
    done = _running("Dan", "2026.06", "1800", "ars")
    done["status"] = "complete"
    app_module.runs["done"] = done
    app_module._reject_if_run_active("Dan", "2026.06", "1800", "ars")  # no raise


def test_stale_running_entry_is_released(app_module):
    """A 'running' entry older than STALE_RUN_SECONDS must not wedge the client."""
    app_module.runs.clear()
    old = datetime.now() - timedelta(seconds=app_module.STALE_RUN_SECONDS + 60)
    app_module.runs["stale"] = _running("Dan", "2026.06", "1800", "ars", started=old)
    app_module._reject_if_run_active("Dan", "2026.06", "1800", "ars")  # no raise


def test_formatting_lane_independent(app_module):
    app_module.runs.clear()
    app_module.runs["fmt"] = _running("Dan", "2026.06", "1800", "formatting")
    # An analysis run is a different lane -> allowed.
    app_module._reject_if_run_active("Dan", "2026.06", "1800", "ars")
    # A second formatting run for the same target is blocked.
    with pytest.raises(HTTPException) as exc:
        app_module._reject_if_run_active("Dan", "2026.06", "1800", "formatting")
    assert exc.value.status_code == 409
