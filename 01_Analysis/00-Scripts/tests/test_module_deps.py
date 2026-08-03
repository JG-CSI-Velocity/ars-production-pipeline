"""The cross-section dependency analysis must surface the real coupling the
closed-loop runner designs around, and resolve a section's run-before set."""

from __future__ import annotations

from ars_analysis.analytics import section_deps


def test_ics_cohort_is_a_leaf():
    """ICS_cohort is the Phase-2 leaf pilot: ODD-only, no cross-section deps."""
    graph = section_deps.dependency_graph()
    assert graph["ICS_cohort"]["depends_on_sections"] == []
    assert section_deps.upstream_sections("ICS_cohort") == []


def test_promotion_collapsed_general_deps():
    """After promoting general's theme AND data producers into shared setup,
    the shared names (GEN_COLORS, demo_df, acct_txn_counts, swipe_lookup) are no
    longer cross-section deps, so general has few remaining dependents."""
    graph = section_deps.dependency_graph()
    names = {n for g in graph.values() for n in g["cross_section_names"]}
    for shared in ("GEN_COLORS", "gen_clean_axes", "demo_df",
                   "acct_txn_counts", "swipe_lookup"):
        assert shared not in names, f"{shared} should be promoted out of the graph"


def test_promoted_names_include_theme_and_producers():
    promoted = section_deps.theme_names()
    assert {"GEN_COLORS", "gen_clean_axes", "gen_fmt_dollar"} <= promoted  # theme
    assert {"demo_df", "acct_txn_counts", "swipe_lookup"} <= promoted      # producers


def test_leaked_locals_are_filtered():
    graph = section_deps.dependency_graph()
    for g in graph.values():
        assert "e" not in g["cross_section_names"]
        assert "e" not in g["unresolved_names"]


def test_missing_section_deps_flags_absent_names():
    """business_accts requires merch_agg (from merchant) and general theme
    names; an empty namespace is missing them -> hard error material."""
    missing = section_deps.missing_section_deps("business_accts", {})
    assert "merch_agg" in missing
    # A namespace that supplies everything the section needs -> nothing missing.
    full = dict.fromkeys(section_deps.required_names("business_accts"), 1)
    assert section_deps.missing_section_deps("business_accts", full) == []


def test_leaf_has_no_required_names():
    assert section_deps.required_names("ICS_cohort") == []
    assert section_deps.missing_section_deps("ICS_cohort", {}) == []


def test_upstreams_use_primary_producer():
    """merchant produces merch_agg (sole producer) -> business_accts must run
    merchant. general is NOT needed anymore: its theme + demo_df/acct_txn_counts
    are promoted to shared setup, so the upstream set is just the real data
    producer."""
    up = section_deps.upstream_sections("business_accts")
    assert up == ["merchant"]
