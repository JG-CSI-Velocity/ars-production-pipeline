"""run_module orchestration: it must build only the context a section needs,
run a TXN section's resolved upstreams (then the section) or an ARS section's
selected modules, and emit a scoped deck. Heavy analysis/deck calls are
monkeypatched -- this verifies the wiring, not the analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import runner
from shared.context import PipelineContext as SharedContext


@dataclass
class _FakeResult:
    slide_id: str
    title: str = "x"


def _ctx(tmp_path):
    return SharedContext(
        client_id="1776", client_name="CoastHills CU", csm="JamesG",
        analysis_date=date(2026, 6, 1), output_dir=tmp_path,
    )


class _FakeWrapper:
    calls: list[str] = []

    def __init__(self, name, path):
        self.section_name = name
        self.module_id = f"txn.{name}"
        self.failures = []

    def validate(self, ctx):
        return []

    def run(self, ctx, shared_namespace=None):
        _FakeWrapper.calls.append(self.section_name)
        return [_FakeResult(f"TXN-X-{self.section_name}")]


def _patch_txn(monkeypatch, deck_calls):
    import ars_analysis.analytics.txn_wrapper as tw
    import ars_analysis.output.deck_builder as db

    _FakeWrapper.calls = []
    monkeypatch.setattr(runner, "_load_client_config", lambda cfg: cfg)
    monkeypatch.setattr(runner, "_resolve_template_path", lambda: None)
    monkeypatch.setattr(tw, "prepare_shared_namespace", lambda ctx: {})
    monkeypatch.setattr(tw, "TXNSectionWrapper", _FakeWrapper)
    monkeypatch.setattr(db, "build_scoped_deck",
                        lambda ctx, section: deck_calls.append(section.section_id))


def test_leaf_runs_only_itself(tmp_path, monkeypatch):
    deck_calls: list[str] = []
    _patch_txn(monkeypatch, deck_calls)

    ctx = _ctx(tmp_path)
    runner.run_module(ctx, "txn.ICS_cohort")

    # ICS_cohort is a leaf -> no declared upstreams, but the 'general' baseline
    # always runs first (builds shared combined_df columns), then the target.
    assert _FakeWrapper.calls == ["general", "ICS_cohort"]
    assert deck_calls == ["txn.ICS_cohort"]
    # Only the TARGET section's slides go into the deck, not the baseline's.
    assert [s.slide_id for s in ctx.all_slides] == ["TXN-X-ICS_cohort"]


def test_coupled_runs_upstreams_first_but_scopes_to_target(tmp_path, monkeypatch):
    deck_calls: list[str] = []
    _patch_txn(monkeypatch, deck_calls)

    ctx = _ctx(tmp_path)
    runner.run_module(ctx, "txn.business_accts")

    # general baseline first, then merchant (produces merch_agg), then target.
    assert _FakeWrapper.calls == ["general", "merchant", "business_accts"]
    # Only the TARGET section's slides go into the deck, not the upstream's.
    assert [s.slide_id for s in ctx.all_slides] == ["TXN-X-business_accts"]
    assert deck_calls == ["txn.business_accts"]


def test_txn_run_sets_cache_sync(tmp_path, monkeypatch):
    """Single-module TXN runs write the parquet cache synchronously so a short
    run doesn't lose the first-ever build."""
    monkeypatch.delenv("TXN_CACHE_SYNC", raising=False)
    _patch_txn(monkeypatch, [])
    runner.run_module(_ctx(tmp_path), "txn.ICS_cohort")
    assert __import__("os").environ.get("TXN_CACHE_SYNC") == "1"


