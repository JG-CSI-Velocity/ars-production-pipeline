"""Tests for the History (get_recent_runs) and Schedules wiring.

Covers the run-history column data, the schedule fan-out resolver, the
idempotent due-runner, and the pause toggle. Heavy subprocess launching is
monkeypatched so nothing actually shells out.
"""

from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient


# ─── History: get_recent_runs product + date ────────────────────────

def _write_log(app, csm, month, stem, text):
    d = app.LOGS_BASE / csm / month
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.log").write_text(text, encoding="utf-8")


def test_get_recent_runs_parses_product_and_date(app_module):
    app = app_module
    _write_log(
        app, "TestCSM", "2026.04", "1776_20260406_091500",
        "  STEP 2: Running ARS + TXN Analysis\n"
        "Pipeline done: 1776 (CoastHills CU) -- 4/4 steps in 120.0s\n"
        "ARS complete: 88 slides generated\n",
    )
    rows = app.get_recent_runs()
    assert len(rows) == 1
    r = rows[0]
    assert r["product"] == "ARS + TXN"
    assert r["date"] == "2026-04-06 09:15"
    assert r["slides"] == "88"
    assert r["duration"] == "2m 0s"
    assert r["status"] == "complete"


def test_get_recent_runs_defaults_product_and_flags_warning(app_module):
    app = app_module
    _write_log(
        app, "TestCSM", "2026.04", "2001_badstem",
        "some output\nERROR: kaboom\n",
    )
    rows = app.get_recent_runs()
    r = rows[0]
    assert r["product"] == "ARS"          # default when no STEP 2 banner
    assert r["date"] == "2026.04"          # falls back to month folder
    assert r["status"] == "warning"


# ─── Schedule window logic ──────────────────────────────────────────

def test_schedule_is_due_window(app_module):
    app = app_module
    sched = {"start_day": 5, "end_day": 8}
    assert not app._schedule_is_due(sched, 4)
    assert app._schedule_is_due(sched, 5)
    assert app._schedule_is_due(sched, 7)
    assert app._schedule_is_due(sched, 8)
    assert not app._schedule_is_due(sched, 9)


def test_schedule_is_due_legacy_single_day(app_module):
    app = app_module
    assert app._schedule_is_due({"day": 10}, 10)
    assert not app._schedule_is_due({"day": 10}, 11)


# ─── Fan-out resolver ───────────────────────────────────────────────

def _stage_raw_dump(app, csm, month, client_id):
    src = app.ARS_BASE / csm / month
    src.mkdir(parents=True, exist_ok=True)
    (src / f"{client_id}_ODDD.zip").write_bytes(b"")


def _stage_ready(app, csm, month, client_id):
    d = app.READY_FOR_ANALYSIS / csm / month / client_id
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{client_id}-x-ODD.xlsx").write_bytes(b"")


def test_resolve_client_scope(app_module):
    app = app_module
    sched = {"scope": "client", "csm": "TestCSM", "client_id": "1234"}
    assert app._resolve_schedule_clients(sched, "2026.04") == [("TestCSM", "1234")]


def test_resolve_csm_scope_unions_raw_and_ready(app_module):
    app = app_module
    _stage_raw_dump(app, "TestCSM", "2026.04", "1111")
    _stage_ready(app, "TestCSM", "2026.04", "2222")
    sched = {"scope": "csm", "csm": "TestCSM"}
    got = set(app._resolve_schedule_clients(sched, "2026.04"))
    assert got == {("TestCSM", "1111"), ("TestCSM", "2222")}


def test_resolve_all_scope(app_module):
    app = app_module
    _stage_raw_dump(app, "TestCSM", "2026.04", "3333")
    sched = {"scope": "all"}
    got = set(app._resolve_schedule_clients(sched, "2026.04"))
    assert got == {("TestCSM", "3333")}


# ─── Due runner: fires in-window, skips completed, idempotent ────────

