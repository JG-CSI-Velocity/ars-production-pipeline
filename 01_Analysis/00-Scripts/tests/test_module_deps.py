"""The cross-section dependency audit must surface the real coupling that the
closed-loop refactor has to design around (silent skips otherwise hide it)."""

from __future__ import annotations

import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import module_deps  # noqa: E402


def test_ics_cohort_is_a_leaf():
    """ICS_cohort is the Phase-2 leaf pilot: ODD-only, no cross-section deps."""
    graph = module_deps.analyze()
    assert "ICS_cohort" in graph
    assert graph["ICS_cohort"]["depends_on_sections"] == []


def test_general_is_the_shared_hub():
    """Many sections depend on `general` (theme, formatters, demo_df,
    acct_txn_counts) -- the promote-to-shared-setup target."""
    graph = module_deps.analyze()
    dependents = [s for s, g in graph.items()
                  if "general" in g["depends_on_sections"]]
    assert len(dependents) >= 10
    # demo_df / acct_txn_counts / GEN_COLORS are real cross-section names.
    names = {n for g in graph.values() for n in g["cross_section_names"]}
    assert "GEN_COLORS" in names
    assert "demo_df" in names


def test_leaked_locals_are_filtered():
    graph = module_deps.analyze()
    for g in graph.values():
        assert "e" not in g["cross_section_names"]
        assert "e" not in g["unresolved_names"]
