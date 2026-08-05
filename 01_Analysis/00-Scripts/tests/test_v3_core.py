"""Tests for ars_engine.core -- the unified context/result/config contracts."""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ars_engine.core import (
    ClientInfo,
    OutputPaths,
    PipelineContext,
    SlideSpec,
    as_of_ts,
    from_legacy_result,
)
from ars_engine.core.config import engine_for_section, load_engine_flags


def _ctx(month: str = "2026.06") -> PipelineContext:
    ci = ClientInfo(client_id="1759", client_name="Test Bank", month=month)
    return PipelineContext(client=ci, paths=OutputPaths.from_dir(Path("/tmp/ars-test")))


class TestClientInfo:
    def test_from_client_config_scalar_codes_wrapped(self):
        ci = ClientInfo.from_client_config(
            "1759", "Test Bank", "2026.06", {"EligibleStatusCodes": "A", "ICRate": "1.25"}
        )
        assert ci.eligible_stat_codes == ["A"]
        assert ci.ic_rate == 1.25

    def test_from_client_config_bad_float_defaults_zero(self):
        ci = ClientInfo.from_client_config("1", "", "2026.06", {"NSF_OD_Fee": "n/a"})
        assert ci.nsf_od_fee == 0.0
        assert ci.client_name == "1"  # falls back to id

    def test_from_client_config_list_passthrough(self):
        ci = ClientInfo.from_client_config(
            "1", "X", "2026.06", {"EligibleProductCodes": ["DDA", "SAV"]}
        )
        assert ci.eligible_prod_codes == ["DDA", "SAV"]


class TestL12MWindow:
    def test_window_for_june_2026(self):
        ctx = _ctx("2026.06")
        ctx.compute_l12m_window()
        assert ctx.l12m_start == pd.Timestamp("2025-06-01")
        assert ctx.l12m_end == pd.Timestamp("2026-05-31")

    def test_in_l12m_mask(self):
        ctx = _ctx("2026.06")
        s = pd.Series(pd.to_datetime(["2025-05-31", "2025-06-01", "2026-05-31", "2026-06-01"]))
        mask = ctx.in_l12m(s)
        assert mask.tolist() == [False, True, True, False]

    def test_analysis_date_from_month(self):
        assert _ctx("2026.06").analysis_date == date(2026, 6, 1)

    def test_as_of_ts_uses_end_date_not_wall_clock(self):
        ctx = _ctx()
        ctx.end_date = pd.Timestamp("2026-05-31")
        assert as_of_ts(ctx) == pd.Timestamp("2026-05-31")


class TestSlideSpecAdapter:
    def test_adapts_analytics_base_shape(self):
        class LegacyDeckResult:  # analytics/base.py field set
            slide_id = "A7.6a"
            title = "DCTR Trend"
            chart_path = Path("/tmp/c.png")
            excel_data = {"main": pd.DataFrame({"x": [1]})}
            notes = "n"
            success = True
            error = ""
            layout_index = 8
            slide_type = "screenshot"
            kpis = {"rate": "31%"}
            extra_charts = None
            bullets = None
            title_color = None
            denominator_label = "Eligible"
            denominator_n = 1234

        s = from_legacy_result(LegacyDeckResult())
        assert s.slide_id == "A7.6a"
        assert s.denominator_label == "Eligible"
        assert s.denominator_n == 1234
        assert not s.df.empty

    def test_adapts_shared_types_shape(self):
        class LegacyRunnerResult:  # shared/types.py field set
            name = "top_merchants"
            title = "Top Merchants"
            data = {"main": pd.DataFrame({"m": ["a"]})}
            charts = [Path("/tmp/1.png"), Path("/tmp/2.png")]
            error = None
            summary = "s"
            metadata = {"slide_id": "TXN-MERCH-03", "insights": {"top": "a"}}

        s = from_legacy_result(LegacyRunnerResult())
        assert s.slide_id == "TXN-MERCH-03"
        assert s.chart_path == Path("/tmp/1.png")
        assert s.extra_charts == [Path("/tmp/2.png")]
        assert s.success
        assert s.insights == {"top": "a"}

    def test_slidespec_passthrough(self):
        s = SlideSpec(slide_id="X", title="t")
        assert from_legacy_result(s) is s

    def test_rejects_unknown_shape(self):
        with pytest.raises(TypeError):
            from_legacy_result(object())


class TestEngineFlags:
    def test_missing_file_means_old(self, tmp_path):
        flags = load_engine_flags(tmp_path / "nope.json")
        assert flags == {}
        assert engine_for_section("txn.merchant", flags) == "old"

    def test_new_flag_routes_new(self, tmp_path):
        p = tmp_path / "engine_flags.json"
        p.write_text('{"txn.merchant": "new", "ars.dctr": "garbage"}')
        flags = load_engine_flags(p)
        assert engine_for_section("txn.merchant", flags) == "new"
        # unknown values coerce to old, never accidentally new
        assert engine_for_section("ars.dctr", flags) == "old"
