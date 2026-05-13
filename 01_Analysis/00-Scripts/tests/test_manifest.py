from ars_analysis.pipeline import manifest as m


def test_status_enum_values():
    assert m.RunStatus.OK.value == "ok"
    assert m.RunStatus.PARTIAL.value == "partial"
    assert m.RunStatus.FAILED.value == "failed"


def test_section_status_enum_values():
    assert m.SectionStatus.OK.value == "ok"
    assert m.SectionStatus.PARTIAL.value == "partial"
    assert m.SectionStatus.FAILED.value == "failed"
    assert m.SectionStatus.NO_CHARTS.value == "no_charts"
    assert m.SectionStatus.SKIPPED.value == "skipped"


def test_script_record_round_trips_to_dict():
    rec = m.ScriptRecord(
        name="04_build_threat_data",
        status=m.ScriptStatus.FAILED,
        elapsed_s=2.3,
        error_class="IndexError",
        error_msg="out-of-bounds",
        error_file="competition/04_build_threat_data.py",
        error_line=18,
        suggested_fix="Add a len() guard before iloc[0].",
        issue_body_md="## Failure...",
    )
    d = rec.to_dict()
    assert d["name"] == "04_build_threat_data"
    assert d["status"] == "failed"
    assert d["error_line"] == 18
