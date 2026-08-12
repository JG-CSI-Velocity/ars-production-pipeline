"""The three run-launching endpoints share ONE orchestration body.

Audit 2026-08-12 found three hand-copied format+analyze variants in app.py
that had drifted apart -- the scheduler had lost the ODD hand-off, env
forwarding, and staleness tracking, so a scheduled run was silently not the
same operation as a clicked run. These tests pin the consolidation.
"""
import inspect

from fastapi.testclient import TestClient


def test_single_subprocess_launch_site(app_module):
    # Every pipeline subprocess goes through _stream_subprocess. A second
    # Popen call site means a new hand-copied orchestration variant.
    src = inspect.getsource(app_module)
    assert src.count("subprocess.Popen(") == 1


def test_generate_button_uses_shared_pipeline(app_module):
    src = inspect.getsource(app_module.start_run)
    assert "_run_full_pipeline" in src


def test_scheduler_uses_shared_pipeline(app_module, tmp_path, monkeypatch):
    # Functional: trigger a schedule and assert it dispatches through
    # _run_full_pipeline with fresh-format semantics and the schedule's
    # formatting extras -- the same body the Generate button uses.
    monkeypatch.setattr(app_module, "SCHEDULES_FILE", tmp_path / "schedules.json")

    calls = []

    def _fake_pipeline(run_id, csm, month, client_id, product, **kwargs):
        calls.append({"csm": csm, "client_id": client_id,
                      "product": product, **kwargs})

    monkeypatch.setattr(app_module, "_run_full_pipeline", _fake_pipeline)

    client = TestClient(app_module.app)
    created = client.post("/api/schedules", json={
        "csm": "TestCSM", "client_id": "9999",
        "product": "ars", "extras": "trans",
    }).json()

    resp = client.post(f"/api/schedules/{created['id']}/run")
    assert resp.status_code == 200

    # The worker thread may still be flushing; the dispatch itself is
    # synchronous enough to observe after the response in TestClient runs.
    import time
    for _ in range(50):
        if calls:
            break
        time.sleep(0.02)

    assert len(calls) == 1
    assert calls[0]["csm"] == "TestCSM"
    assert calls[0]["client_id"] == "9999"
    assert calls[0]["always_format"] is True
    assert calls[0]["format_extras"] == ["--with-trans"]
