"""Tests for ars_parity -- capture, normalization, comparison, sign-off."""

import json

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from ars_parity import signoff
from ars_parity.capture import RunSnapshot, capture_run, load_snapshot, save_snapshot
from ars_parity.compare import ComparePolicy, compare_snapshots, summarize
from ars_parity.figure_data import dump_figure_data, extract_figure_data
from ars_parity.normalize import normalize_df


class TestFigureData:
    def test_extracts_line_bar_pie(self):
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3)
        ax1.plot([1, 2, 3], [10.0, 20.0, 15.0], label="rate")
        ax2.bar(["a", "b"], [5, 7])
        ax3.pie([60, 40])
        data = extract_figure_data(fig)
        plt.close(fig)

        line = data["axes"][0]["lines"][0]
        assert line["y"] == [10.0, 20.0, 15.0]
        bars = data["axes"][1]["bars"]
        assert sorted(b["h"] for b in bars) == [5, 7]
        wedges = data["axes"][2]["wedges"]
        assert len(wedges) == 2
        # 60% wedge spans 216 degrees
        spans = sorted(w["theta2"] - w["theta1"] for w in wedges)
        assert spans == pytest.approx([144.0, 216.0], abs=1e-3)

    def test_nan_becomes_none(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [np.nan, 3.0])
        data = extract_figure_data(fig)
        plt.close(fig)
        assert data["axes"][0]["lines"][0]["y"] == [None, 3.0]

    def test_dump_writes_sidecar(self, tmp_path):
        fig, ax = plt.subplots()
        ax.plot([1], [1])
        out = dump_figure_data(fig, tmp_path / "chart_01.png")
        plt.close(fig)
        assert out == tmp_path / "chart_01.figdata.json"
        assert json.loads(out.read_text())["axes"]


class TestNormalize:
    def test_rows_sorted_and_nan_unified(self):
        df1 = pd.DataFrame({"k": ["b", "a"], "v": [2.0, np.nan]})
        df2 = pd.DataFrame({"k": ["a", "b"], "v": [np.nan, 2.0]})
        assert normalize_df(df1) == normalize_df(df2)

    def test_timestamps_serialized(self):
        df = pd.DataFrame({"d": [pd.Timestamp("2026-06-01")]})
        assert normalize_df(df)["rows"][0][0] == "2026-06-01T00:00:00"


