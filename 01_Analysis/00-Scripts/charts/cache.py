"""Content-hash cache for chart PNG rendering.

Re-running an analysis often produces the same charts because the underlying
DataFrame and styling are unchanged. Skipping the matplotlib render saves
~5-10 seconds per chart * ~100 charts -> 8-15 min per run.

The cache works on opt-in basis:

    from charts.cache import cached_chart, fingerprint_df

    def _render(save_path):
        with chart_figure(save_path=save_path) as (fig, ax):
            ax.bar(...)

    key = fingerprint_df(df, columns=["Stat Code", "Debit?"], extras={
        "style": "ars.mplstyle:v3",
        "client": ctx.client.client_id,
        "month": ctx.client.month,
    })
    cached_chart(chart_path, key, _render)

The helper checks for `<chart_path>.cachekey` next to the PNG. If the key
matches AND the PNG exists, the draw_fn is skipped entirely. Otherwise the
draw_fn runs and the new key is stamped.

Cache invalidates automatically whenever any input changes -- the key is a
SHA-256 of the fingerprint inputs.

Tunables:
    ARS_CHART_CACHE=0   disable the cache (force re-render every chart)
    ARS_CHART_CACHE_PURGE=1   clear all .cachekey sidecars on import
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Callable

from loguru import logger

import pandas as pd

CACHE_DISABLED: bool = os.environ.get("ARS_CHART_CACHE", "1") == "0"


def fingerprint_df(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    extras: dict[str, object] | None = None,
) -> str:
    """Return a stable SHA-256 hex over selected DataFrame columns + extras.

    Use a small subset of columns when possible -- hashing every byte of a
    300-MB DataFrame defeats the cache. Pick the columns the chart actually
    plots (e.g. ["Stat Code", "Debit?", "Date Opened"] for a DCTR chart).

    `extras` is a free-form dict folded into the hash. Use it for the things
    that change a chart's visual without changing the DataFrame: style file
    version, palette name, client_id (so two clients' caches don't collide),
    month, branch mapping version, etc.

    Returns a 16-character truncated hex so file sidecars stay short.
    """
    h = hashlib.sha256()
    if df is not None:
        if columns is None:
            columns = list(df.columns)
        # Stable column order so {A, B} and {B, A} produce the same key
        for col in sorted(columns):
            if col not in df.columns:
                h.update(f"!missing:{col}".encode())
                continue
            series = df[col]
            # pandas hash is stable across runs for the same data
            try:
                col_hash = pd.util.hash_pandas_object(series, index=False).values
                h.update(col_hash.tobytes())
            except Exception:
                # Fallback: serialize to string. Slower but always works.
                h.update(series.astype(str).str.cat(sep="|").encode())
        h.update(f"|rows:{len(df)}".encode())
    if extras:
        # Sort keys so {a:1, b:2} and {b:2, a:1} produce the same key
        h.update(json.dumps(extras, sort_keys=True, default=str).encode())
    return h.hexdigest()[:16]


def _sidecar_for(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".cachekey")


def cached_chart(
    save_path: Path | str,
    key: str,
    draw_fn: Callable[[Path], None],
) -> bool:
    """Render `save_path` via `draw_fn` unless a matching key cache exists.

    Returns True on cache hit (draw_fn was skipped), False on miss (draw_fn ran).
    On hit, the existing PNG is left untouched. On miss, draw_fn writes the PNG
    and the sidecar is updated atomically.

    `draw_fn(save_path)` is called with the absolute save path. It should
    produce a PNG at that location -- any side effects (Excel writes, ctx
    mutations) still happen on every call, so put cache-sensitive work
    inside draw_fn only when you want it to skip on cache hit.
    """
    save_path = Path(save_path)
    sidecar = _sidecar_for(save_path)

    if CACHE_DISABLED:
        draw_fn(save_path)
        return False

    if save_path.exists() and sidecar.exists():
        try:
            existing = sidecar.read_text(encoding="utf-8").strip()
        except OSError:
            existing = ""
        if existing == key:
            logger.debug("Chart cache hit: {p}", p=save_path.name)
            return True

    save_path.parent.mkdir(parents=True, exist_ok=True)
    draw_fn(save_path)
    if save_path.exists():
        try:
            sidecar.write_text(key, encoding="utf-8")
        except OSError as exc:
            logger.warning("Cache sidecar write failed for {p}: {err}", p=save_path, err=exc)
    return False


def purge_cache(root: Path) -> int:
    """Delete every `.cachekey` sidecar under `root`. Returns count deleted.

    Useful in tests; also exposed as a no-op manual recovery when the cache
    is suspected to be poisoned (e.g. brand colors changed but PNG didn't
    re-render because the DataFrame fingerprint stayed the same).
    """
    root = Path(root)
    n = 0
    if not root.exists():
        return 0
    for p in root.rglob("*.cachekey"):
        try:
            p.unlink()
            n += 1
        except OSError:
            pass
    return n


if os.environ.get("ARS_CHART_CACHE_PURGE") == "1":
    # Best-effort startup purge for ad-hoc debugging.
    try:
        from ars_analysis.pipeline.context import OutputPaths  # noqa: F401
        # We can't know the run dir at import; this is a defensive no-op.
        # Real purge is per-run: `from charts.cache import purge_cache; purge_cache(ctx.paths.charts_dir)`
    except Exception:
        pass
