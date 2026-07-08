"""The cross-section dependency analysis must surface the real coupling the
closed-loop runner designs around, and resolve a section's run-before set."""

from __future__ import annotations

from ars_analysis.analytics import section_deps


def test_ics_cohort_is_a_leaf():
    """ICS_cohort is the Phase-2 leaf pilot: ODD-only, no cross-section deps."""
    graph = section_deps.dependency_graph()
    assert graph["ICS_cohort"]["depends_on_sections"] == []
    assert section_deps.upstream_sections("ICS_cohort") == []


def test_general_is_the_shared_hub():
    graph = section_deps.dependency_graph()
    dependents = [s for s, g in graph.items()
                  if "general" in g["depends_on_sections"]]
    assert len(dependents) >= 10
    names = {n for g in graph.values() for n in g["cross_section_names"]}
    assert "GEN_COLORS" in names
    assert "demo_df" in names


def test_leaked_locals_are_filtered():
    graph = section_deps.dependency_graph()
    for g in graph.values():
        assert "e" not in g["cross_section_names"]
        assert "e" not in g["unresolved_names"]


def test_upstreams_use_primary_producer():
    """merchant produces merch_agg (sole producer) -> business_accts must run
    merchant; theme names collapse to `general`, not the many defensive
    re-assigners, so the upstream set stays tight."""
    up = section_deps.upstream_sections("business_accts")
    assert "merchant" in up
    assert "general" in up
    # `general` runs before `merchant` (execution order 100 < 110).
    assert up.index("general") < up.index("merchant")
