"""Lock the contracts the competition axis helpers promise.

These four functions are the fix for the audit's "Wave 4" competition
chart bugs. The bugs are visual, but the contracts are arithmetic:
each helper guarantees a specific relationship between data extent and
returned limits, and those guarantees are what keep the charts honest
when a new client's data extends past the historical range.

Loaded via exec_module since the helper file sits in an
exec()-as-namespace directory rather than being importable.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_axes_module():
    """Load competition/00_axes.py as a module despite the leading digit."""
    path = (
        Path(__file__).resolve().parents[1]
        / "analytics" / "competition" / "00_axes.py"
    )
    spec = importlib.util.spec_from_file_location("comp_axes", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def axes():
    return _load_axes_module()


# ---------------------------------------------------------------------------
# fit_y_to_data -- the threat_quadrant fix (audit #2, main-deck)
# ---------------------------------------------------------------------------

def test_fit_y_to_data_uses_soft_cap_for_quiet_clients(axes):
    """A client whose max activity is well under 105 should still get the
    full historical 105 axis range -- otherwise the chart's quadrant
    geometry shifts unexpectedly between low-activity and high-activity
    clients."""
    lo, hi = axes.fit_y_to_data([10, 40, 60, 85], soft_cap=105)
    assert lo == 0
    assert hi == 105


def test_fit_y_to_data_scales_up_when_data_exceeds_cap(axes):
    """The bug: a competitor at index 140 used to clip off the top of the
    chart. Helper must scale to data + headroom in this case."""
    lo, hi = axes.fit_y_to_data([20, 60, 140], soft_cap=105, headroom=1.10)
    assert lo == 0
    # 140 * 1.10 = 154, exceeds the 105 floor
    assert hi == pytest.approx(154.0)


def test_fit_y_to_data_handles_empty_series(axes):
    lo, hi = axes.fit_y_to_data([], soft_cap=105)
    assert (lo, hi) == (0.0, 105)


# ---------------------------------------------------------------------------
# symmetric_diagonal_limits -- the spend_scatter fix (audit #26)
# ---------------------------------------------------------------------------

def test_symmetric_diagonal_uses_global_max(axes):
    """Both axes must share the same upper bound so the 50/50 diagonal
    visually represents equal spend."""
    lo, hi = axes.symmetric_diagonal_limits(
        xs=[10, 50, 200],
        ys=[5, 30, 80],
        pad=0.05,
    )
    assert lo == 0
    # max is 200, +5% pad
    assert hi == pytest.approx(210.0)


def test_symmetric_diagonal_handles_y_dominant(axes):
    """When the competitor (y) dominates spend, the axis still extends to
    the larger value -- not the x-axis range."""
    lo, hi = axes.symmetric_diagonal_limits(xs=[10, 20], ys=[100, 500])
    assert hi == pytest.approx(525.0)


# ---------------------------------------------------------------------------
# fit_xy_with_marker_pad -- the bubble_chart fix (audit #12)
# ---------------------------------------------------------------------------

def test_fit_xy_with_marker_pad_extends_beyond_data(axes):
    """The biggest bubbles need visible space beyond the data range so
    they don't clip on the chart edge. The helper must return limits
    that strictly contain the data extent."""
    (xlo, xhi), (ylo, yhi) = axes.fit_xy_with_marker_pad(
        xs=[0, 50, 100],
        ys=[0, 25, 50],
        max_marker_size=2500,
    )
    assert xlo < 0
    assert xhi > 100
    assert ylo < 0
    assert yhi > 50


def test_fit_xy_with_marker_pad_scales_with_marker_size(axes):
    """A chart with small markers shouldn't get the same headroom as one
    with huge markers."""
    (_, xhi_small), _ = axes.fit_xy_with_marker_pad(
        xs=[0, 100], ys=[0, 50], max_marker_size=200,
    )
    (_, xhi_big), _ = axes.fit_xy_with_marker_pad(
        xs=[0, 100], ys=[0, 50], max_marker_size=2500,
    )
    assert xhi_big > xhi_small


# ---------------------------------------------------------------------------
# clear_quadrant_label_zones -- the spend_vs_frequency fix (audit #28)
# ---------------------------------------------------------------------------

def test_clear_quadrant_label_zones_pads_all_four_corners(axes):
    """Quadrant labels at 0.03/0.97 in all corners need visible empty
    space, which means the returned limits must extend symmetrically
    past the data on both ends of both axes."""
    (xlo, xhi), (ylo, yhi) = axes.clear_quadrant_label_zones(
        xs=[10, 50, 100],
        ys=[100, 500, 1000],
        headroom=1.18,
    )
    # Both axes padded on both sides.
    assert xlo < 10 and xhi > 100
    assert ylo < 100 and yhi > 1000
    # Pad is symmetric.
    xrng = 100 - 10
    yrng = 1000 - 100
    assert (10 - xlo) == pytest.approx(xhi - 100)
    assert (100 - ylo) == pytest.approx(yhi - 1000)
    # And proportional to data range.
    assert (xhi - xlo) == pytest.approx(xrng * 1.18)
    assert (yhi - ylo) == pytest.approx(yrng * 1.18)


def test_clear_quadrant_label_zones_handles_degenerate_input(axes):
    """Empty input must not raise -- the wrapping script already gates on
    len(df) >= 5, but defense-in-depth keeps a single bad row from
    crashing the chart."""
    (xlo, xhi), (ylo, yhi) = axes.clear_quadrant_label_zones(xs=[], ys=[])
    # Returns a usable default rather than NaN.
    assert xlo == 0.0 and ylo == 0.0
    assert xhi == 1.0 and yhi == 1.0
