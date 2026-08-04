"""Local cache tier (#251 follow-up): derived artifacts live on local disk.

The M: share moves at ~1.7 MB/s on the work machine, so caches stored there
made even "hits" re-stream hundreds of MB. These tests pin: the local root
resolution, the per-file TXN parquet cache (parity, keying, kill switch), the
combined-cache save/read split with legacy migration, and the parallel file
loader preserving sequential ordering.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

_ANALYTICS = Path(__file__).resolve().parents[1] / "analytics"
_DEFINE = _ANALYTICS / "txn_setup" / "04-define-data-func.py"


def _txn_cache_mod():
    spec = importlib.util.spec_from_file_location("txn_cache_lct", _ANALYTICS / "txn_cache.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def local_root(tmp_path, monkeypatch):
    root = tmp_path / "local-cache"
    monkeypatch.setenv("ARS_LOCAL_CACHE_DIR", str(root))
    monkeypatch.delenv("ARS_TXN_FILE_CACHE", raising=False)
    return root


# ---------------------------------------------------------------------------
# txn_cache helpers
# ---------------------------------------------------------------------------

def test_local_cache_root_env_override(local_root):
    assert _txn_cache_mod().local_cache_root() == local_root


def test_local_cache_root_has_default_without_env(monkeypatch):
    monkeypatch.delenv("ARS_LOCAL_CACHE_DIR", raising=False)
    root = _txn_cache_mod().local_cache_root()
    assert root.name in ("ARS-cache", ".ars-cache")


def test_file_cache_path_keyed_by_mtime_and_size(local_root, tmp_path):
    tc = _txn_cache_mod()
    src = tmp_path / "1192_trans.txt"
    src.write_text("data")
    p = tc.file_cache_path("txn-files", "1192", src, ".parquet")
    stat = src.stat()
    assert p == (local_root / "txn-files" / "1192"
                 / f"1192_trans.txt.{int(stat.st_mtime)}.{stat.st_size}.parquet")
    assert tc.file_cache_path("txn-files", "1192", tmp_path / "gone.txt", ".parquet") is None


def test_combined_cache_paths_prefer_local_then_legacy(local_root, tmp_path):
    tc = _txn_cache_mod()
    client_path = tmp_path / "TXN Files" / "Jordan" / "1192"
    client_path.mkdir(parents=True)
    local_expected = local_root / "txn-combined" / "1192_combined_cache.parquet"

    # Neither exists: read == local save target (NO CACHE case).
    save, read = tc.combined_cache_paths("1192", client_path)
    assert (save, read) == (local_expected, local_expected)

    # Only legacy exists: read migrates from the share once.
    legacy = client_path / "1192_combined_cache.parquet"
    legacy.write_text("legacy")
    save, read = tc.combined_cache_paths("1192", client_path)
    assert (save, read) == (local_expected, legacy)

    # Local exists: it wins even with legacy still present.
    local_expected.parent.mkdir(parents=True)
    local_expected.write_text("local")
    save, read = tc.combined_cache_paths("1192", client_path)
    assert (save, read) == (local_expected, local_expected)


# ---------------------------------------------------------------------------
# Per-file parquet cache in 04-define-data-func
# ---------------------------------------------------------------------------

def _load_04(with_cache_ns: bool = True) -> dict:
    src = _DEFINE.read_text(encoding="utf-8")
    head = src.split("# Load data -- Parquet cache or raw files")[0]
    ns: dict = {"pd": pd, "Path": Path}
    if with_cache_ns:
        ns["_txn_cache"] = _txn_cache_mod()
        ns["CLIENT_ID"] = "1192"
    exec(compile(head, str(_DEFINE), "exec"), ns)  # noqa: S102
    return ns


def _write_raw(path: Path, rows: int = 20) -> None:
    data = ["\t".join(f"v{r}_{c}" for c in range(13)) for r in range(rows)]
    path.write_text("BANNER ROW\n" + "\n".join(data), encoding="utf-8")


def test_second_read_uses_local_parquet_and_matches_raw(local_root, tmp_path):
    ns = _load_04()
    f = tmp_path / "1192_trans_0701.txt"
    _write_raw(f)

    first = ns["load_transaction_file"](str(f))
    cached_files = list((local_root / "txn-files" / "1192").glob("*.parquet"))
    assert len(cached_files) == 1

    # Delete the raw file: only the cache can serve the second read.
    f_stat_key = cached_files[0].name
    raw_bytes = f.read_bytes()
    f.unlink()
    # file_cache_path stats the source, so restore a byte-identical file to
    # keep the key stable (mtime may differ -> preserve it explicitly).
    f.write_bytes(raw_bytes)
    import os
    mtime = int(f_stat_key.split(".")[-3])
    os.utime(f, (mtime, mtime))

    second = ns["load_transaction_file"](str(f))
    pd.testing.assert_frame_equal(first, second)


def test_changed_raw_file_misses_old_cache_key(local_root, tmp_path):
    import os
    import time

    ns = _load_04()
    f = tmp_path / "1192_trans_0701.txt"
    _write_raw(f, rows=5)
    ns["load_transaction_file"](str(f))

    _write_raw(f, rows=9)  # re-delivered file: new size
    os.utime(f, (time.time() + 10, time.time() + 10))
    df = ns["load_transaction_file"](str(f))
    assert len(df) == 9  # re-read raw, not the stale 5-row cache


def test_kill_switch_disables_file_cache(local_root, tmp_path, monkeypatch):
    monkeypatch.setenv("ARS_TXN_FILE_CACHE", "0")
    ns = _load_04()
    f = tmp_path / "1192_trans_0701.txt"
    _write_raw(f)
    ns["load_transaction_file"](str(f))
    assert not (local_root / "txn-files").exists()


def test_standalone_namespace_runs_uncached(local_root, tmp_path):
    # Without _txn_cache/CLIENT_ID (e.g. old tests, notebook use) the loader
    # must behave exactly as before -- no cache, no crash.
    ns = _load_04(with_cache_ns=False)
    f = tmp_path / "1192_trans_0701.txt"
    _write_raw(f)
    df = ns["load_transaction_file"](str(f))
    assert len(df) == 20
    assert not (local_root / "txn-files").exists()


def test_corrupt_file_cache_falls_back_to_raw(local_root, tmp_path):
    ns = _load_04()
    f = tmp_path / "1192_trans_0701.txt"
    _write_raw(f)
    target = ns["_file_cache_target"](Path(f))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"not parquet")

    df = ns["load_transaction_file"](str(f))
    assert len(df) == 20


# ---------------------------------------------------------------------------
# Parallel loading tail preserves sequential order
# ---------------------------------------------------------------------------

def _run_04_tail(files, workers: str, local_root) -> dict:
    src = _DEFINE.read_text(encoding="utf-8")
    ns = _load_04()
    ns.update({
        "USE_PARQUET_CACHE": None,
        "files_to_load": [Path(f) for f in files],
    })
    import os
    os.environ["ARS_TXN_PARALLEL"] = workers
    try:
        exec(compile(src, str(_DEFINE), "exec"), ns)  # noqa: S102
    finally:
        os.environ.pop("ARS_TXN_PARALLEL", None)
    return ns


@pytest.mark.parametrize("workers", ["1", "3"])
def test_tail_loads_all_files_in_sorted_order(local_root, tmp_path, workers):
    names = ["c_march.txt", "a_jan.txt", "b_feb.txt"]
    for i, name in enumerate(names):
        _write_raw(tmp_path / name, rows=5 + i)

    ns = _run_04_tail([tmp_path / n for n in names], workers, local_root)

    frames = ns["transaction_files"]
    assert [f["source_file"].iloc[0] for f in frames] == sorted(names)
    assert ns["SKIP_COMBINE"] is False
    assert sum(len(f) for f in frames) == 5 + 6 + 7