def _snap(**overrides) -> RunSnapshot:
    base = RunSnapshot(
        client_id="1759",
        month="2026.06",
        product="ars",
        label="golden",
        slides={"A7.6a": {"module_id": "dctr.trends", "success": True,
                          "has_chart": True, "has_excel": True, "title": "t"}},
        sheets={"A7.6a_main": normalize_df(pd.DataFrame({"m": ["Jan"], "rate": [0.31]}))},
        figures={"A7.6a_dctr_01": {"axes": [{"lines": [{"y": [0.31]}]}]}},
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


class TestCompare:
    def test_identical_passes(self):
        assert compare_snapshots(_snap(), _snap(label="candidate")) == []

    def test_float_within_rtol_passes(self):
        cand = _snap(label="candidate")
        cand.sheets = {"A7.6a_main": normalize_df(pd.DataFrame({"m": ["Jan"], "rate": [0.31 + 1e-12]}))}
        assert compare_snapshots(_snap(), cand) == []

    def test_float_drift_fails(self):
        cand = _snap(label="candidate")
        cand.sheets = {"A7.6a_main": normalize_df(pd.DataFrame({"m": ["Jan"], "rate": [0.32]}))}
        diffs = compare_snapshots(_snap(), cand)
        assert len(diffs) == 1
        assert diffs[0].column == "rate"
        assert "FAIL" in summarize(diffs)

    def test_declared_column_relaxation(self):
        cand = _snap(label="candidate")
        cand.sheets = {"A7.6a_main": normalize_df(pd.DataFrame({"m": ["Jan"], "rate": [0.310000001]}))}
        policy = ComparePolicy(column_overrides={"A7.6a_*": {"rate": 1e-6}})
        assert compare_snapshots(_snap(), cand, policy) == []
        # without the declared relaxation the same drift fails
        assert compare_snapshots(_snap(), cand) != []

    def test_missing_slide_and_sheet_reported(self):
        cand = _snap(label="candidate", slides={}, sheets={}, figures={})
        diffs = compare_snapshots(_snap(), cand)
        surfaces = {d.surface for d in diffs}
        assert surfaces == {"slides", "sheet", "figure"}

    def test_prefix_scoping(self):
        cand = _snap(label="candidate", slides={}, sheets={}, figures={})
        diffs = compare_snapshots(_snap(), cand, ComparePolicy(slide_prefixes=("TXN-MERCH-",)))
        assert diffs == []  # A7.* slides out of scope

    def test_candidate_extras_are_reported(self):
        """Symmetry: an extra slide/sheet/figure only in the candidate is a
        diff -- otherwise renamed slides or lost golden figures pass silently."""
        cand = _snap(label="candidate")
        cand.slides = dict(cand.slides)
        cand.slides["A9.9"] = {"module_id": "m", "success": True,
                               "has_chart": True, "has_excel": False, "title": "x"}
        diffs = compare_snapshots(_snap(), cand)
        assert len(diffs) == 1
        assert diffs[0].candidate == "extra-in-candidate"
        # out-of-scope extras stay invisible
        assert compare_snapshots(
            _snap(), cand, ComparePolicy(slide_prefixes=("TXN-",))
        ) == []

    def test_int_counts_are_exact(self):
        gold = _snap(sheets={"A7.6a_main": normalize_df(pd.DataFrame({"n": [1000]}))})
        cand = _snap(label="candidate",
                     sheets={"A7.6a_main": normalize_df(pd.DataFrame({"n": [1001]}))})
        assert compare_snapshots(gold, cand) != []


class TestCaptureRoundTrip:
    def test_capture_save_load(self, tmp_path):
        run_dir = tmp_path / "run"
        (run_dir / "charts" / "merchant").mkdir(parents=True)
        (run_dir / "1759_2026.06_run_report.json").write_text(json.dumps({
            "slides": [{"slide_id": "TXN-MERCH-03", "module_id": "txn_merchant",
                        "success": True, "has_chart": True, "has_excel": False,
                        "title": "Top merchants"}]
        }))
        (run_dir / "charts" / "merchant" / "TXN-MERCH-03_x_01.figdata.json").write_text(
            json.dumps({"axes": []})
        )
        pd.DataFrame({"a": [1]}).to_excel(
            run_dir / "1759_2026.06_analysis.xlsx", sheet_name="TXN-MERCH-03_main", index=False
        )

        snap = capture_run(run_dir, "1759", "2026.06", "ars", "golden")
        assert "TXN-MERCH-03" in snap.slides
        assert "TXN-MERCH-03_main" in snap.sheets
        assert "TXN-MERCH-03_x_01" in snap.figures

        dest = save_snapshot(snap, tmp_path / "snap")
        loaded = load_snapshot(dest)
        assert loaded.slides == snap.slides
        assert loaded.sheets == snap.sheets


class TestSignoff:
    def test_approval_requires_two_passing_clients(self, tmp_path):
        p = tmp_path / "parity_status.json"
        signoff.record_check("txn.merchant", "1759", "2026.06", True, 0, path=p)
        with pytest.raises(ValueError):
            signoff.approve("txn.merchant", "JG", path=p)
        signoff.record_check("txn.merchant", "1615", "2026.06", True, 0, path=p)
        entry = signoff.approve("txn.merchant", "JG", path=p)
        assert entry["approved_by"] == "JG"
        assert signoff.is_approved("txn.merchant", path=p)

    def test_failed_check_voids_approval(self, tmp_path):
        p = tmp_path / "parity_status.json"
        signoff.record_check("ars.dctr", "1759", "2026.06", True, 0, path=p)
        signoff.record_check("ars.dctr", "1615", "2026.06", True, 0, path=p)
        signoff.approve("ars.dctr", "JG", path=p)
        signoff.record_check("ars.dctr", "1800", "2026.07", False, 12, path=p)
        assert not signoff.is_approved("ars.dctr", path=p)

    def test_documented_divergence_counts_as_passing(self, tmp_path):
        """The legacy oracle is sometimes wrong (Reg E B1 class): a failing
        check with an attributed reason counts toward approval."""
        p = tmp_path / "parity_status.json"
        signoff.record_check("ars.rege", "1759", "2026.06", False, 3, path=p,
                             divergence_reason="legacy B1 used wrong denominator",
                             divergence_by="JG")
        signoff.record_check("ars.rege", "1615", "2026.06", True, 0, path=p)
        entry = signoff.approve("ars.rege", "JG", path=p)
        assert entry["approved_by"] == "JG"
        rec = signoff.load_status(p)["ars.rege"]["checks"]["1759"]
        assert rec["divergence_by"] == "JG"
        assert rec["sha"]  # checks are SHA-stamped

    def test_divergence_requires_attribution(self, tmp_path):
        p = tmp_path / "parity_status.json"
        with pytest.raises(ValueError):
            signoff.record_check("x", "1", "2026.06", False, 1, path=p,
                                 divergence_reason="because")

    def test_checks_from_other_sha_dont_count(self, tmp_path):
        p = tmp_path / "parity_status.json"
        signoff.record_check("ars.value", "1759", "2026.06", True, 0, path=p)
        status = signoff.load_status(p)
        status["ars.value"]["checks"]["1759"]["sha"] = "deadbeef"  # older code
        signoff._save(status, p)
        assert signoff.passing_clients("ars.value", path=p) == []
