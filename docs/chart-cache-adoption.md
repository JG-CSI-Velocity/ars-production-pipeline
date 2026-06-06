# Chart-PNG cache adoption guide

The cache helper lives at `01_Analysis/00-Scripts/charts/cache.py`. This doc explains how to wire an existing chart call site through it.

## Why opt-in

`save_chart_png` is too late — by the time you call it, the figure is already rendered. The cache needs to sit *around* the render so it can skip the matplotlib work entirely on a hit. Every chart's input data is different (DataFrame slice, computed series, scalar overlays), so there's no one-size-fits-all wrapper. Each chart site declares its own fingerprint inputs.

## Three-step pattern

### Before (today's pattern)

```python
charts_dir = ctx.paths.charts_dir
charts_dir.mkdir(parents=True, exist_ok=True)
save_to = charts_dir / "my_chart.png"

with chart_figure(save_path=save_to) as (fig, ax):
    ax.bar(df["category"], df["value"])
    ax.set_title("My Chart")
```

### After (cache-aware)

```python
from charts.cache import cached_chart, fingerprint_df

charts_dir = ctx.paths.charts_dir
charts_dir.mkdir(parents=True, exist_ok=True)
save_to = charts_dir / "my_chart.png"

# 1. Fingerprint everything that affects the visual.
#    Include: DataFrame columns the chart reads, scalar inputs, style version,
#    palette name, anything that distinguishes one client's chart from another's.
key = fingerprint_df(
    df,
    columns=["category", "value"],
    extras={
        "client": ctx.client.client_id,
        "month": ctx.client.month,
        "style": "ars.mplstyle:v3",
        "overall_dctr": ctx.results.get("dctr_1", {}).get("insights", {}).get("overall_dctr"),
    },
)

# 2. Move the chart drawing into a function that takes the save path.
def _draw(path):
    with chart_figure(save_path=path) as (fig, ax):
        ax.bar(df["category"], df["value"])
        ax.set_title("My Chart")

# 3. Call cached_chart instead of drawing directly.
cached_chart(save_to, key, _draw)
```

That's it. Cache hit -> `_draw` is skipped. Cache miss -> `_draw` runs and the new key is stamped to `my_chart.png.cachekey`.

## What goes in extras

Anything that could change a chart's visual without changing the DataFrame:

- **`client`**: prevents one client's cached chart from being served to another client when the same DataFrame slice happens to fingerprint identically (rare but real)
- **`month`**: ensures L12M windows refresh
- **`style`**: bump the version string whenever `ars.mplstyle` or `shared/brand.py` changes
- **Computed scalars overlaid on the chart**: e.g. `overall_dctr` if it's drawn as a reference line. If you don't include it, changing the upstream insight won't invalidate the cache.
- **Anything pulled from `ctx.client`**: branch mapping version, eligible stat codes, etc., if the chart filters by them.

## What NOT to fingerprint

- The full DataFrame if you're plotting a subset. Pick the columns the chart actually reads — `fingerprint_df` does a column-wise hash, not a whole-DataFrame hash. Hashing 300MB of data defeats the purpose.
- Random seeds, UUIDs, timestamps. These would defeat the cache on every run.
- File system paths. The `save_path` is implicit in the cache key location; extras shouldn't restate it.

## When to skip the cache

Some chart sites mutate `ctx.results` or write Excel data inside the draw block. **Move that code outside the cached function** so it runs on every call. The cache should only skip the render, not the data export.

```python
# Wrong: Excel write skipped on cache hit
def _draw(path):
    ctx.results["my_key"] = computed_value          # <-- side effect
    with chart_figure(save_path=path) as (fig, ax): # <-- only this should be cached
        ...

# Right: side effect runs on every call
ctx.results["my_key"] = computed_value
def _draw(path):
    with chart_figure(save_path=path) as (fig, ax):
        ...
cached_chart(save_to, key, _draw)
```

## Disabling the cache

For ad-hoc debugging (e.g. "did my brand change actually re-render the navy?"), either:

- `set ARS_CHART_CACHE=0` in the env before launching, OR
- Delete the `.cachekey` sidecars in the run dir: `del 01_Analysis\01_Completed_Analysis\<CSM>\<period>\<client>\charts\*.cachekey`, OR
- Call `from charts.cache import purge_cache; purge_cache(ctx.paths.charts_dir)` once at the top of a run

## Expected adoption order

Highest impact (run frequency × render time) first:

1. **DCTR module** (`dctr/penetration.py`, `dctr/trends.py`, `dctr/branches.py`, `dctr/overlays.py`) — ~10 charts, runs on every client
2. **Reg E module** (`rege/status.py`) — ~4 charts
3. **Mailer module** (`mailer/response.py`, `mailer/impact.py`, `mailer/reach.py`) — ~15-25 charts depending on campaign count
4. **Insights module** (`insights/synthesis.py`, `insights/conclusions.py`) — ~8 charts
5. **Competition / TXN sections** — last; many charts but they use Plotly, not matplotlib, and `chart_figure` doesn't cover them yet. Separate adapter needed.

Each module's adoption is a small commit. Run the test suite plus one real client both before and after.
