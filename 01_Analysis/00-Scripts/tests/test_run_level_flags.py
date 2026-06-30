"""Run-level anomaly flags (RunManifest.flag) reach the manifest and scorecard.

Section-scoped flags already existed (SectionRecorder.flag); some conditions are
run-level (deck QA, "0 closed accounts so the whole attrition section skipped")
and have no owning section. These must still surface to the operator.
"""

from __future__ import annotations

from ars_analysis.pipeline import scorecard
from ars_analysis.pipeline.manifest import FlagLevel, RunManifest, RunStatus


def _manifest(tmp_path):
    return RunManifest(
        client_id="1217", client_name="Pioneer FCU", csm="JamesG",
        month="2026.06", product="ars", output_dir=tmp_path,
    )


def test_flag_appears_in_to_dict(tmp_path):
    rm = _manifest(tmp_path)
    rm.flag(FlagLevel.WARN, "0 of 1,521 accounts have a parsed Date Closed")
    d = rm.to_dict()
    assert d["anomaly_flags"] == [
        {"level": "warn", "message": "0 of 1,521 accounts have a parsed Date Closed"}
    ]


def test_scorecard_renders_run_level_flag_and_caution_verdict(tmp_path):
    rm = _manifest(tmp_path)
    rm.status = RunStatus.OK
    rm.flag(FlagLevel.WARN, "attrition section skipped: 0 closed accounts")
    out = scorecard.write(rm, tmp_path / "run_scorecard.md")
    text = out.read_text(encoding="utf-8")
    assert "## Anomaly flags" in text
    assert "**Run** (warn): attrition section skipped: 0 closed accounts" in text
    assert "Ship with caution" in text


def test_clean_run_has_no_flags_and_ships(tmp_path):
    rm = _manifest(tmp_path)
    rm.status = RunStatus.OK
    text = scorecard.write(rm, tmp_path / "run_scorecard.md").read_text(encoding="utf-8")
    assert "Anomaly flags" not in text
    assert "**Verdict:** Ship" in text
