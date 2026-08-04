"""Duplicate TXN file guard (issue #251: byte-identical 1192 December pair).

A re-delivered monthly export under a new name double-counts a whole month
and inflates every frame in the run by its row count. These tests pin the
detection helper, the fresh-load skip, and the cache-hit self-heal (rows
from the duplicate dropped after loading, no rebuild needed).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

_ANALYTICS = Path(__file__).resolve().parents[1] / "analytics"
_DEFINE = _ANALYTICS / "txn_setup" / "04-define-data-func.py"


def _txn_cache_mod():
    spec = importlib.util.spec_from_file_location(
        "txn_cache_dedupe", _ANALYTICS / "txn_cache.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# duplicate_file_groups helper
# ---------------------------------------------------------------------------

def test_identical_files_grouped_keeper_first(tmp_path):
    a = tmp_path / "1192_a_dec.txt"
    b = tmp_path / "1192_b_relabelled.txt"
    a.write_text("same content" * 100)
    b.write_text("same content" * 100)
    groups = _txn_cache_mod().duplicate_file_groups([b, a])
    assert groups == [[a, b]]  # sorted by name; first is the keeper


def test_same_size_different_content_not_grouped(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("x" * 500)
    b.write_text("y" * 500)
    assert _txn_cache_mod().duplicate_file_groups([a, b]) == []


def test_distinct_sizes_and_missing_files_no_groups(tmp_path):
    a = tmp_path / "a.txt"
    a.write_text("aaa")
    assert _txn_cache_mod().duplicate_file_groups([a, tmp_path / "gone.txt"]) == []


# ---------------------------------------------------------------------------
# 04-define-data-func integration
# ---------------------------------------------------------------------------

def _write_raw(path: Path, rows: int = 8, marker: str = "v") -> None:
    data = ["\t".join(f"{marker}{r}_{c}" for c in range(13)) for r in range(rows)]
    path.write_text("BANNER ROW\n" + "\n".join(data), encoding="utf-8")


def _base_ns(monkeypatch, tmp_path) -> dict:
    # Local file-cache off so these tests exercise only the dedupe logic.
    monkeypatch.setenv("ARS_TXN_FILE_CACHE", "0")
    monkeypatch.setenv("ARS_LOCAL_CACHE_DIR", str(tmp_path / "cache"))
    return {"pd": pd, "Path": Path, "_txn_cache": _txn_cache_mod()}


def test_fresh_load_skips_duplicate_file(tmp_path, monkeypatch, capsys):
    f1 = tmp_path / "1192_jan.txt"
    f2 = tmp_path / "1192_dec_a.txt"
    f3 = tmp_path / "1192_dec_b_relabelled.txt"
    _write_raw(f1, rows=5, marker="j")
    _write_raw(f2, rows=8, marker="d")
    f3.write_bytes(f2.read_bytes())  # byte-identical duplicate

    ns = _base_ns(monkeypatch, tmp_path)
    ns.update({"USE_PARQUET_CACHE": None, "files_to_load": [f1, f2, f3]})
    exec(compile(_DEFINE.read_text(encoding="utf-8"), str(_DEFINE), "exec"), ns)  # noqa: S102

    loaded = {df["source_file"].iloc[0] for df in ns["transaction_files"]}
    assert loaded == {f1.name, f2.name}  # keeper by name order; extra skipped
    out = capsys.readouterr().out
    assert "byte-identical TXN files detected" in out
    assert f3.name in out


def test_cache_hit_drops_duplicate_rows(tmp_path, monkeypatch, capsys):
    f2 = tmp_path / "1192_dec_a.txt"
    f3 = tmp_path / "1192_dec_b_relabelled.txt"
    _write_raw(f2, rows=8, marker="d")
    f3.write_bytes(f2.read_bytes())

    cache = tmp_path / "combined_cache.parquet"
    pd.DataFrame({
        "amount": [1.0, 2.0, 3.0, 4.0],
        "source_file": [f2.name, f2.name, f3.name, f3.name],
    }).to_parquet(cache, index=False)

    ns = _base_ns(monkeypatch, tmp_path)
    ns.update({"USE_PARQUET_CACHE": cache, "files_to_load": [f2, f3]})
    exec(compile(_DEFINE.read_text(encoding="utf-8"), str(_DEFINE), "exec"), ns)  # noqa: S102

    df = ns["combined_df"]
    assert set(df["source_file"]) == {f2.name}
    assert len(df) == 2
    assert "Dropped 2 cached rows from duplicate file(s)" in capsys.readouterr().out


def test_no_duplicates_is_silent_and_loads_everything(tmp_path, monkeypatch, capsys):
    f1 = tmp_path / "1192_jan.txt"
    f2 = tmp_path / "1192_feb.txt"
    _write_raw(f1, rows=5, marker="j")
    _write_raw(f2, rows=6, marker="f")

    ns = _base_ns(monkeypatch, tmp_path)
    ns.update({"USE_PARQUET_CACHE": None, "files_to_load": [f1, f2]})
    exec(compile(_DEFINE.read_text(encoding="utf-8"), str(_DEFINE), "exec"), ns)  # noqa: S102

    assert len(ns["transaction_files"]) == 2
    assert "byte-identical" not in capsys.readouterr().out