def _install_fake_launcher(app, monkeypatch):
    """Replace _launch_pipeline_run with a recorder that also marks the client
    completed for the month -- so the idempotency guard has something to see."""
    calls = []

    def fake(csm, month, client_id, product="ars", **kwargs):
        calls.append((csm, client_id))
        done = app.COMPLETED_ANALYSIS / csm / month / client_id
        done.mkdir(parents=True, exist_ok=True)
        (done / "run_manifest.json").write_text("{}")
        return f"run_{client_id}"

    monkeypatch.setattr(app, "_launch_pipeline_run", fake)
    return calls


def test_run_due_schedules_skips_out_of_window(app_module, monkeypatch):
    app = app_module
    calls = _install_fake_launcher(app, monkeypatch)
    app._save_schedules([{
        "id": "s1", "enabled": True, "scope": "client",
        "csm": "TestCSM", "client_id": "1234",
        "start_day": 5, "end_day": 8, "product": "ars",
    }])
    # day 9 is outside the 5-8 window -> nothing fires
    app._run_due_schedules(datetime(2026, 4, 9, 6, 0))
    assert calls == []


def test_run_due_schedules_fires_and_is_idempotent(app_module, monkeypatch):
    app = app_module
    _stage_raw_dump(app, "TestCSM", "2026.04", "1111")
    _stage_raw_dump(app, "TestCSM", "2026.04", "2222")
    calls = _install_fake_launcher(app, monkeypatch)
    app._save_schedules([{
        "id": "s1", "enabled": True, "scope": "csm", "csm": "TestCSM",
        "start_day": 5, "end_day": 8, "product": "ars",
    }])

    # First in-window day fires both ready clients.
    app._run_due_schedules(datetime(2026, 4, 5, 6, 0))
    assert set(calls) == {("TestCSM", "1111"), ("TestCSM", "2222")}

    # Second in-window day: both are now completed -> nothing new fires.
    calls.clear()
    app._run_due_schedules(datetime(2026, 4, 6, 6, 0))
    assert calls == []


def test_run_due_schedules_respects_disabled(app_module, monkeypatch):
    app = app_module
    _stage_raw_dump(app, "TestCSM", "2026.04", "1111")
    calls = _install_fake_launcher(app, monkeypatch)
    app._save_schedules([{
        "id": "s1", "enabled": False, "scope": "csm", "csm": "TestCSM",
        "start_day": 5, "end_day": 8, "product": "ars",
    }])
    app._run_due_schedules(datetime(2026, 4, 5, 6, 0))
    assert calls == []


def test_dry_run_launches_nothing(app_module, monkeypatch):
    app = app_module
    _stage_raw_dump(app, "TestCSM", "2026.04", "1111")
    calls = _install_fake_launcher(app, monkeypatch)
    app._save_schedules([{
        "id": "s1", "enabled": True, "scope": "csm", "csm": "TestCSM",
        "start_day": 5, "end_day": 8, "product": "ars",
    }])
    results = app._run_due_schedules(datetime(2026, 4, 5, 6, 0), dry_run=True)
    assert calls == []
    assert any(r["status"] == "would-run" for r in results)


# ─── PATCH toggle ───────────────────────────────────────────────────

def test_patch_toggles_enabled(app_module):
    app = app_module
    client = TestClient(app.app)
    created = client.post("/api/schedules", json={
        "scope": "client", "csm": "TestCSM", "client_id": "1234",
        "start_day": 5, "end_day": 8,
    }).json()
    assert created["enabled"] is True

    patched = client.patch(f"/api/schedules/{created['id']}", json={"enabled": False}).json()
    assert patched["enabled"] is False

    listed = client.get("/api/schedules").json()
    assert listed[0]["enabled"] is False


def test_create_schedule_normalizes_window(app_module):
    app = app_module
    client = TestClient(app.app)
    # end before start -> swapped; legacy single day accepted
    created = client.post("/api/schedules", json={
        "scope": "csm", "csm": "TestCSM", "start_day": 8, "end_day": 5,
    }).json()
    assert created["start_day"] == 5
    assert created["end_day"] == 8


def test_create_client_scope_requires_client(app_module):
    app = app_module
    client = TestClient(app.app)
    resp = client.post("/api/schedules", json={"scope": "client", "csm": "TestCSM"})
    assert resp.status_code == 400
