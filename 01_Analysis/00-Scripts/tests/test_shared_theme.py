"""The shared theme promotion must actually load at runtime: after
_load_shared_theme, the namespace carries GEN_COLORS + the gen_* helpers, so a
section can run without the `general` section having run first."""

from __future__ import annotations

from types import SimpleNamespace


def test_load_shared_theme_populates_namespace():
    from ars_analysis.analytics import txn_wrapper as tw

    ctx = SimpleNamespace(
        client=SimpleNamespace(client_id="1776", client_name="CoastHills CU",
                               month="2026.06", assigned_csm="JamesG",
                               eligible_stat_codes=["O"]),
        data=None,
    )
    ns = tw._build_namespace(ctx)
    tw._load_shared_theme(ns)

    assert "GEN_COLORS" in ns and isinstance(ns["GEN_COLORS"], dict)
    assert callable(ns.get("gen_clean_axes"))
    assert callable(ns.get("gen_fmt_dollar"))
    # A representative palette/order constant is present too.
    assert "AGE_ORDER" in ns


def test_load_shared_producers_builds_frames():
    """The promoted data producers run over a combined_df and populate the
    shared frames (2 of 3 need only combined_df; demo_df needs the ODD-merged
    frame a real run provides, so it's allowed to no-op here)."""
    from _fixtures import namespace_with_theme, synthetic_combined, synthetic_rewards
    from ars_analysis.analytics import txn_wrapper as tw

    ns = namespace_with_theme()
    ns["combined_df"] = synthetic_combined()
    ns["combined_df_all"] = ns["combined_df"]
    ns["rewards_df"] = synthetic_rewards()
    ns["odd_df"] = ns["rewards_df"]

    tw._load_shared_producers(ns)  # guarded -- never raises

    # acct_txn_counts (engagement) and swipe_lookup run on combined_df alone.
    assert "acct_txn_counts" in ns
    assert "swipe_lookup" in ns
