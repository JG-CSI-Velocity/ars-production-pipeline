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


import json
from pathlib import Path


def test_run_manifest_starts_and_flushes(tmp_path: Path):
    rm = m.RunManifest(
        client_id="1200", client_name="Guardians CU",
        csm="JamesG", month="2026.05", product="combined",
        output_dir=tmp_path,
    )
    rm.start_run()
    rm.flush()

    out_path = tmp_path / "run_manifest.json"
    assert out_path.exists()

    data = json.loads(out_path.read_text())
    assert data["schema_version"] == 1
    assert data["client_id"] == "1200"
    assert data["status"] == "running"
    assert data["sections"] == []


def test_run_manifest_end_run_sets_status_and_elapsed(tmp_path: Path):
    rm = m.RunManifest(
        client_id="1200", client_name="Guardians CU",
        csm="JamesG", month="2026.05", product="combined",
        output_dir=tmp_path,
    )
    rm.start_run()
    rm.end_run(m.RunStatus.OK)

    data = json.loads((tmp_path / "run_manifest.json").read_text())
    assert data["status"] == "ok"
    assert data["ended_at"]
    assert data["elapsed_s"] >= 0


def test_flush_is_atomic_via_tempfile_rename(tmp_path: Path, monkeypatch):
    """The flush path must NOT leave a half-written file if write fails."""
    rm = m.RunManifest(
        client_id="1200", client_name="Guardians CU",
        csm="JamesG", month="2026.05", product="combined",
        output_dir=tmp_path,
    )
    rm.start_run()
    rm.flush()  # establish baseline

    baseline = (tmp_path / "run_manifest.json").read_text()

    # Force os.replace to fail; the existing file should remain valid
    import os as _os
    real_replace = _os.replace

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(_os, "replace", boom)
    rm.flush()  # must NOT raise -- flush failures are swallowed
    assert (tmp_path / "run_manifest.json").read_text() == baseline
