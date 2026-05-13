# tests/test_pipeline_integration.py
from pathlib import Path
import json

from ars_analysis.pipeline import manifest as m
from ars_analysis.pipeline import scorecard
from ars_analysis.pipeline import error_capture as ec


def test_full_lifecycle_writes_manifest_and_scorecard(tmp_path: Path):
    rm = m.RunManifest(
        client_id="1200", client_name="Guardians CU",
        csm="JamesG", month="2026.05", product="combined",
        output_dir=tmp_path,
    )
    rm.start_run()

    # Section 1: success path
    with rm.start_section("Portfolio Overview") as sec:
        sec.set_key_numbers({"accounts": 36840})
        sec.record_script(m.ScriptRecord(name="02_portfolio_data", status=m.ScriptStatus.OK, slides=3))
        sec.set_slides(17)

    # Section 2: a real failure captured through error_capture
    with rm.start_section("Competition") as sec:
        try:
            d = {"a": 1}
            return_val = d[0]  # noqa: F841
        except KeyError as exc:
            import sys
            fields = ec.capture_exception(
                exc, sys.exc_info()[2],
                section_name="Competition",
                script_name="04_build_threat_data",
                client_id="1200", month="2026.05",
                project_marker="tests",
            )
            sec.record_script(m.ScriptRecord(
                name="04_build_threat_data",
                status=m.ScriptStatus.FAILED,
                **fields,
            ))
            sec.flag(m.FlagLevel.WARN, "data anomaly")
        sec.set_slides(38)

    rm.end_run(m.RunStatus.PARTIAL)

    manifest_path = tmp_path / "run_manifest.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text())
    assert data["status"] == "partial"
    assert data["totals"]["scripts_failed"] == 1
    assert data["totals"]["sections_ok"] == 1
    assert data["sections"][1]["scripts"][0]["error_class"] == "KeyError"

    scorecard_path = scorecard.write(rm, tmp_path / "run_scorecard.md")
    text = scorecard_path.read_text()
    assert "Run scorecard" in text
    assert "Portfolio Overview" in text
    assert "Competition" in text
    assert "04_build_threat_data" in text
    assert "Issue body" in text
