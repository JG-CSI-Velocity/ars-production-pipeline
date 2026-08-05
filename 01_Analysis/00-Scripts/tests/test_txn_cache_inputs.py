"""Combined-cache input-set manifest (data-engineer audit r1 #1).

The mtime-only freshness rule misses two silent-stale paths: a deleted input
(cache still "newer than everything") and an mtime-preserving re-delivery
(copy2/robocopy keep source mtimes). The manifest records the exact input set
so both invalidate the cache.
"""

from __future__ import annotations

import os

from ars_analysis.analytics import txn_cache


def _mk(tmp_path, name, content=b"x" * 10):
    p = tmp_path / name
    p.write_bytes(content)
    return p


def test_no_manifest_returns_none(tmp_path):
    cache = _mk(tmp_path, "c_combined_cache.parquet")
    assert txn_cache.input_set_matches(cache, [_mk(tmp_path, "a.txt")]) is None


def test_roundtrip_match(tmp_path):
    cache = _mk(tmp_path, "c_combined_cache.parquet")
    files = [_mk(tmp_path, "a-trans.txt"), _mk(tmp_path, "b-trans.txt")]
    txn_cache.save_input_manifest(cache, files)
    assert txn_cache.input_set_matches(cache, files) is True


def test_deleted_input_invalidates(tmp_path):
    cache = _mk(tmp_path, "c_combined_cache.parquet")
    a = _mk(tmp_path, "a-trans.txt")
    b = _mk(tmp_path, "b-trans.txt")
    txn_cache.save_input_manifest(cache, [a, b])
    b.unlink()
    # The cache baked b's rows in; with b gone the mtime rule would still HIT.
    assert txn_cache.input_set_matches(cache, [a]) is False


def test_mtime_preserving_redelivery_invalidates(tmp_path):
    cache = _mk(tmp_path, "c_combined_cache.parquet")
    a = _mk(tmp_path, "a-trans.txt", b"old contents!")
    txn_cache.save_input_manifest(cache, [a])
    old_stat = a.stat()
    # Corrected file re-delivered with the ORIGINAL mtime (copy2 semantics)
    # but different size -- invisible to the mtime rule.
    a.write_bytes(b"corrected, longer contents")
    os.utime(a, (old_stat.st_atime, old_stat.st_mtime))
    assert txn_cache.input_set_matches(cache, [a]) is False


def test_added_input_invalidates(tmp_path):
    cache = _mk(tmp_path, "c_combined_cache.parquet")
    a = _mk(tmp_path, "a-trans.txt")
    txn_cache.save_input_manifest(cache, [a])
    b = _mk(tmp_path, "b-trans.txt")
    assert txn_cache.input_set_matches(cache, [a, b]) is False


def test_corrupt_manifest_falls_back_to_none(tmp_path):
    cache = _mk(tmp_path, "c_combined_cache.parquet")
    a = _mk(tmp_path, "a-trans.txt")
    txn_cache.input_manifest_path(cache).write_text("{not json", encoding="utf-8")
    assert txn_cache.input_set_matches(cache, [a]) is None
