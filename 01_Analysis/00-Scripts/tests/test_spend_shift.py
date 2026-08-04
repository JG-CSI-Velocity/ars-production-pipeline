"""Responder Spend Shift (campaign 44-47): before/after mail-anchor analysis.

Pins the anchor logic (responders anchor on first successful response,
non-responders on first mail), full-window coverage exclusion, the cohort
PRE/POST aggregates, SIG-share math, vendor entered/exited detection, and
that the three chart cells render (or skip) cleanly.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

_CAMPAIGN = Path(__file__).resolve().parents[1] / "analytics" / "campaign"

_MONTH_ABBR = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
               'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}


def _period_sort_key(label):
    return (2000 + int(label[3:])) * 100 + _MONTH_ABBR[label[:3]]


def _is_success(val):
    if pd.isna(val):
        return False
    v = str(val).strip().upper()
    return v.startswith('TH') or v in ('NU 5+', 'NU5+')


def _txn_rows(acct, months, merchant, amount, ttype):
    return [
        {"primary_account_num": acct, "amount": amount,
         "transaction_type": ttype, "merchant_consolidated": merchant,
         "year_month": pd.Period(m, freq="M")}
        for m in months
    ]


def _fixture_ns() -> dict:
    # Data range Oct 2024 - Jul 2026-agnostic: use Oct24..Jul25.
    # A: Responder, responded Jan25 -> PRE=Oct-Dec24, POST=Feb-Apr25 (covered)
    # B: Non-Responder, mailed Jan25 -> same windows (covered)
    # C: Responder, responded Nov24 -> PRE needs Aug24 < range -> EXCLUDED
    camp_raw = pd.DataFrame({
        "Acct Number": ["A", "B", "C"],
        "Nov24 Mail": [None, None, "M"],
        "Nov24 Resp": [None, None, "TH-10"],
        "Jan25 Mail": ["M", "M", None],
        "Jan25 Resp": ["TH-15", None, None],
    })
    camp_acct = pd.DataFrame({
        "primary_account_num": ["A", "B", "C"],
        "camp_status": ["Responder", "Non-Responder", "Responder"],
    })

    txns = []
    # A before: WALMART, $100/mo PIN; after: TARGET, $200/mo SIG
    txns += _txn_rows("A", ["2024-10", "2024-11", "2024-12"], "WALMART", 100.0, "PIN")
    txns += _txn_rows("A", ["2025-02", "2025-03", "2025-04"], "TARGET", 200.0, "SIG")
    # A anchor-month txn must land in neither window
    txns += _txn_rows("A", ["2025-01"], "IGNORED ANCHOR MONTH", 999.0, "PIN")
    # B flat: AMAZON $50/mo PIN in both windows
    txns += _txn_rows("B", ["2024-10", "2024-11", "2024-12",
                            "2025-02", "2025-03", "2025-04"], "AMAZON", 50.0, "PIN")
    # C has transactions but is excluded by coverage
    txns += _txn_rows("C", ["2024-10", "2024-11"], "COSTCO", 75.0, "PIN")
    camp_txn = pd.DataFrame(txns)
    camp_txn["camp_status"] = camp_txn["primary_account_num"].map(
        dict(zip(camp_acct["primary_account_num"], camp_acct["camp_status"])))

    return {
        "pd": pd, "np": np,
        "camp_raw": camp_raw, "camp_acct": camp_acct, "camp_txn": camp_txn,
        "mail_cols": ["Nov24 Mail", "Jan25 Mail"],
        "resp_cols": ["Nov24 Resp", "Jan25 Resp"],
        "_is_success": _is_success, "_period_sort_key": _period_sort_key,
        "DATASET_START": pd.Timestamp("2024-10-01"),
        "DATASET_END": pd.Timestamp("2025-07-31"),
        "DATASET_LABEL": "Oct 2024-Jul 2025",
    }


def _run(script: str, ns: dict) -> dict:
    src = (_CAMPAIGN / script).read_text(encoding="utf-8")
    exec(compile(src, script, "exec"), ns)  # noqa: S102
    return ns


def test_anchors_windows_and_summary_numbers():
    ns = _run("44_spend_shift_data.py", _fixture_ns())

    assert ns["ss_excluded"] == {"no_full_window": 1}  # C
    anchored = ns["ss_anchor_df"]
    assert set(anchored["primary_account_num"]) == {"A", "B"}

    s = ns["ss_summary"].set_index(["camp_status", "window"])
    # A (Responder): $300 over 3 pre months -> $100/mo; $600 post -> $200/mo
    assert s.loc[("Responder", "PRE"), "avg_monthly_spend_per_acct"] == 100.0
    assert s.loc[("Responder", "POST"), "avg_monthly_spend_per_acct"] == 200.0
    # SIG share flips 0% -> 100% for A
    assert s.loc[("Responder", "PRE"), "sig_share_pct"] == 0.0
    assert s.loc[("Responder", "POST"), "sig_share_pct"] == 100.0
    # B (control) is flat at $50/mo, all PIN
    assert s.loc[("Non-Responder", "PRE"), "avg_monthly_spend_per_acct"] == 50.0
    assert s.loc[("Non-Responder", "POST"), "avg_monthly_spend_per_acct"] == 50.0
    assert s.loc[("Non-Responder", "POST"), "sig_share_pct"] == 0.0
    # The anchor-month transaction ($999) landed in neither window
    assert 999.0 not in ns["ss_win"]["amount"].values


def test_vendor_shift_flags_new_and_gone():
    ns = _run("44_spend_shift_data.py", _fixture_ns())
    shift = ns["ss_vendor_shift"]
    assert shift.loc["TARGET", "shift"] == "NEW"
    assert shift.loc["WALMART", "shift"] == "GONE"
    # Control account's merchant is not in the responder shift table
    assert "AMAZON" not in shift.index


def test_data_cell_skips_without_campaign_data(capsys):
    ns = {"pd": pd, "np": np, "camp_acct": pd.DataFrame()}
    _run("44_spend_shift_data.py", ns)
    assert len(ns["ss_summary"]) == 0
    assert "Skipping spend-shift" in capsys.readouterr().out


_CHART_STUBS = {
    "plt": plt, "np": np, "pd": pd, "mticker": mticker,
    "GEN_COLORS": {
        "info": "#1f77b4", "warning": "#ff7f0e", "success": "#2ca02c",
        "accent": "#d62728", "grid": "#cccccc", "dark_text": "#222222",
    },
    "gen_clean_axes": lambda ax: None,
    "DATASET_LABEL": "Oct 2024-Jul 2025",
}


def _chart_ns() -> dict:
    ns = _run("44_spend_shift_data.py", _fixture_ns())
    ns.update(_CHART_STUBS)
    return ns


def test_chart_cells_render_without_error():
    for script in ("45_spend_shift_spend_chart.py",
                   "46_spend_shift_vendors_chart.py",
                   "47_spend_shift_pin_sig_chart.py"):
        ns = _chart_ns()
        _run(script, ns)
        assert plt.get_fignums(), script
        plt.close("all")


def test_chart_cells_skip_cleanly_without_data(capsys):
    for script in ("45_spend_shift_spend_chart.py",
                   "46_spend_shift_vendors_chart.py",
                   "47_spend_shift_pin_sig_chart.py"):
        ns = dict(_CHART_STUBS)
        ns["ss_summary"] = pd.DataFrame()
        ns["ss_vendor_shift"] = pd.DataFrame()
        _run(script, ns)
        assert not plt.get_fignums(), script
    assert "Skipping" in capsys.readouterr().out
