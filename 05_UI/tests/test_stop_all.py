"""Emergency STOP ALL: kill every in-progress run and its child-process tree.

The launch sites store each live subprocess in ``run_procs`` so ``/api/stop_all``
can terminate it; ``_mark_terminal`` guards the operator's ``stopped`` verdict
against the worker thread that finishes its (now-killed) subprocess and would
otherwise overwrite it with ``error``.
"""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime

from fastapi.testclient import TestClient


def _running(**extra):
    base = {
        "status": "running", "csm": "TestCSM", "month": "2026.04",
        "client_id": "9999", "product": "ars",
        "started": datetime.now().isoformat(), "progress": 10,
        "current_step": "working", "log": [],
    }
    base.update(extra)
    return base


def test_stop_all_noop_when_idle(app_module):
    app_module.runs.clear()
    app_module.run_procs.clear()
    client = TestClient(app_module.app)
    resp = client.post("/api/stop_all")
    assert resp.status_code == 200
    assert resp.json() == {"stopped": 0, "run_ids": []}


def test_stop_all_kills_running_job(app_module):
    app_module.runs.clear()
    app_module.run_procs.clear()

    # A real, long-lived child we expect STOP ALL to kill.
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(120)"],
        **app_module._popen_tree_kwargs(),
    )
    rid = "run_under_test"
    app_module.runs[rid] = _running()
    app_module._register_proc(rid, proc)

    client = TestClient(app_module.app)
    resp = client.post("/api/stop_all")

    assert resp.json() == {"stopped": 1, "run_ids": [rid]}
    assert app_module.runs[rid]["status"] == "stopped"
    assert rid not in app_module.run_procs  # handle cleaned up
    # Child is actually dead (give the OS a beat to reap it).
    for _ in range(50):
        if proc.poll() is not None:
            break
        time.sleep(0.1)
    assert proc.poll() is not None, "child process survived STOP ALL"


def test_mark_terminal_does_not_clobber_stopped(app_module):
    """After STOP ALL flips a run to 'stopped', the worker thread's terminal
    write (which runs when its killed subprocess unblocks) must be ignored."""
    app_module.runs.clear()
    app_module.run_procs.clear()
    rid = "r1"
    app_module.runs[rid] = _running(status="stopped")

    app_module._mark_terminal(rid, "error", progress=100)

    assert app_module.runs[rid]["status"] == "stopped"


def test_mark_terminal_sets_status_when_running(app_module):
    app_module.runs.clear()
    app_module.run_procs.clear()
    rid = "r1"
    app_module.runs[rid] = _running()
    app_module.run_procs[rid] = object()  # sentinel handle to prove cleanup

    app_module._mark_terminal(rid, "complete", progress=100)

    assert app_module.runs[rid]["status"] == "complete"
    assert app_module.runs[rid]["progress"] == 100
    assert "finished" in app_module.runs[rid]
    assert rid not in app_module.run_procs


def test_terminate_proc_noop_on_none_and_dead(app_module):
    assert app_module._terminate_proc(None) is False
    done = subprocess.Popen([sys.executable, "-c", "pass"])
    done.wait()
    assert app_module._terminate_proc(done) is False
