"""Tests for the #229 source-file staging path in 00_Formatting/run.py.

Covers the three behaviors the UI 'Generate from a path' flow relies on:
  - a raw ODD CSV is run through the 7-step formatter (signature columns appear)
  - the 4-row preamble is skipped and the index column dropped
  - a file that doesn't look like a raw ODD is refused, not silently mangled
"""

import csv
import importlib.util
from pathlib import Path

import pandas as pd

_RUN_PY = Path(__file__).resolve().parents[2] / "run.py"


def _load_run():
    spec = importlib.util.spec_from_file_location("ars_run_under_test", _RUN_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_raw_odd(path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        for i in range(4):  # 4 preamble/metadata rows above the real header
            w.writerow([f"preamble {i}"])
        w.writerow(["", "Account", "Stat Code", "DOB", "Date Opened",
                    "Jun26 PIN $", "Jun26 Sig $", "Jun26 PIN #", "Jun26 Sig #",
                    "Jun26 Mail", "Jun26 Resp"])
        w.writerow([0, "1001", "2", "1980-01-01", "2010-05-01", 100, 50, 4, 2, "TH-10", "NU 5+"])
        w.writerow([1, "1002", "3", "1975-06-15", "2015-03-20", 0, 0, 0, 0, "", ""])


def test_raw_csv_is_fully_formatted(tmp_path):
    run = _load_run()
    src = tmp_path / "1815-2026-06-FedChoice FCU-ODD.csv"
    _write_raw_odd(src)
    out = tmp_path / "out"

    ok, err = run.process_source_file(str(src), "Dan", "2026.06", "1815", str(out), force=True)

    assert (ok, err) == (1, 0)
    xlsx = list((out / "1815").glob("*.xlsx"))
    assert len(xlsx) == 1
    df = pd.read_excel(xlsx[0])
    # 7-step formatter signature columns must be present
    for col in ("Total Spend", "Total Swipes", "SwipeCat12", "Response Grouping"):
        assert col in df.columns, f"missing {col}"
    # index column dropped, real data preserved (2 rows)
    assert len(df) == 2
    assert "Account" in df.columns


def test_non_odd_csv_is_refused(tmp_path):
    run = _load_run()
    src = tmp_path / "9999-2026-06-junk-ODD.csv"
    with open(src, "w", newline="") as f:
        w = csv.writer(f)
        for i in range(4):
            w.writerow([f"preamble {i}"])
        w.writerow(["foo", "bar", "baz"])  # not an ODD header
        w.writerow([1, 2, 3])
    out = tmp_path / "out"

    ok, err = run.process_source_file(str(src), "Dan", "2026.06", "9999", str(out), force=True)

    # sanity guard refuses rather than writing a garbage workbook
    assert (ok, err) == (0, 1)
    assert not list((out / "9999").glob("*.xlsx"))
