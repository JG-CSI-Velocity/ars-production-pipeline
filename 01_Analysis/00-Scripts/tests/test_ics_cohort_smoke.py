"""Smoke test for the ICS_cohort section cells.

Executes every NN_*.py cell in analytics/ICS_cohort/ against deterministic
synthetic ODD data, mirroring the TXN wrapper's shared-namespace execution
model (cells build on each other like notebook cells). Confirms:

  1. Every cell runs green on a healthy ODD.
  2. The owner gate (ics-00-config) sets SKIP_SECTION when Source is absent
     and the rest of the section is skipped cleanly.
  3. The stat-code filter is driven by the injected ELIGIBLE_STATUS_CODES
     (config-driven, not hardcoded to 'O').

The harness stubs the Jupyter `display`/`display_formatted` shims and the
optional `seaborn` dependency (not installed in this environment), and
provides the theme + import namespace the wrapper would normally inject.
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: no display backend in CI / this env

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Neutralize plt.show so cells that call it don't try to open a window.
plt.show = lambda *a, **k: None

# Cells dir: tests/ lives under 00-Scripts/, analytics/ is its sibling.
CELLS_DIR = Path(__file__).resolve().parents[1] / "analytics" / "ICS_cohort"

# Real hex theme palette. Cells reference dark_text/info/muted/success; the
# rest are included so any future key access resolves to a real color.
GEN_COLORS = {
    "dark_text": "#1A202C",
    "info": "#2B6CB0",
    "muted": "#718096",
    "success": "#2F855A",
    "grid": "#E2E8F0",
    "accent": "#805AD5",
    "warning": "#C05621",
    "danger": "#C53030",
    "primary": "#2C5282",
    "secondary": "#4A5568",
    "neutral": "#A0AEC0",
}


# ---------------------------------------------------------------------------
# seaborn stub
# ---------------------------------------------------------------------------
# seaborn is NOT installed in this environment. Only cell 30 uses it
# (sns.heatmap), and it ignores the return value. A permissive shim whose
# attribute access yields a callable no-op covers any sns.* method without
# breaking when the result is discarded.
class _SeabornStub:
    """Permissive no-op stand-in for seaborn. sns.anything(...) -> None."""

    def __getattr__(self, _name):
        def _noop(*_a, **_k):
            return None

        return _noop


_SNS_STUB = _SeabornStub()


# ---------------------------------------------------------------------------
# Synthetic ODD builder
# ---------------------------------------------------------------------------
# Fixed pools so the data is fully deterministic (no today()-based dates,
# no unseeded randomness).
_OPEN_DATE_POOL = [
    pd.Timestamp("2020-03-15"),
    pd.Timestamp("2021-06-01"),
    pd.Timestamp("2022-01-20"),
    pd.Timestamp("2023-09-10"),
    pd.Timestamp("2024-02-05"),
    pd.Timestamp("2024-11-18"),
    pd.Timestamp("2025-04-22"),
    pd.Timestamp("2025-08-30"),
    pd.Timestamp("2025-12-12"),
    pd.Timestamp("2026-01-07"),
]
# Closed-date offsets (days) added to the open date for the closed subset.
_CLOSED_OFFSET_DAYS = [120, 300, 540, 800, 1100]


def _make_synth_odd(eligible_codes, drop_source=False, n_rows=400):
    """Build a deterministic ~400-row synthetic ODD DataFrame.

    Stat Codes always include every code in `eligible_codes` (plus closed
    codes like 'C') in healthy proportion, so the eligible cohort is
    non-trivial. Monthly swipe/spend columns end at Mar26.
    """
    rng = np.random.default_rng(42)
    elig = [str(c).strip().upper() for c in eligible_codes]

    # Stat Code pool: weight eligible codes heavily so cohorts are healthy,
    # mixed with closed/other codes.
    closed_codes = ["C", "X", "Z"]
    stat_pool = elig * 4 + closed_codes
    stat_codes = rng.choice(stat_pool, size=n_rows)

    # ICS Account mix across the Yes/No/Y/N variants the normalizer collapses.
    ics_pool = ["Yes", "No", "Y", "N"]
    ics = rng.choice(ics_pool, size=n_rows, p=[0.45, 0.35, 0.10, 0.10])

    # Open dates from the fixed pool; closed subset gets a later closed date.
    open_idx = rng.integers(0, len(_OPEN_DATE_POOL), size=n_rows)
    date_opened = [_OPEN_DATE_POOL[i] for i in open_idx]

    closed_mask = rng.random(n_rows) < 0.30  # ~30% closed
    date_closed = []
    for i in range(n_rows):
        if closed_mask[i]:
            off = _CLOSED_OFFSET_DAYS[i % len(_CLOSED_OFFSET_DAYS)]
            date_closed.append(date_opened[i] + pd.Timedelta(days=off))
        else:
            date_closed.append(pd.NaT)

    frame = {
        "Acct Number": [f"ACC{1000 + i}" for i in range(n_rows)],
        "ICS Account": ics,
        "Stat Code": stat_codes,
        "Date Opened": date_opened,
        "Date Closed": date_closed,
        "Avg Bal": rng.uniform(0, 50_000, size=n_rows).round(2),
        "Curr Bal": rng.uniform(0, 75_000, size=n_rows).round(2),
        "Business?": rng.choice(["Yes", "No"], size=n_rows, p=[0.25, 0.75]),
        "Debit?": rng.choice(["Yes", "No"], size=n_rows, p=[0.60, 0.40]),
        "Product Code": rng.choice(["DDA", "SAV", "MMA"], size=n_rows),  # prod ODD name (loader renames Prod Code -> Product Code)
        "Branch": rng.choice(["001", "002", "003"], size=n_rows),
    }

    if not drop_source:
        frame["Source"] = rng.choice(["REF", "DM", ""], size=n_rows, p=[0.45, 0.45, 0.10])

    # 12 monthly swipe/spend pairs ending Mar26 -> 24 monthly columns.
    for p in pd.period_range(end="2026-03", periods=12, freq="M"):
        tag = p.strftime("%b%y")
        frame[f"{tag} Swipes"] = rng.integers(0, 40, size=n_rows)
        frame[f"{tag} Spend"] = rng.uniform(0, 2_000, size=n_rows).round(2)

    return pd.DataFrame(frame)


# ---------------------------------------------------------------------------
# Section runner
# ---------------------------------------------------------------------------
def _display(*_a, **_k):
    """Jupyter display() shim -- no-op in script context."""
    return None


def _display_formatted(*_a, **_k):
    """display_formatted() shim used by several cells -- no-op."""
    return None


def _build_namespace(odd_df, eligible_codes):
    """Mirror the TXN wrapper's _build_namespace plus theme vars."""
    from collections import OrderedDict
    import matplotlib.dates as mdates
    import matplotlib.patheffects as pe
    import matplotlib.ticker as mticker
    from matplotlib.gridspec import GridSpec
    from matplotlib.patches import FancyBboxPatch
    import re as _re
    import json as _json
    import gc as _gc
    import time as _time

    warnings.filterwarnings("ignore")

    return {
        # Common imports available to all cells
        "pd": pd,
        "np": np,
        "plt": plt,
        "sns": _SNS_STUB,
        "GridSpec": GridSpec,
        "FancyBboxPatch": FancyBboxPatch,
        "OrderedDict": OrderedDict,
        "mdates": mdates,
        "pe": pe,
        "mticker": mticker,
        "re": _re,
        "json": _json,
        "gc": _gc,
        "time": _time,
        "Path": Path,
        "os": os,
        "sys": sys,
        "warnings": warnings,
        # Jupyter compatibility shims
        "display": _display,
        "display_formatted": _display_formatted,
        # Theme vars normally injected by the general section
        "GEN_COLORS": dict(GEN_COLORS),
        "GEN_TITLE_Y": 1.02,
        # Pipeline context values
        "odd_df": odd_df,
        "ELIGIBLE_STATUS_CODES": list(eligible_codes),
        "CLIENT_ID": "TEST",
        "CLIENT_NAME": "Test",
        "MONTH": "2026-03",
        "CSM": "test",
        "clients_config": {},
        # Builtins
        "__builtins__": __builtins__,
    }


