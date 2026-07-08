"""The uniform Module contract must hold for EVERY section -- this is the
machine-checkable core of the uniform rewrite. If any section's dependency
contract is malformed (missing folder, unknown/self upstream, TXN without a
slide code), it fails here rather than at run time with a broken deck."""

from __future__ import annotations

import pytest

from ars_analysis.analytics import module as mod


def test_all_sections_expose_a_module():
    mods = mod.all_modules()
    assert len(mods) == 30  # 7 ars.* + 23 txn.*
    assert {m.product for m in mods} == {"ars", "txn"}


@pytest.mark.parametrize("m", mod.all_modules(), ids=lambda m: m.id)
def test_every_module_contract_is_wellformed(m):
    assert m.validate_contract() == []


def test_leaf_and_aggregator_classification():
    by_id = {m.id: m for m in mod.all_modules()}
    # ICS_cohort is a genuine leaf (ODD-only).
    assert by_id["txn.ICS_cohort"].is_leaf
    assert by_id["txn.ICS_cohort"].requires_modules() == []
    # executive aggregates many upstream sections.
    assert by_id["txn.executive"].is_aggregator
    assert "txn.general" in by_id["txn.business_accts"].requires_modules()


def test_run_delegates_to_run_module(monkeypatch):
    calls = []
    import ars_analysis.runner as runner
    monkeypatch.setattr(runner, "run_module", lambda ctx, sid: calls.append(sid))
    mod.get_module_spec("txn.merchant").run(ctx=None)
    assert calls == ["txn.merchant"]
