---
module: Mailer Analysis
date: 2026-06-15
problem_type: performance_issue
component: service_object
symptoms:
  - "Deck shrank from ~165 to ~95 slides but total runtime rose ~50% (>45 min)"
  - "Run progress sat on 'Mailer effectiveness' for tens of minutes"
  - "First combo ('5 panel rendering') not reached until ~39 minutes into the run"
root_cause: scope_issue
resolution_type: code_fix
severity: high
tags: [mailer, rendering, decoupled-output, chart-cache, combo-cap, runtime, ars]
---

# Troubleshooting: Fewer deck slides but longer runtime (mailer renders work the deck throws away)

## Problem
Deck-quality work cut the ARS deck from ~165 slides to ~39-95, yet the end-to-end
run got *slower* (>45 min, ~50% worse). The operator correctly flagged the paradox:
"less slides but it's taking longer."

## Environment
- Module: Mailer Analysis (`01_Analysis/00-Scripts/analytics/mailer/`)
- Project: RPE-Workflow ARS pipeline (Python / pandas / matplotlib)
- Branch: `fix/deck-quality-1759`
- Date: 2026-06-15

## Symptoms
- Deck slide count dropped sharply, total runtime increased.
- The technical-log progress dwelled on "Mailer effectiveness" (module `mailer.cohort`) for ~17 min.
- A run was ~39 minutes in before the *first* combo chart began rendering.

## What Didn't Work

**Attempted Solution 1:** Cap the combo render to the 6 deck waves.
- **Why it was insufficient:** It helped the combo tail, but the operator's log showed
  ~39 minutes elapsed *before combos even started* — so the bulk of the time was upstream
  of the combos, not in them.

**Assumption that failed:** "Fewer slides in the deck must mean less work." False — the
deck slide count and the chart-render cost are decoupled (see Why This Works).

## Solution

**Step 1 — instrument, don't guess.** Added per-module duration logging to
`pipeline/steps/analyze.py` so the run log names the bottleneck:

```python
# pipeline/steps/analyze.py
_t0 = time.monotonic()
results = mod.run(ctx)
dt = time.monotonic() - _t0
timings.append((mid, dt))
logger.info("Module {id} produced {n} result(s) in {secs:.1f}s", id=mid, n=len(results), secs=dt)
# ...end of run:
logger.info("Analysis timing: {tot:.0f}s total | slowest: {slow}", tot=total_s,
            slow=", ".join(f"{m} {s:.0f}s" for m, s in top))
```

The log diff was conclusive: of a 32.8-min analysis, **mailer was 28.5 min (86%)** —
`mailer.cohort` 17.6 min, `mailer.response` 7.3 min, `mailer.insights` 3.3 min — while
all 16 non-mailer modules together were ~4 min.

**Step 2 — render only what the deck keeps.**

```python
# analytics/mailer/cohort.py -- cap combos to the deck window + the oldest (revisit)
_cap = int(os.environ.get("ARS_COMBO_MONTHS", "6") or 0)
if _cap and len(dated_pairs) > _cap:
    _kept = dated_pairs[:_cap]
    if dated_pairs[-1] not in _kept:        # oldest wave -> revisit slide
        _kept = _kept + [dated_pairs[-1]]
    dated_pairs = _kept

# Gate slides the deck DROPS so they stop rendering (A16.1-6 trajectories,
# A14.2 account-age, A15.{month} ladder):
_render_dropped = os.environ.get("ARS_RENDER_DROPPED_MAILER") == "1"
if _render_dropped and spend_cols:
    ...  # only render the dropped charts on explicit opt-in
```

**Step 3 — persistent cross-run cache** for the per-wave charts that don't change once a
wave is in the past (`charts/cache.py` helpers `persistent_chart_dir` /
`chart_is_cached` / `write_chart_key`). Key each wave by ONLY the columns it plots:

```python
# Key by the wave's own -6..+12 offset-window columns, NOT all metric columns,
# so adding next month's column doesn't invalidate every past wave's cache.
_wave_cols = [mail_col, resp_col]
for _o in range(-6, 13):
    _tgt = (mail_date + pd.DateOffset(months=_o)).strftime("%b%y")
    if _tgt in spend_lookup: _wave_cols.append(spend_lookup[_tgt])
    if _tgt in swipe_lookup: _wave_cols.append(swipe_lookup[_tgt])
_cache_key = fingerprint_df(data, columns=_wave_cols, extras={"client": cid, "month": month, "v": "combo-v1"})
if chart_is_cached(cache_path, _cache_key):
    shutil.copyfile(cache_path, run_path)   # copy instead of render
    continue
```

Net: mailer ~28.5 min → ~10-11 min; subsequent monthly runs copy unchanged past waves.

## Why This Works

The **root cause is a scope mismatch between rendering and output selection.** Charts are
rendered during the *analysis* step; the *deck-build* step runs afterward and decides which
slides to keep, consolidate (2x1 merges), appendix, or window (most-recent-6). The mailer
module rendered per-wave charts for **all ~22 waves** — combos, ladders, trajectories,
account-age — and the deck then discarded most of them. So shrinking the deck never reduced
the render work: the expensive matplotlib renders had already run.

The fix realigns the two: render only the waves/slide-types the deck actually keeps, and
cache the immutable past waves so they're never re-rendered.

## Prevention

- **When you drop a slide from the deck, also gate its RENDER.** A `SLIDE_LAYOUT_MAP` /
  consolidation drop removes it from the deck but the analysis still pays to render it.
- **Keep per-module timing in the log** (`Analysis timing: ... | slowest: ...`) so the next
  regression is a one-line read, not a timestamp-diff exercise.
- **Diagnose with the timing line before optimizing** — the first instinct (combos) was only
  62% of the mailer cost; the data redirected the fix.
- **Cache by the minimal inputs a chart depends on**, not the whole dataset, or new data
  invalidates everything and the cache never hits.

## Related Issues
- Memory: `project_deck_quality_fixes.md` (this repo's deck-quality fix log; "Runtime
  regression" + "persistent chart cache" entries).
- Escape hatches: `ARS_SKIP_COMBO=1` / `SKIP_COMBO.flag` (skip combos entirely),
  `ARS_COMBO_MONTHS` (window size), `ARS_RENDER_DROPPED_MAILER=1` (render dropped slides),
  `ARS_CHART_CACHE=0` (disable cache), `ARS_CHART_CACHE_DIR` (cache location).
