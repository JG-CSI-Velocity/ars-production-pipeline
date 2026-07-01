"""Issue #240: an empty/truncated raw ODD must produce a clear operator message.

Client 1200's ODD CSV had no data rows, so `pd.read_csv(skiprows=4)` raised the
bare `EmptyDataError: No columns to parse from file`. The 4-row banner skip is the
correct, permanent contract -- the fix is only to turn that opaque pandas error
into an actionable message pointing at the source file, not at the code.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run  # noqa: E402


def _write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_only_banner_rows_raises_clear_message(tmp_path):
    # 4 preamble rows, no header, no data -> nothing remains after skiprows=4.
    csv = _write(tmp_path / "1200-2026-06-Guardians Credit Union-ODD.csv",
                 "OD Data Dump\nGuardians Credit Union\nGenerated 2026-06-30\n\n")
    with pytest.raises(ValueError) as exc:
        run._read_raw_odd_csv(csv)
    msg = str(exc.value)
    assert "no data rows" in msg
    assert "Re-export or re-download" in msg
    assert "1200-2026-06-Guardians Credit Union-ODD.csv" in msg


def test_empty_file_raises_clear_message(tmp_path):
    csv = _write(tmp_path / "empty-ODD.csv", "")
    with pytest.raises(ValueError) as exc:
        run._read_raw_odd_csv(csv, "empty-ODD.csv")
    assert "no data rows" in str(exc.value)


def test_normal_raw_odd_still_reads(tmp_path):
    # 4 banner rows + header + 2 data rows: skiprows=4 keeps header + data.
    csv = _write(
        tmp_path / "ok-ODD.csv",
        "banner1\nbanner2\nbanner3\nbanner4\n"
        "Account,Stat Code,Date Opened\n"
        "1,O,2020-01-01\n2,O,2021-06-15\n",
    )
    df = run._read_raw_odd_csv(csv)
    assert list(df.columns) == ["Account", "Stat Code", "Date Opened"]
    assert len(df) == 2
