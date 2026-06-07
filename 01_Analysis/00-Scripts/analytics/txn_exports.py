"""Declarations of which variables each TXN script exposes to ctx.results.

Each entry maps a (section, script_number) tuple to a list of namespace
variable names that the TXN-results adapter copies into
`ctx.results[f"{section}_{script_number}"]["insights"]` after the script runs.

Schema:
    SECTION_EXPORTS[(section, script_number)] = {
        "insights": ["var_name", ...],  # bare scalars / strings the slide spec reads
        "tables":   ["var_name", ...],  # DataFrames (rarely surfaced in headlines)
    }

Variables that aren't in the namespace when the adapter runs are silently
skipped (logged at DEBUG). That lets a partially-implemented script survive
without breaking the adapter -- the slide spec falls back to its lenient
placeholder behavior.

To add a new export:
1. Find the TXN script (e.g. analytics/competition/13_threat_quadrant.py).
2. Identify the bare variable in its namespace that holds the value you want.
3. Add an entry below; the key is (section_name, script_number).

To rename a TXN script: rename only -- don't renumber. The script number is
the registry's stable key.

See docs/txn-results-adapter-design.md for the full design rationale.
"""

from __future__ import annotations

from typing import Any

# Per-script export declarations.
# Empty lists are placeholders for known-interesting scripts whose namespace
# variables haven't been wired yet -- the registry doubles as a TODO list.
SECTION_EXPORTS: dict[tuple[str, int], dict[str, list[str]]] = {
    # competition section
    (
        "competition",
        13,
    ): {  # 13_threat_quadrant.py -- "who's eating our card spend"
        "insights": [
            "top_competitor",     # str: top out-of-network spender by share
            "top_share",          # float 0..1: top competitor's share
            "second_competitor",
            "second_share",
            "threat_count",       # int: competitors above the threshold
        ],
        "tables": ["threat_quadrant_df"],
    },
    (
        "competition",
        24,
    ): {  # 24_segment_heatmap.py -- wallet-share by segment
        "insights": [
            "wallet_share_pct",     # float 0..1
            "wallet_gap_dollars",   # float: annualized leakage estimate
        ],
        "tables": ["segment_heatmap_df"],
    },

    # executive section (TXN executive scorecard + action roadmap)
    (
        "executive",
        1,
    ): {  # 01_kpi_scorecard.py -- top-of-deck portfolio KPIs
        "insights": [
            "total_active_accounts",
            "total_swipes",
            "total_spend",
            "avg_spend_per_account",
            "interchange_revenue",
        ],
    },
    (
        "executive",
        5,
    ): {  # 05_action_roadmap.py -- prioritized initiatives
        "insights": [
            "n_actions",
            "total_impact",
            "top_action",
        ],
    },
}


def get_exports(section: str, script_number: int) -> dict[str, list[str]] | None:
    """Return the export declaration for one script, or None if not registered."""
    return SECTION_EXPORTS.get((section, script_number))
