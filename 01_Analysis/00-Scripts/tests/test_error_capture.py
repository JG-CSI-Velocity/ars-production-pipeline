from pathlib import Path
from ars_analysis.pipeline import error_capture as ec


def test_deepest_project_frame_picks_inside_analytics():
    """Frame extraction should prefer the deepest frame inside 'analytics/'."""
    try:
        # Simulate: pandas calls something, which calls something in our code, which raises
        def _user_code():
            d = {"a": 1}
            return d[0]  # raises KeyError from "our" code

        _user_code()
    except KeyError as exc:
        import sys
        tb = sys.exc_info()[2]
        frame = ec.deepest_project_frame(tb, project_marker="analytics")
        # This test file is not under analytics/, so we expect None.
        assert frame is None


def test_deepest_project_frame_finds_marker(tmp_path: Path):
    """Build a fake module under analytics/ and confirm the frame is found."""
    # Synthesize a path-like trace entry
    fake_tb = [
        ec._FrameInfo(filename="/x/y/pandas/core/something.py", lineno=999),
        ec._FrameInfo(filename="/M/ARS/01_Analysis/00-Scripts/analytics/competition/04_build_threat_data.py", lineno=18),
        ec._FrameInfo(filename="/x/y/numpy/something.py", lineno=42),
    ]
    frame = ec._pick_deepest_marker_frame(fake_tb, "analytics")
    assert frame is not None
    assert frame.lineno == 18
    assert "04_build_threat_data" in frame.filename


def test_suggest_fix_indexerror_out_of_bounds():
    s = ec.suggest_fix("IndexError", "single positional indexer is out-of-bounds")
    assert "len()" in s or "empty" in s.lower()


def test_suggest_fix_keyerror():
    s = ec.suggest_fix("KeyError", "'transaction_date'")
    assert "column" in s.lower() or "key" in s.lower()


def test_suggest_fix_memoryerror():
    s = ec.suggest_fix("MemoryError", "Unable to allocate 5.58 GiB for an array")
    assert "cross-join" in s.lower() or "cardinality" in s.lower()


def test_suggest_fix_nameerror():
    s = ec.suggest_fix("NameError", "name 'combined_df' is not defined")
    assert "upstream" in s.lower() or "earlier" in s.lower()


def test_suggest_fix_unknown_returns_empty():
    s = ec.suggest_fix("ValueError", "something weird")
    assert s == ""


def test_capture_exception_populates_script_record_fields():
    try:
        d = {"a": 1}
        return_value = d[0]  # noqa: F841
    except KeyError as exc:
        import sys
        tb = sys.exc_info()[2]
        fields = ec.capture_exception(
            exc, tb,
            section_name="Competition",
            script_name="04_build_threat_data",
            client_id="1200", month="2026.05",
            project_marker="tests",  # use tests/ so the test file itself is the "project frame"
        )

    assert fields["error_class"] == "KeyError"
    assert "0" in fields["error_msg"]
    assert fields["error_file"].endswith("test_error_capture.py")
    assert fields["error_line"] > 0
    assert fields["error_traceback_tail"]
    assert fields["suggested_fix"]  # KeyError always has a suggestion
    body = fields["issue_body_md"]
    assert "Competition" in body
    assert "04_build_threat_data" in body
    assert "1200" in body
    assert "2026.05" in body
    assert "KeyError" in body
