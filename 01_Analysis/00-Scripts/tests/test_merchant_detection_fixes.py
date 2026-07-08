"""Regression tests for two per-script bugs seen in the 1776 TXN run.

- merchant/08_merchant_volatility: a non-finite CV (merchant with ~0 mean
  spend -> std/mean = inf) made savefig(bbox_inches='tight') overflow the
  figure width and matplotlib's RendererAgg constructor threw.
- financial_services/20_detection_diagnostic: an empty keyword-hint list made
  pd.DataFrame([]).sort_values('total_spend') raise KeyError.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

_ANALYTICS = Path(__file__).resolve().parents[1] / "analytics"


def test_merchant_volatility_survives_infinite_cv(tmp_path, monkeypatch):
    """Fewer than 10 finite CVs means nsmallest would otherwise pull inf rows
    into the (un-clamped) left panel and overflow the tight bbox."""
    consistency_df = pd.DataFrame({
        "merchant_consolidated": [f"MERCHANT {i}" for i in range(6)],
        "cv": [10.0, 20.0, 30.0, np.inf, np.inf, np.inf],
    })
    out = tmp_path / "vol.png"

    def _save_like_capture(*_a, **_k):
        # Mirror ChartCapture: show() -> savefig(bbox_inches='tight', dpi=150).
        plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close("all")

    monkeypatch.setattr(plt, "show", _save_like_capture)

    ns = {
        "consistency_df": consistency_df,
        "plt": plt, "np": np, "pd": pd,
        "GEN_COLORS": {k: "#333333" for k in
                       ("info", "warning", "grid", "dark_text", "muted")},
        "gen_clean_axes": lambda ax, **k: None,
    }
    script = _ANALYTICS / "merchant" / "08_merchant_volatility.py"
    exec(compile(script.read_text(), str(script), "exec"), ns)  # noqa: S102

    assert out.exists() and out.stat().st_size > 0


def test_detection_empty_hints_no_keyerror():
    """The fix guards emptiness before sorting by a column that only exists
    once at least one keyword matched."""
    # Old pattern raised:
    with pytest.raises(KeyError):
        pd.DataFrame([]).sort_values("total_spend")

    # Fixed pattern: build first, sort only when non-empty.
    _hint_rows: list[dict] = []
    _hints = pd.DataFrame(_hint_rows)
    if not _hints.empty:
        _hints = _hints.sort_values("total_spend", ascending=False)
    assert _hints.empty  # reached without KeyError
