"""Tests for the rates_audit denominator-law enforcement step."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from ars_analysis.pipeline.steps.audit import (
    DEFAULT_BY_PREFIX,
    LAW_LABELS,
    OPEN_ALLOWLIST,
    _default_label,
    _looks_like_rate,
    write_rates_audit,
)


@dataclass
class _FakeResult:
    slide_id: str = ""
    title: str = ""
    kpis: dict | None = None
    denominator_label: str = ""
    denominator_n: int = 0
    success: bool = True


@dataclass
class _FakePaths:
    base_dir: Path | None = None


@dataclass
class _FakeCtx:
    all_slides: list = field(default_factory=list)
    paths: _FakePaths = field(default_factory=_FakePaths)
    manifest: object = None


def test_law_labels_are_the_four_layers():
    assert LAW_LABELS == frozenset((
        "Eligible", "Eligible Personal", "Eligible Business", "Open",
    ))


def test_open_allowlist_contains_dctr_2():
    assert "dctr_2" in OPEN_ALLOWLIST
    assert "DCTR-2" in OPEN_ALLOWLIST


def test_default_label_dctr_is_eligible():
    assert _default_label("dctr_1") == "Eligible"
    assert _default_label("DCTR-7") == "Eligible"


def test_default_label_rege_is_eligible_personal():
    assert _default_label("rege_1") == "Eligible Personal"
    assert _default_label("REGE-2") == "Eligible Personal"


def test_default_label_unknown_returns_empty():
    assert _default_label("unknown_slide_xyz") == ""


def test_looks_like_rate_detects_rate_kpis():
    r = _FakeResult(kpis={"DCTR Rate": "30%"})
    assert _looks_like_rate(r) is True


def test_looks_like_rate_detects_explicit_stamp():
    r = _FakeResult(denominator_label="Eligible")
    assert _looks_like_rate(r) is True


def test_looks_like_rate_skips_non_rate():
    r = _FakeResult(kpis={"Total Accounts": "12,345"})
    assert _looks_like_rate(r) is False


def test_write_rates_audit_creates_csv_and_flags_violations(tmp_path):
    ctx = _FakeCtx()
    ctx.paths = _FakePaths(base_dir=tmp_path)
    ctx.all_slides = [
        _FakeResult(slide_id="dctr_1", title="DCTR Overall",
                    kpis={"DCTR Rate": "30%"}),  # default → Eligible (compliant)
        _FakeResult(slide_id="rege_1", title="Reg E Overall",
                    kpis={"Opt-In Rate": "45%"}),  # default → Eligible Personal
        _FakeResult(slide_id="mystery_1", title="Mystery",
                    kpis={"Some Rate": "10%"}),  # no default → empty label (violation)
        _FakeResult(slide_id="dctr_2", title="Open vs Eligible",
                    kpis={"DCTR Rate": "80%"},
                    denominator_label="Open"),  # Open allowed on dctr_2
        _FakeResult(slide_id="value_1", title="Revenue",
                    kpis={"Penetration Rate": "60%"},
                    denominator_label="Open"),  # Open NOT allowed here (violation)
    ]

    path, violations = write_rates_audit(ctx)
    assert path is not None
    assert path.name == "rates_audit.csv"
    assert violations == 2

    with open(path) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 5
    by_id = {r["slide_id"]: r for r in rows}
    assert by_id["dctr_1"]["framework_compliant"] == "True"
    assert by_id["dctr_1"]["denominator_label"] == "Eligible"
    assert by_id["rege_1"]["denominator_label"] == "Eligible Personal"
    assert by_id["mystery_1"]["framework_compliant"] == "False"
    assert by_id["dctr_2"]["framework_compliant"] == "True"
    assert by_id["value_1"]["framework_compliant"] == "False"
    assert "Open" in by_id["value_1"]["violation_reason"]


def test_write_rates_audit_returns_none_when_no_rate_slides(tmp_path):
    ctx = _FakeCtx()
    ctx.paths = _FakePaths(base_dir=tmp_path)
    ctx.all_slides = [
        _FakeResult(slide_id="dctr_1", title="DCTR", kpis={"Total": "100"}),
    ]
    path, violations = write_rates_audit(ctx)
    assert path is None
    assert violations == 0
    assert not (tmp_path / "rates_audit.csv").exists()
