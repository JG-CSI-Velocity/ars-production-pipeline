"""Extract the numeric payload from a live matplotlib figure.

Parity is judged on DATA, never pixels. Most legacy TXN scripts emit only a
PNG (run_report ``has_excel: false``), so their numbers exist solely inside
the matplotlib figure at save time. This module pulls those numbers out:
line xy-data, bar geometry, pie wedge angles, scatter offsets, heatmap
arrays, and rendered text -- enough to detect any numeric drift in a port.

Called from the legacy ``ChartCapture`` save path when ARS_PARITY_CAPTURE=1
(additive, env-gated patch), and usable directly by the v3 chart renderer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _num(v: Any) -> Any:
    """Convert numpy scalars / datetimes to JSON-safe python values."""
    import numpy as np

    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        f = float(v)
        return None if f != f else f  # NaN -> None
    if isinstance(v, float):
        return None if v != v else v
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, np.datetime64):
        return str(v)
    return v


def _seq(values: Any) -> list:
    return [_num(v) for v in list(values)]


def extract_figure_data(fig: Any) -> dict[str, Any]:
    """Return a JSON-serializable dict of every plotted number in the figure."""
    out: dict[str, Any] = {"axes": []}
    for ax in fig.get_axes():
        ax_data: dict[str, Any] = {
            "title": ax.get_title(),
            "xlabel": ax.get_xlabel(),
            "ylabel": ax.get_ylabel(),
            "lines": [],
            "bars": [],
            "wedges": [],
            "collections": [],
            "texts": [],
            "xticklabels": [t.get_text() for t in ax.get_xticklabels()],
            "yticklabels": [t.get_text() for t in ax.get_yticklabels()],
        }

        for line in ax.get_lines():
            ax_data["lines"].append(
                {
                    "label": str(line.get_label()),
                    "x": _seq(line.get_xdata()),
                    "y": _seq(line.get_ydata()),
                }
            )

        from matplotlib.patches import Rectangle, Wedge

        for patch in ax.patches:
            if isinstance(patch, Wedge):
                ax_data["wedges"].append(
                    {
                        "theta1": _num(patch.theta1),
                        "theta2": _num(patch.theta2),
                        "r": _num(patch.r),
                    }
                )
            elif isinstance(patch, Rectangle):
                ax_data["bars"].append(
                    {
                        "x": _num(patch.get_x()),
                        "y": _num(patch.get_y()),
                        "w": _num(patch.get_width()),
                        "h": _num(patch.get_height()),
                    }
                )

        for coll in ax.collections:
            entry: dict[str, Any] = {"type": type(coll).__name__}
            try:
                offsets = coll.get_offsets()
                if offsets is not None and len(offsets):
                    entry["offsets"] = [_seq(pair) for pair in offsets]
            except (AttributeError, TypeError, ValueError):
                pass
            try:
                arr = coll.get_array()
                if arr is not None and getattr(arr, "size", 0):
                    entry["array"] = _seq(arr.ravel())
            except (AttributeError, TypeError, ValueError):
                pass
            ax_data["collections"].append(entry)

        # Annotations / value labels rendered onto the axes
        ax_data["texts"] = [t.get_text() for t in ax.texts if t.get_text()]

        out["axes"].append(ax_data)

    # Figure-level text (suptitle etc.)
    out["texts"] = [t.get_text() for t in fig.texts if t.get_text()]
    return out


def dump_figure_data(fig: Any, png_path: Path | str) -> Path | None:
    """Write ``<chart>.figdata.json`` next to the chart PNG. Never raises --
    parity capture must not be able to break a production run."""
    try:
        png_path = Path(png_path)
        data = extract_figure_data(fig)
        out = png_path.with_suffix(".figdata.json")
        out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return out
    except Exception:  # noqa: BLE001 - deliberate: capture is best-effort
        return None