def test_ars_section_runs_overview_plus_selected(tmp_path, monkeypatch):
    import ars_analysis.analytics.registry as reg
    import ars_analysis.output.deck_builder as db
    import ars_analysis.pipeline.steps.analyze as an
    import ars_analysis.pipeline.steps.subsets as sub

    selected: list[list[str]] = []
    deck_calls: list[str] = []
    monkeypatch.setattr(runner, "_load_client_config", lambda cfg: cfg)
    monkeypatch.setattr(runner, "_resolve_template_path", lambda: None)
    monkeypatch.setattr(reg, "load_all_modules", lambda: None)
    monkeypatch.setattr(sub, "step_subsets", lambda ctx: None)

    def _fake_selected(ctx, module_ids):
        selected.append(list(module_ids))
        ctx.all_slides.append(_FakeResult("DCTR-1"))

    monkeypatch.setattr(an, "step_analyze_selected", _fake_selected)
    monkeypatch.setattr(db, "build_scoped_deck",
                        lambda ctx, section: deck_calls.append(section.section_id))

    ctx = _ctx(tmp_path)
    runner.run_module(ctx, "ars.dctr")

    ids = selected[0]
    assert any(m.startswith("overview.") for m in ids)   # foundational, always run
    assert any(m.startswith("dctr.") for m in ids)       # the selected section
    assert deck_calls == ["ars.dctr"]


def test_run_modules_txn_aggregates_once_deck_per_section(tmp_path, monkeypatch):
    """The batch path: prepare_shared_namespace (the ~25-min aggregation) runs
    ONCE for many TXN sections, each folder runs once, and a deck is built per
    selected section."""
    import ars_analysis.analytics.txn_wrapper as tw
    import ars_analysis.output.deck_builder as db

    deck_calls: list[str] = []
    setups = {"n": 0}
    _FakeWrapper.calls = []
    monkeypatch.setattr(runner, "_load_client_config", lambda cfg: cfg)
    monkeypatch.setattr(runner, "_resolve_template_path", lambda: None)

    def _fake_prepare(ctx):
        setups["n"] += 1
        return {}

    monkeypatch.setattr(tw, "prepare_shared_namespace", _fake_prepare)
    monkeypatch.setattr(tw, "TXNSectionWrapper", _FakeWrapper)
    monkeypatch.setattr(db, "build_scoped_deck",
                        lambda ctx, section: (deck_calls.append(section.section_id)
                                              or object()))

    ctx = _ctx(tmp_path)
    runner.run_modules(ctx, ["txn.ICS_cohort", "txn.business_accts"])

    assert setups["n"] == 1                       # aggregation happened ONCE
    assert set(deck_calls) == {"txn.ICS_cohort", "txn.business_accts"}
    # business_accts pulls merchant upstream; each folder runs at most once.
    assert _FakeWrapper.calls.count("merchant") == 1
    assert _FakeWrapper.calls.count("business_accts") == 1
    assert _FakeWrapper.calls.count("ICS_cohort") == 1


def test_run_modules_ars_sets_up_once_deck_per_section(tmp_path, monkeypatch):
    """ARS batch: subsets + overview run once, then a deck per selected section."""
    import ars_analysis.analytics.registry as reg
    import ars_analysis.output.deck_builder as db
    import ars_analysis.pipeline.steps.analyze as an
    import ars_analysis.pipeline.steps.subsets as sub

    subsets = {"n": 0}
    deck_calls: list[str] = []
    monkeypatch.setattr(runner, "_load_client_config", lambda cfg: cfg)
    monkeypatch.setattr(runner, "_resolve_template_path", lambda: None)
    monkeypatch.setattr(reg, "load_all_modules", lambda: None)
    monkeypatch.setattr(sub, "step_subsets", lambda ctx: subsets.__setitem__("n", subsets["n"] + 1))
    monkeypatch.setattr(an, "step_analyze_selected", lambda ctx, ids: None)
    monkeypatch.setattr(db, "build_scoped_deck",
                        lambda ctx, section: (deck_calls.append(section.section_id)
                                              or object()))

    ctx = _ctx(tmp_path)
    runner.run_modules(ctx, ["ars.dctr", "ars.rege"])

    assert subsets["n"] == 1                      # ARS setup happened ONCE
    assert deck_calls == ["ars.dctr", "ars.rege"]
