"""Tests for the chart-PNG content-hash cache."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from ars_analysis.charts.cache import (
    cached_chart,
    fingerprint_df,
    purge_cache,
)


def _stub_draw(path: Path) -> None:
    """Stand-in for an actual matplotlib render -- just writes a tiny PNG-ish file."""
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\nfake")


def test_fingerprint_stable_across_calls():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    k1 = fingerprint_df(df, columns=["a", "b"])
    k2 = fingerprint_df(df, columns=["a", "b"])
    assert k1 == k2
    assert len(k1) == 16


def test_fingerprint_column_order_independent():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    k1 = fingerprint_df(df, columns=["a", "b"])
    k2 = fingerprint_df(df, columns=["b", "a"])
    assert k1 == k2


def test_fingerprint_changes_when_data_changes():
    df1 = pd.DataFrame({"a": [1, 2, 3]})
    df2 = pd.DataFrame({"a": [1, 2, 4]})  # one cell different
    assert fingerprint_df(df1, columns=["a"]) != fingerprint_df(df2, columns=["a"])


def test_fingerprint_changes_when_extras_change():
    df = pd.DataFrame({"a": [1, 2]})
    k1 = fingerprint_df(df, columns=["a"], extras={"client": "1001"})
    k2 = fingerprint_df(df, columns=["a"], extras={"client": "1002"})
    assert k1 != k2


def test_cached_chart_writes_on_first_call(tmp_path):
    path = tmp_path / "chart.png"
    calls = []
    hit = cached_chart(path, "key-1", lambda p: (_stub_draw(p), calls.append(p)))
    assert hit is False
    assert path.exists()
    assert (tmp_path / "chart.png.cachekey").read_text() == "key-1"


def test_cached_chart_skips_on_matching_key(tmp_path):
    path = tmp_path / "chart.png"
    calls = []
    # First call: miss -> draws
    cached_chart(path, "key-1", lambda p: (_stub_draw(p), calls.append("first")))
    # Second call with same key: hit -> skips
    hit = cached_chart(path, "key-1", lambda p: (_stub_draw(p), calls.append("second")))
    assert hit is True
    assert calls == ["first"]  # second never ran


def test_cached_chart_re_renders_on_key_change(tmp_path):
    path = tmp_path / "chart.png"
    calls = []
    cached_chart(path, "key-1", lambda p: (_stub_draw(p), calls.append("first")))
    cached_chart(path, "key-2", lambda p: (_stub_draw(p), calls.append("second")))
    assert calls == ["first", "second"]
    assert (tmp_path / "chart.png.cachekey").read_text() == "key-2"


def test_cached_chart_re_renders_when_png_missing(tmp_path):
    path = tmp_path / "chart.png"
    calls = []
    cached_chart(path, "key-1", lambda p: (_stub_draw(p), calls.append("first")))
    # Someone deleted the PNG out from under us; sidecar still says key-1
    path.unlink()
    hit = cached_chart(path, "key-1", lambda p: (_stub_draw(p), calls.append("second")))
    assert hit is False  # cache miss because PNG is gone
    assert calls == ["first", "second"]


def test_cached_chart_respects_env_disable(tmp_path, monkeypatch):
    import importlib
    monkeypatch.setenv("ARS_CHART_CACHE", "0")
    # Reimport to pick up the new env value
    import ars_analysis.charts.cache as cache_mod
    importlib.reload(cache_mod)

    path = tmp_path / "chart.png"
    calls = []
    cache_mod.cached_chart(path, "k", lambda p: (_stub_draw(p), calls.append(1)))
    cache_mod.cached_chart(path, "k", lambda p: (_stub_draw(p), calls.append(2)))
    assert calls == [1, 2]  # disabled => draws every time

    # Restore for other tests
    monkeypatch.setenv("ARS_CHART_CACHE", "1")
    importlib.reload(cache_mod)


def test_purge_cache_removes_sidecars(tmp_path):
    (tmp_path / "a.png").write_text("")
    (tmp_path / "a.png.cachekey").write_text("k")
    (tmp_path / "b.png").write_text("")
    (tmp_path / "b.png.cachekey").write_text("k")
    n = purge_cache(tmp_path)
    assert n == 2
    assert not (tmp_path / "a.png.cachekey").exists()
    assert (tmp_path / "a.png").exists()  # PNG itself untouched
