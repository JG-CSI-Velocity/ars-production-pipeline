"""Tests for the 2026-08-05 CSM-operator audit fixes.

Covers:
- the config-key fix (clients_config.json is keyed by client ID at the top
  level; the rebuild path must resolve the real client name from it),
- GET /api/active_runs (page-load reattach to in-flight runs),
- GET /api/run_log_tail (path-traversal rejection + tail behavior).
"""

from __future__ import annotations

import importlib
import json

from fastapi.testclient import TestClient


# ─── Config-key fix (audit finding 4) ────────────────────────────────


def _write_top_level_config(app_module, client_id="9999", name="CoastHills CU"):
    app_module.CONFIG_PATH.write_text(json.dumps({
        client_id: {
            "ClientName": name,
            "EligibleStatusCodes": ["A", "D"],
            "EligibleProductCodes": ["DDA"],
        },
    }))


def test_client_meta_resolves_top_level_keyed_config(app_module):
    _write_top_level_config(app_module)
    meta = app_module._client_meta("9999")
    assert meta["ClientName"] == "CoastHills CU"
    assert meta["EligibleStatusCodes"] == ["A", "D"]


def test_client_meta_unknown_client_returns_empty(app_module):
    _write_top_level_config(app_module)
    assert app_module._client_meta("0000") == {}


def test_client_meta_legacy_nested_shape_still_works(app_module):
    app_module.CONFIG_PATH.write_text(json.dumps({
        "clients": {"9999": {"ClientName": "Legacy CU"}},
    }))
    assert app_module._client_meta("9999")["ClientName"] == "Legacy CU"


def test_rebuild_deck_resolves_client_name_from_config(
    app_module, completed_run, monkeypatch
):
    """The rebuild endpoint must build ClientInfo from the top-level-keyed
    config (a `.get("clients", {})` lookup used to always return {} and
    rebuilt decks with client_name = client_id + empty eligibility codes),
    and echo the resolved name in the completion JSON.
    """
    _write_top_level_config(app_module, client_id=completed_run["client_id"])

    app_module._ensure_scripts_importable()
    gen_mod = importlib.import_module("ars_analysis.pipeline.steps.generate")

    captured = {}

    def _fake_rebuild(ctx):
        captured["ctx"] = ctx

    monkeypatch.setattr(gen_mod, "rebuild_deck_from_report", _fake_rebuild)

    client = TestClient(app_module.app)
    r = client.post(
        f"/api/rebuild_deck/{completed_run['csm']}/{completed_run['month']}"
        f"/{completed_run['client_id']}"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    # Completion JSON echoes the resolved name so the UI can show
    # "Rebuilt deck for CoastHills CU" (a bare ID = config lookup failed).
    assert body["client_name"] == "CoastHills CU"

    ctx = captured["ctx"]
    assert ctx.client.client_name == "CoastHills CU"
    assert ctx.client.eligible_stat_codes == ["A", "D"]
    assert ctx.client.eligible_prod_codes == ["DDA"]


# ─── GET /api/active_runs (audit finding 3a) ─────────────────────────


def test_active_runs_lists_only_running(app_module):
    app_module.runs["r_running"] = {
        "status": "running", "client_id": "1776", "csm": "TestCSM",
        "month": "2026.04", "product": "ars",
        "started": "2026-08-05T10:00:00", "progress": 10,
        "current_step": "Module 3/25", "log": [],
    }
    app_module.runs["r_done"] = {
        "status": "complete", "client_id": "1200", "csm": "TestCSM",
        "month": "2026.04", "product": "ars",
        "started": "2026-08-05T08:00:00", "progress": 100,
        "current_step": "done", "log": [],
    }
    client = TestClient(app_module.app)
    r = client.get("/api/active_runs")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    entry = body[0]
    assert entry["run_id"] == "r_running"
    assert entry["kind"] == "ars"
    assert entry["csm"] == "TestCSM"
    assert entry["client_id"] == "1776"
    assert entry["month"] == "2026.04"
    assert entry["started"] == "2026-08-05T10:00:00"
    # The heavy per-run fields (log) must NOT leak into the banner payload.
    assert "log" not in entry


def test_active_runs_empty_when_nothing_running(app_module):
    client = TestClient(app_module.app)
    r = client.get("/api/active_runs")
    assert r.status_code == 200
    assert r.json() == []


# ─── GET /api/run_log_tail (audit finding 6) ─────────────────────────


def _stage_log(app_module, csm="TestCSM", month="2026.04",
               name="1776_20260805_120000_123.log", n_lines=200):
    log_dir = app_module.LOGS_BASE / csm / month
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / name).write_text(
        "\n".join(f"line {i}" for i in range(n_lines)), encoding="utf-8"
    )


def test_run_log_tail_rejects_path_traversal(app_module):
    _stage_log(app_module)
    client = TestClient(app_module.app)
    bad_names = ["..", "../secret", "..\\secret", "a/b.log", "a\\b.log", " "]
    for bad in bad_names:
        r = client.get("/api/run_log_tail",
                       params={"csm": "TestCSM", "month": "2026.04", "name": bad})
        assert r.status_code == 400, f"expected 400 for name={bad!r}"
    # Traversal in the csm / month components is rejected too
    for params in (
        {"csm": "..", "month": "2026.04", "name": "x.log"},
        {"csm": "TestCSM", "month": "..", "name": "x.log"},
    ):
        r = client.get("/api/run_log_tail", params=params)
        assert r.status_code == 400


def test_run_log_tail_returns_last_lines(app_module):
    _stage_log(app_module)
    client = TestClient(app_module.app)
    # Name without .log (the History rows carry log_file.stem) resolves too
    r = client.get("/api/run_log_tail", params={
        "csm": "TestCSM", "month": "2026.04", "name": "1776_20260805_120000_123",
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body["lines"]) == 80
    assert body["lines"][0] == "line 120"
    assert body["lines"][-1] == "line 199"


def test_run_log_tail_missing_log_is_404(app_module):
    client = TestClient(app_module.app)
    r = client.get("/api/run_log_tail", params={
        "csm": "TestCSM", "month": "2026.04", "name": "nope.log",
    })
    assert r.status_code == 404
