"""Per-section smoke applied to EVERY TXN section: run its data-aggregation
script over the shared synthetic fixtures (combined_df + rewards_df + theme) and
assert it executes. All 23 sections run on the shared fixtures.
"""

from __future__ import annotations

import contextlib
import io

import pytest

from ars_analysis.analytics.section_registry import txn_sections

from _fixtures import namespace_with_theme, synthetic_combined, synthetic_rewards

# Every TXN section's 00/01 data script now runs over the shared fixture.
# (payroll used to be gapped, but that was a real pandas-3.x bug -- a float64
# payroll_source column rejecting string processor names -- now fixed in
# payroll/01, not a fixture limitation.)
_KNOWN_GAPS: dict[str, str] = {}

_FOLDERS = [s.folder for s in txn_sections()]


@pytest.mark.parametrize("folder", _FOLDERS)
def test_section_data_script_smoke(folder):
    if folder in _KNOWN_GAPS:
        pytest.xfail(_KNOWN_GAPS[folder])

    from _fixtures import ANALYTICS
    # Run the section's config (00_*) then its data script (01_*), so
    # config-driven sections (e.g. ICS_cohort's odd_df->data bridge) work.
    scripts = sorted((ANALYTICS / folder).glob("0[01]_*.py"))
    if not scripts:
        pytest.skip("no 00/01 data script")

    ns = namespace_with_theme()
    combined = synthetic_combined()
    rewards = synthetic_rewards()
    ns["combined_df"] = combined
    ns["combined_df_all"] = combined
    ns["rewards_df"] = rewards
    ns["odd_df"] = rewards
    ns["data"] = rewards
    # business/personal split frames (normally from txn_setup).
    ns["business_df"] = combined.copy()
    ns["personal_df"] = combined.copy()

    with contextlib.redirect_stdout(io.StringIO()):
        for scr in scripts:
            exec(compile(scr.read_text(encoding="utf-8"),  # noqa: S102
                         str(scr), "exec"), ns)


def test_smoke_covers_all_sections():
    """Guardrail: every TXN section runs on the shared fixture -- no gaps."""
    assert _KNOWN_GAPS == {}
    assert len(_FOLDERS) - len(_KNOWN_GAPS) == len(_FOLDERS)
