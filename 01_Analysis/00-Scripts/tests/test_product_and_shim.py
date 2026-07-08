"""Phase 0 regression tests for the module closed-loop refactor.

1. The TXN execution namespace must provide a `display_formatted` shim so the
   ~40 notebook-era call sites (all of ICS_cohort, unguarded) stop raising
   NameError and taking their charts down with them (#241).
2. The `_txn_suffix` product logic must yield '_txn' for TXN runs so the deck /
   Excel / run-report / audit stop overwriting the ARS artifacts (#product).
"""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd


def _fake_ctx(product=None):
    client = SimpleNamespace(
        client_id="1776", client_name="CoastHills CU", month="2026.06",
        assigned_csm="JamesG", eligible_stat_codes=["O"],
    )
    ctx = SimpleNamespace(client=client, data=None, settings=None)
    if product is not None:
        ctx.product = product
    return ctx


def test_namespace_provides_display_formatted():
    from ars_analysis.analytics import txn_wrapper

    ns = txn_wrapper._build_namespace(_fake_ctx())
    assert "display_formatted" in ns, "display_formatted missing from TXN namespace"
    fn = ns["display_formatted"]
    assert callable(fn)
    # Must tolerate every call shape the cells use, without raising.
    fn(pd.DataFrame({"a": [1, 2]}), "Some Title")
    fn(pd.DataFrame({"a": [1]}))
    fn("just a string")
    fn()


def test_display_formatted_does_not_abort_execution():
    """A bare call (the ICS_cohort pattern) must return, not raise -- proving a
    cell that also builds a chart would survive to render it."""
    from ars_analysis.analytics import txn_wrapper

    ns = txn_wrapper._build_namespace(_fake_ctx())
    code = "display_formatted(df, 'Portfolio Totals')\nrendered = True\n"
    ns["df"] = pd.DataFrame({"x": [1]})
    exec(compile(code, "<cell>", "exec"), ns)  # noqa: S102 -- mirrors runtime exec
    assert ns.get("rendered") is True


def test_txn_suffix_reflects_product():
    from ars_analysis.pipeline.steps.generate import _txn_suffix

    assert _txn_suffix(_fake_ctx(product="txn")) == "_txn"
    assert _txn_suffix(_fake_ctx(product="ars")) == ""
    assert _txn_suffix(_fake_ctx(product="combined")) == ""
