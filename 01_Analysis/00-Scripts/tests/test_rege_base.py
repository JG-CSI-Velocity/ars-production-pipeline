"""Locks the Reg E rate definition: personal w/ Reg E / eligible personal w/ debit.

Owner decision 2026-06-11. If this test fails, someone changed the Reg E
base -- check with the owner before shipping.
"""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from ars_analysis.analytics.rege._helpers import reg_e_base, rege


def _ctx(eligible_personal: pd.DataFrame) -> SimpleNamespace:
    return SimpleNamespace(
        client=SimpleNamespace(
            reg_e_opt_in=["Opt In"],
            reg_e_column="Reg E Code Jan26",
        ),
        data=eligible_personal,
        subsets=SimpleNamespace(eligible_personal=eligible_personal),
        start_date=None,
        end_date=None,
    )


def test_reg_e_base_is_eligible_personal_with_debit():
    ep = pd.DataFrame({
        # 4 debit holders (2 opted in), 3 without debit (all "opted in" --
        # they must NOT count in either numerator or denominator)
        "Debit?":           ["Yes", "Yes", "Yes", "Yes", "No", "No", ""],
        "Reg E Code Jan26": ["Opt In", "Opt In", "Opt Out Reply", "Mandatory",
                             "Opt In", "Opt In", "Opt In"],
    })
    base, base_l12m, col, opts = reg_e_base(_ctx(ep))

    assert len(base) == 4, "base must be debit holders only"
    t, oi, rate = rege(base, col, opts)
    assert (t, oi) == (4, 2)
    assert rate == 0.5  # 2 opted-in / 4 eligible personal w/debit


def test_reg_e_base_raises_when_no_debit_holders():
    ep = pd.DataFrame({
        "Debit?": ["No", "No"],
        "Reg E Code Jan26": ["Opt In", "Opt In"],
    })
    try:
        reg_e_base(_ctx(ep))
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "debit" in str(exc).lower()
