# ===========================================================================
# AXIS-SCALING HELPERS for the competition section charts
# ===========================================================================
# Four charts in this section ship to the main deck with axis bugs that
# range from clipping client data (13_threat_quadrant) to visual
# collisions (28_spend_vs_frequency). Centralizing the rules here keeps
# every chart's margins and quadrant geometry consistent and gives the
# next maintainer one file to edit instead of four.
#
# Loaded first by txn_wrapper (numeric prefix 00) so every later chart
# script can call these helpers without an import (the txn_wrapper runs
# scripts in a shared namespace via exec()).
#
# Issues addressed:
#   13_threat_quadrant: y_max was hardcoded at 105; competitors above the
#     cap clipped off the top and the WATCH/DEFEND/ACT NOW bands landed
#     in the wrong place.
#   12_bubble_chart: ax.margins(0.08) was not enough for the largest
#     bubble; fit_xy_with_marker_pad reserves visible space for the
#     biggest scatter marker.
#   26_spend_scatter: the 50/50 diagonal stretched the auto-scaled axes
#     past the data; symmetric_diagonal_limits returns limits matched to
#     the actual data extent.
#   28_spend_vs_frequency: two top-anchored quadrant labels collided when
#     the title ran wide; clear_quadrant_label_zones restricts axis range
#     so the labels sit clear of the data and each other.


def fit_y_to_data(series, soft_cap=105, headroom=1.10):
    """Return (y_min, y_max) that always contain every value in `series`.

    soft_cap is the value the chart was historically anchored to (e.g.
    105 for activity indices). It is honored as a floor on y_max so a
    quiet client with a max index of 60 does not suddenly render with a
    cramped vertical axis -- but a noisy client whose max is 140 gets
    140*headroom instead of being clipped at 105.
    """
    try:
        data_max = float(max(series))
    except (TypeError, ValueError):
        data_max = 0.0
    return 0.0, max(soft_cap, data_max * headroom)


def symmetric_diagonal_limits(xs, ys, pad=0.05):
    """For diagonal-comparison scatters (your_spend vs competitor_spend),
    return the shared (lo, hi) so axes and the 50/50 line agree.

    Without this, axis auto-scaling expands to the diagonal's endpoints
    even when the data sits in one corner -- creating an ugly box of
    empty whitespace beside a single dense cluster.
    """
    try:
        hi = float(max(max(xs), max(ys)))
    except (TypeError, ValueError):
        hi = 1.0
    return 0.0, hi * (1 + pad)


def fit_xy_with_marker_pad(xs, ys, max_marker_size=2500, pad_frac=0.06):
    """Return ((xmin, xmax), (ymin, ymax)) with enough room for the
    largest marker -- ax.margins() alone misses this when scatter sizes
    vary widely. Pad scales with marker size so a chart with s=200 needs
    less headroom than one with s=2500.
    """
    try:
        xmin, xmax = float(min(xs)), float(max(xs))
        ymin, ymax = float(min(ys)), float(max(ys))
    except (TypeError, ValueError):
        return (0.0, 1.0), (0.0, 1.0)
    extra = pad_frac * (max_marker_size / 2500.0)
    xrng = max(xmax - xmin, 1.0)
    yrng = max(ymax - ymin, 1.0)
    return (
        (xmin - xrng * extra, xmax + xrng * extra),
        (ymin - yrng * extra, ymax + yrng * extra),
    )


def clear_quadrant_label_zones(xs, ys, headroom=1.18):
    """When a chart has quadrant labels in all four corners (positioned
    via transAxes at 0.03/0.97), the labels overlap the densest cluster
    unless the axes have visible empty space in each corner. Returns
    ((xmin, xmax), (ymin, ymax)) with proportional padding so the labels
    sit on clean background.
    """
    try:
        xmin, xmax = float(min(xs)), float(max(xs))
        ymin, ymax = float(min(ys)), float(max(ys))
    except (TypeError, ValueError):
        return (0.0, 1.0), (0.0, 1.0)
    xrng = max(xmax - xmin, 1.0)
    yrng = max(ymax - ymin, 1.0)
    pad = (headroom - 1.0) / 2.0
    return (
        (xmin - xrng * pad, xmax + xrng * pad),
        (ymin - yrng * pad, ymax + yrng * pad),
    )


print("Competition axis helpers loaded.")