def _run_section(odd_df, eligible_codes, tmp_cwd=None):
    """Exec every NN_*.py cell in CELLS_DIR in sorted order, sharing one
    namespace. Honors SKIP_SECTION (once set, all remaining cells skip),
    mirroring the TXN wrapper. Returns (namespace, failures)."""
    namespace = _build_namespace(odd_df, eligible_codes)
    failures = []

    cells = sorted(CELLS_DIR.glob("*.py"))
    # Cells savefig() to relative paths; run from a scratch dir so the repo
    # isn't polluted with PNGs.
    prev_cwd = os.getcwd()
    if tmp_cwd is not None:
        os.chdir(tmp_cwd)
    try:
        for path in cells:
            if namespace.get("SKIP_SECTION"):
                # Owner gate tripped -- skip ALL remaining cells (wrapper parity).
                continue
            try:
                namespace["__file__"] = str(path)
                src = path.read_text(encoding="utf-8")
                exec(compile(src, str(path), "exec"), namespace)
            except Exception as exc:  # noqa: BLE001 -- collect, don't abort
                failures.append((path.name, repr(exc)))
            finally:
                plt.close("all")
    finally:
        os.chdir(prev_cwd)

    return namespace, failures


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_all_cells_run_green(tmp_path):
    odd = _make_synth_odd(["O"])
    namespace, failures = _run_section(odd, ["O"], tmp_cwd=tmp_path)
    assert failures == [], "ICS_cohort cells failed:\n" + "\n".join(
        f"  {name}: {err}" for name, err in failures
    )
    # Healthy ODD must NOT trip the owner gate.
    assert namespace.get("SKIP_SECTION") is not True


def test_gate_skips_without_source(tmp_path):
    odd = _make_synth_odd(["O"], drop_source=True)
    namespace, failures = _run_section(odd, ["O"], tmp_cwd=tmp_path)
    assert namespace.get("SKIP_SECTION") is True
    assert failures == [], "Gate path should skip cleanly, not error:\n" + "\n".join(
        f"  {name}: {err}" for name, err in failures
    )


def test_stat_codes_from_config(tmp_path):
    # Eligible code 'A' (not 'O') -- proves the filter is config-driven.
    odd = _make_synth_odd(["A"])
    namespace, failures = _run_section(odd, ["A"], tmp_cwd=tmp_path)
    assert namespace.get("SKIP_SECTION") is not True
    assert failures == [], "ICS_cohort cells failed:\n" + "\n".join(
        f"  {name}: {err}" for name, err in failures
    )
    matched = int(namespace["is_target_status"](odd["Stat Code"]).sum())
    assert matched > 0, "Expected rows matching eligible code 'A'"
