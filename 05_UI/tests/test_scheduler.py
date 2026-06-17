"""Pure-logic tests for the schedule execution engine (no subprocesses).

Functions are imported from app.py; claim/ledger dirs are pointed at tmp_path.
"""

import importlib.util
from datetime import datetime
from pathlib import Path

import pytest

_APP = Path(__file__).resolve().parents[1] / "app.py"


def _load_app():
    spec = importlib.util.spec_from_file_location("velocity_app_under_test", _APP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def app(tmp_path, monkeypatch):
    mod = _load_app()
    monkeypatch.setattr(mod, "SCHEDULE_CLAIMS_DIR", tmp_path / "claims")
    monkeypatch.setattr(mod, "RUNS_LEDGER_DIR", tmp_path / "runs")
    return mod


def test_current_report_month(app):
    assert app.current_report_month(datetime(2026, 7, 5)) == "2026.07"
    assert app.current_report_month(datetime(2026, 12, 31)) == "2026.12"


def test_due_schedules_day_boundary(app):
    scheds = [{"id": "s1", "day": 10, "enabled": True}]
    no_claim = lambda sid, m: None
    # before the day -> not due
    assert app.due_schedules(scheds, datetime(2026, 7, 9), no_claim) == []
    # on the day -> due
    assert len(app.due_schedules(scheds, datetime(2026, 7, 10), no_claim)) == 1
    # after the day (catch-up) -> still due
    assert len(app.due_schedules(scheds, datetime(2026, 7, 15), no_claim)) == 1


def test_due_schedules_respects_completed_claim_and_enabled(app):
    scheds = [{"id": "s1", "day": 5, "enabled": True}]
    done = lambda sid, m: {"status": "complete"}
    assert app.due_schedules(scheds, datetime(2026, 7, 10), done) == []
    waiting = lambda sid, m: {"status": "waiting for data"}
    assert len(app.due_schedules(scheds, datetime(2026, 7, 10), waiting)) == 1
    disabled = [{"id": "s2", "day": 5, "enabled": False}]
    assert app.due_schedules(disabled, datetime(2026, 7, 10), lambda s, m: None) == []


def test_try_claim_one_winner_and_blocks_reclaim(app):
    assert app.try_claim("s1", "2026.07") is True          # first wins
    # a completed claim blocks re-claim by a different machine
    app.update_claim("s1", "2026.07", status="complete")
    import os
    os.environ["COMPUTERNAME"] = "OTHER-MACHINE"
    assert app.try_claim("s1", "2026.07") is False
    del os.environ["COMPUTERNAME"]


def test_try_claim_recovers_stale(app):
    import json
    assert app.try_claim("s2", "2026.07") is True
    # write a genuinely-old claim from a dead machine (update_claim would refresh
    # updated_at, so write the file directly)
    app._claim_path("s2", "2026.07").write_text(json.dumps({
        "schedule_id": "s2", "month": "2026.07", "status": "running",
        "claimed_by": "DEAD-MACHINE", "claimed_at": "2000-01-01T00:00:00",
        "updated_at": "2000-01-01T00:00:00", "clients": {},
    }), encoding="utf-8")
    assert app.try_claim("s2", "2026.07") is True          # stale -> re-claimable


def test_clients_for_scope_client(app):
    s = {"scope": "client", "client_id": "1765"}
    assert app.clients_for_scope(s, "2026.07") == ["1765"]


def test_clients_for_scope_csm(app, monkeypatch):
    monkeypatch.setattr(app, "_clients_from_raw_dumps", lambda csm, m: {"1765", "1801"})
    monkeypatch.setattr(app, "_clients_from_folder", lambda base, csm, m: {"1801", "1900"})
    s = {"scope": "csm", "csm": "Jordan"}
    assert app.clients_for_scope(s, "2026.07") == ["1765", "1801", "1900"]


def test_ledger_round_trip(app):
    app.write_run_record({"run_id": "r1", "client_id": "1765", "status": "complete"})
    app.write_run_record({"run_id": "r2", "client_id": "1801", "status": "error"})
    hist = app.read_run_history()
    ids = {r["run_id"] for r in hist}
    assert ids == {"r1", "r2"}
