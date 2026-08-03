"""clear_stale_txn_cache deletes only caches older than the cutoff, and only
when --apply is used. Guards the TXN 'stale cache crashes new code' fix."""

from __future__ import annotations

from datetime import datetime
import os

from tools import clear_stale_txn_cache as mod


def _cache(base, csm, cid, when: datetime):
    f = base / csm / cid / f"{cid}_combined_cache.parquet"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("x")
    os.utime(f, (when.timestamp(), when.timestamp()))
    return f


def test_find_stale_selects_only_pre_cutoff(tmp_path):
    old = _cache(tmp_path, "CSM1", "1776", datetime(2026, 6, 1))
    fresh = _cache(tmp_path, "CSM2", "1453", datetime(2026, 7, 9, 12))
    stale = mod.find_stale(tmp_path, datetime(2026, 7, 9))
    paths = {p for p, _, _ in stale}
    assert old in paths and fresh not in paths


def test_dry_run_keeps_files_apply_deletes(tmp_path, monkeypatch, capsys):
    old = _cache(tmp_path, "CSM1", "1776", datetime(2026, 6, 1))
    fresh = _cache(tmp_path, "CSM2", "1453", datetime(2026, 7, 9, 12))

    monkeypatch.setattr("sys.argv", ["prog", "--base", str(tmp_path)])
    mod.main()
    assert old.exists() and fresh.exists()  # dry-run deletes nothing

    monkeypatch.setattr("sys.argv", ["prog", "--base", str(tmp_path), "--apply"])
    mod.main()
    assert not old.exists() and fresh.exists()  # only the stale one is gone
