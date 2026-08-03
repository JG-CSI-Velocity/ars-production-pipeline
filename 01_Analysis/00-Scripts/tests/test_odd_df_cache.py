"""Parsed-DataFrame cache for the ODD workbook (perf quick win).

_ODD_CACHE only skips the network copy -- every _read_file call still paid
the multi-minute openpyxl parse, up to 3x per combined run. These tests pin
the two cache levels (in-process dict + cross-run pickle sidecar), the copy
semantics that keep callers isolated, and the fallback / kill-switch paths.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ars_analysis.pipeline.steps import load as load_mod


@pytest.fixture(autouse=True)
def _isolated_caches(tmp_path, monkeypatch):
    """Fresh caches per test, sidecars confined to tmp_path."""
    monkeypatch.setenv("ARS_ODD_CACHE_DIR", str(tmp_path / ".odd_cache"))
    monkeypatch.delenv("ARS_ODD_CACHE", raising=False)
    load_mod._ODD_DF_CACHE.clear()
    load_mod._ODD_CACHE.clear()
    yield
    load_mod._ODD_DF_CACHE.clear()
    load_mod._ODD_CACHE.clear()


def _write_fixture_xlsx(path: Path) -> pd.DataFrame:
    # Banner row above the header exercises _detect_header_row, and a numeric
    # header cell exercises the str-coercion in _read_tabular.
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["SOME BANNER TEXT", None, None, None])
    ws.append(["Stat Code", "Product Code", "Date Opened", 202406])
    ws.append(["A", "P1", "01/02/2024", 10])
    ws.append(["C", "P2", "03/04/2024", 20])
    wb.save(path)
    return pd.DataFrame(
        {
            "Stat Code": ["A", "C"],
            "Product Code": ["P1", "P2"],
            "Date Opened": ["01/02/2024", "03/04/2024"],
            "202406": [10, 20],
        }
    )


def test_parse_parity_and_copy_isolation(tmp_path):
    src = tmp_path / "1192-2026-07-ODD.xlsx"
    _write_fixture_xlsx(src)

    first = load_mod._read_file(src)
    second = load_mod._read_file(src)  # in-process hit

    pd.testing.assert_frame_equal(first, second)
    # Mutating a returned frame must not leak into later reads.
    first["Stat Code"] = "MUTATED"
    third = load_mod._read_file(src)
    assert third["Stat Code"].tolist() == ["A", "C"]


def test_sidecar_round_trip_across_process_restart(tmp_path):
    src = tmp_path / "1192-2026-07-ODD.xlsx"
    _write_fixture_xlsx(src)

    first = load_mod._read_file(src)
    writer = load_mod._df_cache_put(src, first)
    if writer is not None:
        writer.join(timeout=10)

    sidecars = list((tmp_path / ".odd_cache").glob("*.pkl"))
    assert len(sidecars) == 1

    # Simulate a fresh subprocess: in-process caches empty, sidecar remains.
    load_mod._ODD_DF_CACHE.clear()
    load_mod._ODD_CACHE.clear()
    from_sidecar = load_mod._read_file(src)
    pd.testing.assert_frame_equal(from_sidecar, first)


def test_changed_source_bypasses_sidecar(tmp_path):
    import os
    import time

    src = tmp_path / "1192-2026-07-ODD.xlsx"
    _write_fixture_xlsx(src)
    writer = load_mod._df_cache_put(src, load_mod._read_file(src))
    if writer is not None:
        writer.join(timeout=10)

    # New mtime/size -> different sidecar key -> full re-parse.
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Stat Code", "Product Code", "Date Opened", "Avg Bal"])
    ws.append(["Z", "P9", "05/06/2025", 99])
    wb.save(src)
    os.utime(src, (time.time() + 5, time.time() + 5))
    load_mod._ODD_DF_CACHE.clear()
    load_mod._ODD_CACHE.clear()

    df = load_mod._read_file(src)
    assert df["Stat Code"].tolist() == ["Z"]


def test_corrupt_sidecar_falls_back_to_parse(tmp_path):
    src = tmp_path / "1192-2026-07-ODD.xlsx"
    expected = _write_fixture_xlsx(src)

    sidecar = load_mod._df_sidecar_path(src)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_bytes(b"this is not a pickle")

    df = load_mod._read_file(src)
    assert df["Stat Code"].tolist() == expected["Stat Code"].tolist()


def test_kill_switch_disables_both_levels(tmp_path, monkeypatch):
    monkeypatch.setenv("ARS_ODD_CACHE", "0")
    src = tmp_path / "1192-2026-07-ODD.xlsx"
    _write_fixture_xlsx(src)

    load_mod._read_file(src)
    assert load_mod._ODD_DF_CACHE == {}
    assert not (tmp_path / ".odd_cache").exists()
    assert load_mod._df_cache_get(src) is None
