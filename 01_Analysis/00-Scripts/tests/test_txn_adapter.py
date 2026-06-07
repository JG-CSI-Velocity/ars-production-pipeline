"""Tests for the TXN-results adapter (txn_wrapper.expose_to_ctx_results)."""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))
if "ars_analysis" not in sys.modules:
    _pkg = types.ModuleType("ars_analysis")
    _pkg.__path__ = [str(_SCRIPTS_DIR)]
    sys.modules["ars_analysis"] = _pkg

from ars_analysis.analytics.txn_exports import SECTION_EXPORTS, get_exports
from ars_analysis.analytics.txn_wrapper import (
    _extract_script_number,
    expose_to_ctx_results,
)


@dataclass
class _StubCtx:
    """Minimal duck-typed PipelineContext for adapter tests."""
    results: dict = field(default_factory=dict)


def test_extract_script_number_handles_standard_names():
    assert _extract_script_number("01_kpi_scorecard.py") == 1
    assert _extract_script_number("13_threat_quadrant.py") == 13
    assert _extract_script_number("70_banking_vs_ecosystems.py") == 70


def test_extract_script_number_returns_none_for_unprefixed():
    assert _extract_script_number("competitor_config.py") is None
    assert _extract_script_number("foo.py") is None


def test_get_exports_returns_competition_13_entry():
    exports = get_exports("competition", 13)
    assert exports is not None
    assert "top_competitor" in exports["insights"]
    assert "top_share" in exports["insights"]
    assert "threat_quadrant_df" in exports["tables"]


def test_get_exports_returns_none_for_unregistered_script():
    assert get_exports("competition", 999) is None
    assert get_exports("nonexistent_section", 1) is None


def test_expose_to_ctx_results_copies_declared_variables():
    ctx = _StubCtx()
    namespace = {
        "top_competitor": "Big National Bank",
        "top_share": 0.27,
        "second_competitor": "Mega CU",
        "second_share": 0.18,
        "threat_count": 12,
        "threat_quadrant_df": "<DataFrame stand-in>",
        "irrelevant_var": "should not be copied",
    }
    expose_to_ctx_results(
        ctx, namespace, "competition", 13, Path("13_threat_quadrant.py")
    )
    bucket = ctx.results["competition_13"]
    assert bucket["script"] == "13_threat_quadrant.py"
    assert bucket["insights"]["top_competitor"] == "Big National Bank"
    assert bucket["insights"]["top_share"] == 0.27
    assert bucket["insights"]["threat_count"] == 12
    assert bucket["tables"]["threat_quadrant_df"] == "<DataFrame stand-in>"
    # Vars not in the export registry don't leak in
    assert "irrelevant_var" not in bucket["insights"]


def test_expose_to_ctx_results_silently_skips_missing_namespace_vars():
    """Partially-failed scripts shouldn't break the adapter."""
    ctx = _StubCtx()
    namespace = {"top_competitor": "BigBank"}  # missing top_share, threat_count
    expose_to_ctx_results(ctx, namespace, "competition", 13, Path("13_foo.py"))
    bucket = ctx.results["competition_13"]
    assert bucket["insights"] == {"top_competitor": "BigBank"}
    # No KeyError on missing vars


def test_expose_to_ctx_results_noop_when_no_registry_entry():
    """Unregistered (section, script_n) tuples are silently ignored."""
    ctx = _StubCtx()
    expose_to_ctx_results(ctx, {"some_var": 1}, "competition", 999, Path("999_x.py"))
    assert ctx.results == {}


def test_expose_to_ctx_results_noop_when_ctx_is_none():
    """txn_setup runs without a usable ctx -- the adapter must tolerate it."""
    # Should not raise
    expose_to_ctx_results(None, {"top_competitor": "x"}, "competition", 13, Path("13.py"))


def test_executive_exports_registered():
    """Both executive scorecard + roadmap need export declarations."""
    assert get_exports("executive", 1) is not None
    assert "interchange_revenue" in get_exports("executive", 1)["insights"]
    assert get_exports("executive", 5) is not None
    assert "top_action" in get_exports("executive", 5)["insights"]


def test_section_exports_keys_are_well_formed():
    """Every registry entry has a (str, int) key and dict value."""
    for key, value in SECTION_EXPORTS.items():
        assert isinstance(key, tuple) and len(key) == 2
        assert isinstance(key[0], str) and key[0]
        assert isinstance(key[1], int) and key[1] > 0
        assert isinstance(value, dict)
        # Insights / tables, both optional but if present must be list[str]
        for field_name in ("insights", "tables"):
            if field_name in value:
                assert isinstance(value[field_name], list)
                for v in value[field_name]:
                    assert isinstance(v, str) and v
