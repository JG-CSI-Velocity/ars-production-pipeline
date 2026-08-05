"""Tests for ars_staging -- scan, dedupe-alias, incremental copy, manifest."""

import os
from pathlib import Path

import pytest

from ars_engine.core.config import EngineConfig, PathsConfig
from ars_staging.manifest import load_manifest
from ars_staging.poller import poll, scan_ready_tree, staged_odd_file, staged_txn_files


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Synthetic ready tree + isolated local cache root."""
    monkeypatch.setenv("ARS_LOCAL_CACHE_DIR", str(tmp_path / "cache"))
    ready = tmp_path / "ready"

    odd_dir = ready / "Dan" / "2026.06" / "1759"
    odd_dir.mkdir(parents=True)
    (odd_dir / "1759-2026-06-Test Bank-ODD.xlsx").write_bytes(b"odd-bytes")
    (odd_dir / "~$1759-2026-06-Test Bank-ODD.xlsx").write_bytes(b"lock")

    txn_dir = ready / "TXN Files" / "Dan" / "1759"
    (txn_dir / "2026").mkdir(parents=True)
    (txn_dir / "testbank-trans-05312026.txt").write_bytes(b"a" * 100)
    (txn_dir / "2026" / "testbank-trans-06302026.csv").write_bytes(b"b" * 200)
    # byte-identical re-delivery under a new name (issue #251)
    (txn_dir / "z-relabeled-trans-05312026.txt").write_bytes(b"a" * 100)
    # non-data file that must be ignored
    (txn_dir / "notes.pdf").write_bytes(b"pdf")

    cfg = EngineConfig(paths=PathsConfig(ars_base=tmp_path, ready_dir=ready).resolved())
    return cfg


def test_scan_finds_odd_and_txn_skips_locks_and_nondata(env):
    items = scan_ready_tree(env.paths.ready_dir)
    kinds = sorted((i.kind, i.src.name) for i in items)
    assert ("odd", "1759-2026-06-Test Bank-ODD.xlsx") in kinds
    assert ("txn", "testbank-trans-05312026.txt") in kinds
    assert ("txn", "testbank-trans-06302026.csv") in kinds  # year subfolder
    names = [n for _, n in kinds]
    assert "~$1759-2026-06-Test Bank-ODD.xlsx" not in names
    assert "notes.pdf" not in names


def test_poll_stages_dedupes_and_is_incremental(env):
    r1 = poll(config=env, progress=lambda m: None)
    # 3 staged (1 odd + 2 txn), 1 aliased duplicate
    assert r1.staged == 3
    assert r1.aliased == 1
    assert not r1.errors

    m = load_manifest("1759")
    rec = m["files"]["z-relabeled-trans-05312026.txt"]
    assert rec["status"] == "alias_of:testbank-trans-05312026.txt"
    assert rec["staged"] is None

    # staged copies exist and are byte-identical
    txn = staged_txn_files("1759")
    assert len(txn) == 2  # alias not staged
    odd = staged_odd_file("1759", "2026.06")
    assert odd is not None and odd.read_bytes() == b"odd-bytes"

    # second poll: nothing new
    r2 = poll(config=env, progress=lambda m: None)
    assert r2.staged == 0
    assert r2.unchanged >= 3

    # touch a source -> it re-stages, AND its former byte-identical alias is
    # no longer an alias so it stages too (the bug_003 stale-alias fix)
    src = env.paths.ready_dir / "TXN Files" / "Dan" / "1759" / "testbank-trans-05312026.txt"
    src.write_bytes(b"c" * 150)
    os.utime(src, (src.stat().st_mtime + 10, src.stat().st_mtime + 10))
    r3 = poll(config=env, progress=lambda m: None)
    assert r3.staged == 2
    restaged = [p for p in staged_txn_files("1759") if p.name == src.name]
    assert restaged and restaged[0].read_bytes() == b"c" * 150


def test_on_client_staged_fires_only_for_new_txn(env):
    fired: list[str] = []
    poll(config=env, on_client_staged=fired.append, progress=lambda m: None)
    assert fired == ["1759"]
    fired.clear()
    poll(config=env, on_client_staged=fired.append, progress=lambda m: None)
    assert fired == []  # nothing new -> no refresh


def test_stale_alias_restages_when_keeper_content_changes(env):
    """Bug_003: an alias_of record is a runtime property, not permanent. When
    the keeper is re-delivered with corrected content (files no longer
    byte-identical), the former alias must re-stage, not silently vanish."""
    txn_dir = env.paths.ready_dir / "TXN Files" / "Dan" / "1759"
    keeper = txn_dir / "testbank-trans-05312026.txt"
    former_alias = txn_dir / "z-relabeled-trans-05312026.txt"

    poll(config=env, progress=lambda m: None)
    assert load_manifest("1759")["files"][former_alias.name]["status"].startswith("alias_of:")

    # corrected re-delivery: keeper content changes, alias file untouched
    import os
    keeper.write_bytes(b"corrected" * 20)
    os.utime(keeper, (keeper.stat().st_mtime + 10, keeper.stat().st_mtime + 10))

    r = poll(config=env, progress=lambda m: None)
    assert r.staged >= 2  # keeper re-staged AND former alias staged
    m = load_manifest("1759")
    assert m["files"][former_alias.name]["status"] == "staged"
    staged_names = {p.name for p in staged_txn_files("1759")}
    assert former_alias.name in staged_names
    assert staged_txn_files("1759")  # and its bytes are the original content
    alias_copy = [p for p in staged_txn_files("1759") if p.name == former_alias.name][0]
    assert alias_copy.read_bytes() == b"a" * 100


def test_alias_demotion_fires_store_refresh_hook(env):
    """Bug_004 (staging side): demoting a previously-staged file to alias must
    fire on_client_staged so the store reconciles away its rows."""
    txn_dir = env.paths.ready_dir / "TXN Files" / "Dan" / "1759"
    poll(config=env, progress=lambda m: None)
    # byte-identical re-delivery under an alphabetically-EARLIER name: the new
    # file becomes keeper, the previously staged file demotes to alias
    (txn_dir / "a-first-trans-05312026.txt").write_bytes(b"a" * 100)
    fired: list[str] = []
    poll(config=env, on_client_staged=fired.append, progress=lambda m: None)
    assert fired == ["1759"]
    m = load_manifest("1759")
    assert m["files"]["testbank-trans-05312026.txt"]["status"] == "alias_of:a-first-trans-05312026.txt"


def test_same_basename_at_different_depths_both_stage(env):
    """Bug_001: a year-subdir file and a top-level file with the same basename
    must get distinct manifest keys and staged destinations."""
    txn_dir = env.paths.ready_dir / "TXN Files" / "Dan" / "1759"
    header = "\t".join(["h"] * 13) + "\n"
    row_top = "\t".join(["06/15/2026", "A1", "SIG", "10.00", "5411", "SHOP-TOP",
                         "l1", "l2", "T1", "M1", "9", "Y", "05"]) + "\n"
    row_nested = row_top.replace("10.00", "20.00").replace("SHOP-TOP", "SHOP-NESTED")
    (txn_dir / "dup-trans.csv").write_text(header + row_top)
    (txn_dir / "2026" / "dup-trans.csv").write_text(header + row_nested)

    poll(config=env, progress=lambda m: None)
    m = load_manifest("1759")
    assert "dup-trans.csv" in m["files"]
    assert "2026/dup-trans.csv" in m["files"]
    copies = [p for p in staged_txn_files("1759") if p.name == "dup-trans.csv"]
    assert len(copies) == 2
    assert {p.read_text() for p in copies} == {header + row_top, header + row_nested}

    # and the store keys them separately (no DELETE-clobber)
    from ars_engine.data import txn_store
    txn_store.refresh("1759", staged_files=copies, log=lambda m: None)
    con = txn_store.connect("1759")
    try:
        keys = sorted(x[0] for x in con.execute(
            "SELECT DISTINCT source_file FROM transactions").fetchall())
    finally:
        con.close()
    assert keys == ["2026/dup-trans.csv", "dup-trans.csv"]


def test_filters(env):
    items = scan_ready_tree(env.paths.ready_dir, csm_filter="Nobody")
    assert items == []
    items = scan_ready_tree(env.paths.ready_dir, client_filter="9999")
    assert items == []
