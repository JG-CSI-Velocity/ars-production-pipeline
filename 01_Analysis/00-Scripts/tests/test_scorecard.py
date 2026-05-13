from pathlib import Path
import json
from ars_analysis.pipeline import manifest as m
from ars_analysis.pipeline import scorecard


def _build_fixture_manifest(tmp_path: Path) -> m.RunManifest:
    rm = m.RunManifest(
        client_id="1200", client_name="Guardians CU",
        csm="JamesG", month="2026.05", product="combined",
        output_dir=tmp_path,
    )
    rm.start_run()
    with rm.start_section("Portfolio Overview") as sec:
        sec.set_slides(17)
        sec.set_key_numbers({"accounts": 36840, "active": 22229})
    with rm.start_section("Competition") as sec:
        sec.set_slides(38)
        sec.set_key_numbers({"credit_unions": 2814, "top_25_fed_district": 0})
        sec.flag(m.FlagLevel.WARN, "top_25_fed_district=0 unexpected for FL")
        sec.record_script(m.ScriptRecord(
            name="04_build_threat_data",
            status=m.ScriptStatus.FAILED,
            error_class="IndexError",
            error_msg="single positional indexer is out-of-bounds",
            error_file="competition/04_build_threat_data.py",
            error_line=18,
            suggested_fix="Add len() guard before iloc[0].",
            issue_body_md="## Failure during 1200 / 2026.05 run\n\n**Section:** Competition\n",
        ))
    with rm.start_section("MCC Categories") as sec:
        pass
    rm.end_run(m.RunStatus.PARTIAL)
    return rm


def test_scorecard_writes_markdown_with_verdict(tmp_path: Path):
    rm = _build_fixture_manifest(tmp_path)
    out = scorecard.write(rm, tmp_path / "run_scorecard.md")
    text = out.read_text()
    assert "Run scorecard" in text
    assert "1200" in text
    assert "2026.05" in text
    assert "Verdict" in text


def test_scorecard_includes_failure_with_issue_body(tmp_path: Path):
    rm = _build_fixture_manifest(tmp_path)
    out = scorecard.write(rm, tmp_path / "run_scorecard.md")
    text = out.read_text()
    assert "04_build_threat_data" in text
    assert "IndexError" in text
    assert "Issue body" in text
    assert "len() guard" in text


def test_scorecard_lists_section_table(tmp_path: Path):
    rm = _build_fixture_manifest(tmp_path)
    out = scorecard.write(rm, tmp_path / "run_scorecard.md")
    text = out.read_text()
    assert "Portfolio Overview" in text
    assert "Competition" in text
    assert "MCC Categories" in text
    assert "no_charts" in text or "No charts" in text


def test_scorecard_surfaces_anomaly_flags(tmp_path: Path):
    rm = _build_fixture_manifest(tmp_path)
    out = scorecard.write(rm, tmp_path / "run_scorecard.md")
    text = out.read_text()
    assert "top_25_fed_district=0" in text
    assert "warn" in text or "Warn" in text
