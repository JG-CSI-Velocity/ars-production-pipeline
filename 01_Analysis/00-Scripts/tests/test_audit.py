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


def test_law_labels_are_the_framework_layers():
    assert LAW_LABELS == frozenset((
        "Eligible", "Eligible Personal", "Eligible Personal w/Debit",
        "Eligible Business", "Open",
    ))


def test_open_allowlist_contains_dctr_2():
    assert "dctr_2" in OPEN_ALLOWLIST
    assert "DCTR-2" in OPEN_ALLOWLIST


def test_default_label_dctr_is_eligible():
    assert _default_label("dctr_1") == "Eligible"
    assert _default_label("DCTR-7") == "Eligible"


def test_default_label_rege_is_eligible_personal_w_debit():
    assert _default_label("rege_1") == "Eligible Personal w/Debit"
    assert _default_label("REGE-2") == "Eligible Personal w/Debit"


def test_default_label_unknown_returns_empty():
    assert _default_label("unknown_slide_xyz") == ""


def test_default_label_specific_prefix_beats_generic():
    # Original bug: 'A1' would match 'A11.1' before 'A11' got a chance.
    # _default_label sorts prefixes by descending length to prevent that.
    assert _default_label("A11.1") == "Eligible"   # value, not overview
    assert _default_label("A12.Jan26") == "Eligible"  # mailer aggregate
    assert _default_label("A13.Agg") == "Eligible"
    assert _default_label("A14.1") == "Eligible"   # mailer reach
    assert _default_label("A1.1") == "Eligible"   # overview still resolves
    assert _default_label("A1") == "Eligible"


def test_a8_prefix_resolves_to_eligible_personal():
    """Reg E A8.x slides anchor to Eligible Personal w/Debit (owner decision)."""
    for sid in ("A8.1", "A8.2", "A8.3", "A8.12"):
        assert _default_label(sid) == "Eligible Personal w/Debit"


def test_a7_prefix_resolves_to_eligible():
    """DCTR A7.x slides should all anchor to Eligible."""
    for sid in ("A7.1", "A7.2", "A7.3", "A7.6a"):
        assert _default_label(sid) == "Eligible"


def test_default_label_covers_authored_spec_slides():
    """Every section authored in W3 specs should resolve to a 4-layer label."""
    valid = {"Eligible", "Eligible Personal", "Eligible Personal w/Debit",
             "Eligible Business", "Open"}
    for sid in ("DCTR-MAIN-1", "REGE-MAIN-1", "OVERVIEW-MAIN-1",
                "ATTRITION-MAIN-1", "VALUE-MAIN-1", "INSIGHTS-MAIN-1"):
        assert _default_label(sid) in valid, f"{sid}: not registered"


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
    assert by_id["rege_1"]["denominator_label"] == "Eligible Personal w/Debit"
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
