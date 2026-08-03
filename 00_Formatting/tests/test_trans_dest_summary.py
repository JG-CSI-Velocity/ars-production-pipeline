"""Destination-holdings summary after the trans gather (issue #251 follow-up).

When TXN files were hand-placed (or gathered in a prior run), the source dump
legitimately has nothing to copy and the log said only "No transaction files
found" -- which operators read as data loss. The gather must also report how
many files the analysis loader will actually see in the destination
TXN Files/{CSM}/{client}/ folder.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run  # noqa: E402


def _make_dest(tmp_path) -> Path:
    dest = tmp_path / "TXN Files" / "Jordan" / "1192"
    dest.mkdir(parents=True)
    return dest


def test_counts_flat_txt_files(tmp_path):
    dest = _make_dest(tmp_path)
    (dest / "1192_trans_071026.txt").write_text("data")
    (dest / "1192_trans_061026.txt").write_text("data")
    assert run.count_dest_txn_files(str(dest)) == 2


def test_counts_extensionless_and_year_subfolders(tmp_path):
    dest = _make_dest(tmp_path)
    (dest / "1192_35687_[2026.07.05][10.03.04]_monthlydebittransactions").write_text("d")
    year = dest / "2025"
    year.mkdir()
    (year / "1192_trans_010125.txt").write_text("d")
    assert run.count_dest_txn_files(str(dest)) == 2


def test_ignores_non_data_files(tmp_path):
    dest = _make_dest(tmp_path)
    (dest / "1192_trans_071026.txt").write_text("data")
    (dest / "1192_ODDD.zip").write_text("not data")
    (dest / "1192_combined_cache.parquet").write_text("cache")
    (dest / "notes.pdf").write_text("doc")
    assert run.count_dest_txn_files(str(dest)) == 1


def test_missing_folder_counts_zero(tmp_path):
    assert run.count_dest_txn_files(str(tmp_path / "nope")) == 0
