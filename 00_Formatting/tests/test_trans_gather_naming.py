"""Gathering must recognize Ascend-style extensionless TXN files (issue #251).

1192 delivers `1192_35687_[YYYY.MM.DD][HH.MM.SS]_monthlydebittransactions`
(no extension, plural). The old rule (.txt/.csv or exactly '_transaction')
silently skipped them in both the folder gather and the zip gather.
"""

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run  # noqa: E402

ASCEND_NAME = "1192_35687_[2026.07.05][10.03.04]_monthlydebittransactions"


def test_extensionless_transactions_gathered_from_folder(tmp_path):
    src = tmp_path / "dump"
    src.mkdir()
    (src / ASCEND_NAME).write_bytes(b"date,amount\n2026-07-01,10\n")
    (src / "1192_ODDD.zip").write_bytes(b"not a real zip")  # must be ignored
    txn_base = tmp_path / "TXN Files"

    ok, err = run.gather_trans_files(str(src), str(txn_base), "Jordan", "1192")

    assert (ok, err) == (1, 0)
    assert (txn_base / "Jordan" / "1192" / ASCEND_NAME).exists()


def test_extensionless_transactions_extracted_from_zip(tmp_path):
    src = tmp_path / "dump"
    src.mkdir()
    with zipfile.ZipFile(src / "1192_ODDD.zip", "w") as z:
        z.writestr("1192-2026-07-Ascend FCU-ODD.csv", "Account\n1\n")
        z.writestr(ASCEND_NAME, "date,amount\n2026-07-01,10\n")
    txn_base = tmp_path / "TXN Files"

    ok, err = run.gather_trans_from_zips(str(src), str(txn_base), "Jordan", "1192")

    assert (ok, err) == (1, 0)
    assert (txn_base / "Jordan" / "1192" / ASCEND_NAME).exists()


def test_empty_folder_logs_scanned_directory(tmp_path):
    src = tmp_path / "dump"
    src.mkdir()
    log_file = tmp_path / "log.txt"

    ok, err = run.gather_trans_files(str(src), str(tmp_path / "TXN Files"),
                                     "Jordan", "1192", str(log_file))

    assert (ok, err) == (0, 0)
    assert str(src) in log_file.read_text()
