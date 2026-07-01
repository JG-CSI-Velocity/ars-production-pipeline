"""Shared test scaffolding for the 05_UI FastAPI app.

The app reads paths from module-level globals computed at import time, so
each test fixture monkey-patches those globals to a tmp_path-rooted
directory tree mirroring the M:\\ARS layout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_UI_DIR = Path(__file__).resolve().parents[1]
if str(_UI_DIR) not in sys.path:
    sys.path.insert(0, str(_UI_DIR))


@pytest.fixture
def app_module(tmp_path, monkeypatch):
    """Import 05_UI/app.py with ARS_BASE pointing at tmp_path.

    Yields the imported module so individual tests can call its functions
    and instantiate TestClient(app_module.app).
    """
    # Build a minimal ARS layout
    formatting = tmp_path / "00_Formatting"
    analysis = tmp_path / "01_Analysis"
    presentations = tmp_path / "02_Presentations"
    config = tmp_path / "03_Config"
    logs = tmp_path / "04_Logs"
    for d in (formatting, analysis, presentations, config, logs):
        d.mkdir(parents=True, exist_ok=True)
    (analysis / "01_Completed_Analysis").mkdir()
    (formatting / "02-Data-Ready for Analysis").mkdir()

    # Empty config files so loaders return empty dicts
    (config / "clients_config.json").write_text(json.dumps({"clients": {}}))
    (config / "ars_config.json").write_text(json.dumps({
        "paths": {"ars_base": str(tmp_path)},
        "csm_sources": {"sources": {"TestCSM": str(tmp_path / "TestCSM")}}
    }))

    # Force a fresh import every test so ARS_BASE rebinds
    for mod in ("app",):
        sys.modules.pop(mod, None)

    monkeypatch.setenv("ARS_TEST_BASE", str(tmp_path))

    import app  # noqa: E402

    # The app already computed its paths from sys.platform / M: drive at import.
    # Override them to tmp_path so endpoints look at our fixture tree.
    app.ARS_BASE = tmp_path
    app.FORMATTING_BASE = formatting
    app.ANALYSIS_BASE = analysis
    app.PRESENTATIONS_BASE = presentations
    app.LOGS_BASE = logs
    app.READY_FOR_ANALYSIS = formatting / "02-Data-Ready for Analysis"
    app.COMPLETED_ANALYSIS = analysis / "01_Completed_Analysis"
    app.CONFIG_PATH = config / "clients_config.json"
    app.ARS_CONFIG_PATH = config / "ars_config.json"

    yield app


@pytest.fixture
def completed_run(app_module, tmp_path):
    """Stage a fake completed-analysis directory with scorecard + audit + manifest."""
    csm = "TestCSM"
    month = "2026.04"
    client_id = "9999"
    run_dir = app_module.COMPLETED_ANALYSIS / csm / month / client_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "charts").mkdir()
    (run_dir / "run_scorecard.md").write_text(
        "# Run Scorecard\n\nVerdict: Ship\n\nNo anomaly flags.\n"
    )
    (run_dir / "rates_audit.csv").write_text(
        "slide_id,title,metric,value,denominator_label,denominator_n,framework_compliant,violation_reason\n"
        "DCTR-1,DCTR Overall,DCTR Rate,30%,Eligible,12345,True,\n"
        "RegE-1,Reg E Overall,Opt-In Rate,45%,Eligible Personal,8000,True,\n"
        "Mystery-1,Mystery,Some Rate,10%,,0,False,label '' not in 4-layer framework\n"
    )
    (run_dir / "run_manifest.json").write_text(json.dumps({
        "status": "ok",
        # Run-level flags (deck QA, "0 closed accounts", denominator law) live here.
        "anomaly_flags": [
            {"level": "warn", "message": "Attrition: 0 of 1,521 accounts have a parsed Date Closed"}
        ],
        "sections": [
            {
                "name": "dctr",
                "anomaly_flags": [
                    {"level": "warn", "message": "branch_scorecard fallback fired"}
                ],
            },
            {"name": "rege", "anomaly_flags": []},
        ],
    }))
    return {"csm": csm, "month": month, "client_id": client_id, "dir": run_dir}
