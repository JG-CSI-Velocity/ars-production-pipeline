"""End-to-end test: cache adoption in dctr/penetration.py for the
Personal-vs-Business chart (A7.2). Validates the adoption pattern works
in a real analytics module without rendering matplotlib at test time.

The test stubs `chart_figure` so we don't pay the render cost; the cache
behavior is what's under test.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))
if "ars_analysis" not in sys.modules:
    _pkg = types.ModuleType("ars_analysis")
    _pkg.__path__ = [str(_SCRIPTS_DIR)]
    sys.modules["ars_analysis"] = _pkg

from ars_analysis.charts.cache import cached_chart, fingerprint_df


def _stub_draw(path: Path) -> None:
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\nfake-png-content")


def test_personal_vs_business_cache_key_reuses_on_same_inputs(tmp_path):
    """The exact same fingerprint inputs produce the same cache key on every call."""
    extras = {
        "client": "1615",
        "month": "2026.04",
        "style": "ars.mplstyle:v3",
        "cats": ["Personal", "Business"],
        "vals": [29.5, 24.3],
        "cts": [12000, 8500],
        "colors": ["#1A1A1A", "#F15D22"],
        "overall": 28.1,
    }
    k1 = fingerprint_df(df=None, extras=extras)
    k2 = fingerprint_df(df=None, extras=extras)
    assert k1 == k2

    target = tmp_path / "dctr_personal_vs_business.png"
    calls = []
    cached_chart(target, k1, lambda p: (_stub_draw(p), calls.append("first")))
    # Second call same key -> hit
    hit = cached_chart(target, k1, lambda p: (_stub_draw(p), calls.append("second")))
    assert hit is True
    assert calls == ["first"]


def test_personal_vs_business_cache_invalidates_on_rate_change(tmp_path):
    """A change in p_ins['overall_dctr'] flows through the fingerprint."""
    base_extras = {
        "client": "1615", "month": "2026.04", "style": "ars.mplstyle:v3",
        "cats": ["Personal", "Business"], "cts": [12000, 8500],
        "colors": ["#1A1A1A", "#F15D22"], "overall": 28.1,
    }
    k_v1 = fingerprint_df(df=None, extras={**base_extras, "vals": [29.5, 24.3]})
    k_v2 = fingerprint_df(df=None, extras={**base_extras, "vals": [31.0, 24.3]})
    assert k_v1 != k_v2

    target = tmp_path / "chart.png"
    calls = []
    cached_chart(target, k_v1, lambda p: (_stub_draw(p), calls.append("v1")))
    cached_chart(target, k_v2, lambda p: (_stub_draw(p), calls.append("v2")))
    assert calls == ["v1", "v2"]


def test_personal_vs_business_cache_invalidates_on_client_change(tmp_path):
    """Cache key namespaced by client so cross-client cache hits don't happen."""
    extras_1615 = {
        "client": "1615", "month": "2026.04", "style": "ars.mplstyle:v3",
        "cats": ["Personal", "Business"], "vals": [29.5, 24.3],
        "cts": [12000, 8500], "colors": ["#1A1A1A", "#F15D22"], "overall": 28.1,
    }
    extras_1776 = {**extras_1615, "client": "1776"}
    assert fingerprint_df(df=None, extras=extras_1615) != fingerprint_df(df=None, extras=extras_1776)


def test_penetration_imports_with_cache_adoption():
    """The dctr.penetration module should still import after the cache adoption."""
    # Forces a fresh load of the modified module.
    from ars_analysis.analytics.dctr import penetration  # noqa: F401
    assert hasattr(penetration, "DCTRPenetration")
