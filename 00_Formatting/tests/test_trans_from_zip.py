"""Transaction files now ship INSIDE the ODD zips (e.g. 1200_ODDD.zip carries
both the unformatted ODD and the transaction file). process_csm() extracts only
ODD entries, so gather_trans_from_zips() pulls the transaction entry out and
routes it to TXN Files/{CSM}/{client_id}/ where the analysis 'data dump' step
reads it.
"""

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run  # noqa: E402


def _make_zip(path, entries):
    """entries: {arcname: bytes} -> writes a zip and returns its path."""
    with zipfile.ZipFile(path, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return path


def test_txn_entry_extracted_from_odd_zip(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _make_zip(src / "1200_ODDD.zip", {
        "1200-2026-06-Guardians-ODD.csv": b"banner\nbanner\nbanner\nbanner\nAccount\n1\n",
        "1200_transactions_2026.06.30.txt": b"date,amount\n2026-06-30,10\n",
    })
    txn_base = tmp_path / "TXN Files"

    ok, err = run.gather_trans_from_zips(str(src), str(txn_base), "JamesG")

    assert (ok, err) == (1, 0)
    dest = txn_base / "JamesG" / "1200" / "1200_transactions_2026.06.30.txt"
    assert dest.exists()
    assert dest.read_bytes() == b"date,amount\n2026-06-30,10\n"
    # The ODD entry must NOT be routed into TXN Files
    assert list((txn_base / "JamesG" / "1200").iterdir()) == [dest]


def test_client_id_falls_back_to_zip_name(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _make_zip(src / "1441_ODDD.zip", {
        "somebank-ODD.csv": b"x",
        "transactions.txt": b"a,b\n1,2\n",  # inner entry has no leading digits
    })
    txn_base = tmp_path / "TXN Files"

    ok, err = run.gather_trans_from_zips(str(src), str(txn_base), "Dan")

    assert (ok, err) == (1, 0)
    assert (txn_base / "Dan" / "1441" / "transactions.txt").exists()


def test_second_run_dedups_by_size(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _make_zip(src / "1200_ODDD.zip", {"1200_trans.csv": b"a,b\n1,2\n"})
    txn_base = tmp_path / "TXN Files"

    first_ok, _ = run.gather_trans_from_zips(str(src), str(txn_base), "JamesG")
    second = run.gather_trans_from_zips(str(src), str(txn_base), "JamesG")

    assert first_ok == 1
    assert second == (0, 0)  # already present, same size -> skipped


def test_entry_with_odd_and_tran_is_not_routed_to_txn(tmp_path):
    # 'odd' wins: process_csm already handles it, so it must not land in TXN.
    src = tmp_path / "src"
    src.mkdir()
    _make_zip(src / "1200_ODDD.zip", {"1200_odd_transactions.csv": b"a,b\n1,2\n"})
    txn_base = tmp_path / "TXN Files"

    ok, err = run.gather_trans_from_zips(str(src), str(txn_base), "JamesG")

    assert (ok, err) == (0, 0)
    assert not (txn_base / "JamesG" / "1200").exists()


def test_excluded_client_is_skipped(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _make_zip(src / "1200_ODDD.zip", {"1200_trans.csv": b"a,b\n1,2\n"})
    txn_base = tmp_path / "TXN Files"

    ok, err = run.gather_trans_from_zips(
        str(src), str(txn_base), "JamesG",
        clients_config={"1200": {"exclude": True, "exclude_reason": "test"}},
    )

    assert (ok, err) == (0, 0)
    assert not (txn_base / "JamesG" / "1200").exists()
