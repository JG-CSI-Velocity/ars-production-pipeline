"""Regression tests for resilient logging in 00_Formatting/run.py.

Issue #232: a locked or permission-denied formatting_log.txt raised
PermissionError inside log_message and aborted the entire formatting run
before a single file was processed. Logging must degrade to console-only
instead of crashing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run  # noqa: E402


def test_log_message_writes_to_file(tmp_path, capsys):
    log_file = str(tmp_path / "formatting_log.txt")

    run.log_message("hello", log_file)

    assert "hello" in capsys.readouterr().out
    assert Path(log_file).read_text(encoding="utf-8") == "hello\n"


def test_log_message_survives_unwritable_log(tmp_path, capsys):
    # A directory cannot be opened for append -- a portable stand-in for the
    # locked / permission-denied file that crashed the run in issue #232.
    unwritable = str(tmp_path)

    # Must not raise.
    run.log_message("first", unwritable)
    run.log_message("second", unwritable)

    out = capsys.readouterr().out
    assert "first" in out
    assert "second" in out
    # The operator still sees the message and a warning, surfaced in the UI
    # run log because run.py is launched with stdout piped to the UI.
    assert "WARNING" in out


def test_log_message_warns_only_once_per_log(tmp_path, capsys):
    unwritable = str(tmp_path / "is_a_dir")
    Path(unwritable).mkdir()

    run.log_message("a", unwritable)
    run.log_message("b", unwritable)
    run.log_message("c", unwritable)

    warnings = [ln for ln in capsys.readouterr().out.splitlines() if "WARNING" in ln]
    assert len(warnings) == 1
