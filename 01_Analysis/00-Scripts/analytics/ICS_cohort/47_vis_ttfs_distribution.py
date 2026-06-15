# ============================================
# ics-47-vis-ttfs-distribution — Time-to-first-swipe distribution chart
# ============================================
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# Visual companion to ics-43 (which is print/table only). Two histograms
# side-by-side showing where in their lifecycle each cohort first swipes.
# Includes a "Never swiped" bar at the right, and dashed lines for the
# medians of both groups.
#
# Memory notes:
#   - Prior version called ics_cohort(data)/non_ics_cohort(data) (full
#     frame copies, 1-2 GB each) and then .apply(axis=1) per row, which
#     OOM'd the Jupyter kernel before the chart rendered.
#   - This version operates on boolean masks + a column slice of `data`.
#     Same vectorized TTFS as the fixed ics-43.
# Correctness: pd.Period('Apr24', 'M') parses year-of-era as 0024; build
# the window-start Period via datetime.strptime instead.

import matplotlib.pyplot as plt
import matplotlib.ticker as _mtick_47
from datetime import datetime as _dt_47

print(f"\n📊 ics-47 — Time-to-first-swipe distribution, ICS {STAT_LABEL} vs Non-ICS...")

# ------------------------------------------------------------------
# 24-month window anchored at ACTIVITY_END_DATE (via strptime)
# ------------------------------------------------------------------
_anchor_dt = _dt_47.strptime(last_12_months[-1], '%b%y')
_l24_periods = pd.period_range(
    end=pd.Period(year=_anchor_dt.year, month=_anchor_dt.month, freq='M'),
    periods=24, freq='M',
)
last_24_months = [p.strftime('%b%y') for p in _l24_periods]

_window_month_start = np.array(
    [pd.Timestamp(_dt_47.strptime(_m, '%b%y')) for _m in last_24_months]
)
_window_start_ts = _window_month_start[0]
_wstart_dt = _dt_47.strptime(last_24_months[0], '%b%y')
_window_start_period = pd.Period(year=_wstart_dt.year,
                                 month=_wstart_dt.month, freq='M')

# ------------------------------------------------------------------
# Cohort masks (no frame copies)
# ------------------------------------------------------------------
_ics_mask = (
    (data['ICS Account'] == 'Yes')
    & is_target_status(data['Stat Code'])
)
_non_mask = data['ICS Account'] != 'Yes'

print(f"   (ICS={int(_ics_mask.sum()):,} rows, "
      f"Non-ICS={int(_non_mask.sum()):,} rows; no frame copies)")


# ------------------------------------------------------------------
# Vectorized TTFS: returns array of TTFS months (NaN = never swiped
# in window).  Scoped to accounts opened inside the 24-month window.
# ------------------------------------------------------------------
def _ttfs_months(mask):
    _open = data['Date Opened']
    _in_window = (
        mask
        & _open.notna()
        & (_open >= _window_start_ts)
        & (_open <= ACTIVITY_END_DATE)
    )
    if not _in_window.any():
        return np.array([]), 0

    _cols_present = [(f"{_m} Swipes", i) for i, _m in enumerate(last_24_months)
                     if f"{_m} Swipes" in data.columns]
    if not _cols_present:
        return np.array([np.nan] * int(_in_window.sum())), int(_in_window.sum())

    _swipe_cols = [c for c, _ in _cols_present]
    _month_idxs = np.array([i for _, i in _cols_present])

    _swipes = data.loc[_in_window, _swipe_cols].to_numpy(dtype=float, na_value=0.0)
    _opened = (data.loc[_in_window, 'Date Opened'].values
               .astype('datetime64[M]').astype('datetime64[ns]'))
    _month_ts = _window_month_start[_month_idxs].astype('datetime64[ns]')

    _eligible = _month_ts[None, :] >= _opened[:, None]
    _has_swipe = _swipes > 0
    _hit = _eligible & _has_swipe

    _any_hit = _hit.any(axis=1)
    _first_idx = _hit.argmax(axis=1)

    _opened_period = data.loc[_in_window, 'Date Opened'].dt.to_period('M')
    _opened_offset_from_window = (_opened_period - _window_start_period).apply(
        lambda p: p.n
    ).to_numpy()

    _first_hit_offset = _month_idxs[_first_idx]
    _ttfs = _first_hit_offset - _opened_offset_from_window
    _ttfs = np.where(_any_hit, _ttfs, np.nan)

    # release temporaries
    del _swipes, _eligible, _has_swipe, _hit
    return _ttfs.astype(float), int(_in_window.sum())


_ics_ttfs, _ics_total = _ttfs_months(_ics_mask)
_non_ttfs, _non_total = _ttfs_months(_non_mask)

if _ics_total == 0 or _non_total == 0:
    raise RuntimeError(
        f"Need both ICS and Non-ICS rows opened inside the 24-month window "
        f"(ICS={_ics_total}, Non-ICS={_non_total})."
    )

# ------------------------------------------------------------------
# Bin: 0..11 months, 12+, never (NaN).  (Match ics-43's pct_m1/m3/m6
# notion of "by month N" = TTFS in 0..N-1 inclusive.)
# ------------------------------------------------------------------
_BINS = list(range(0, 12))   # 0..11 inclusive


def _bin(arr, total):
    if total == 0:
        return np.zeros(len(_BINS)), 0, 0
    swiped = arr[~np.isnan(arr)].astype(int)
    # Clip TTFS > 11 into the last numeric bin so the "Never" bar stays pure
    swiped_clipped = np.clip(swiped, 0, 11)
    hist = np.array([int((swiped_clipped == b).sum()) for b in _BINS])
    never = int(np.isnan(arr).sum())
    return hist, never, total


_ics_h, _ics_never, _ics_total = _bin(_ics_ttfs, _ics_total)
_non_h, _non_never, _non_total = _bin(_non_ttfs, _non_total)

_ics_pct = (_ics_h / _ics_total * 100) if _ics_total else _ics_h
_non_pct = (_non_h / _non_total * 100) if _non_total else _non_h
_ics_never_pct = (_ics_never / _ics_total * 100) if _ics_total else 0
_non_never_pct = (_non_never / _non_total * 100) if _non_total else 0

# Median months (only swiped accounts)
_ics_swiped = _ics_ttfs[~np.isnan(_ics_ttfs)]
_non_swiped = _non_ttfs[~np.isnan(_non_ttfs)]
_ics_med = float(np.median(_ics_swiped)) if _ics_swiped.size else float('nan')
_non_med = float(np.median(_non_swiped)) if _non_swiped.size else float('nan')

# ------------------------------------------------------------------
# Plot
# ------------------------------------------------------------------
if 'GEN_COLORS' not in dir():
    GEN_COLORS = {'info': '#2B6CB0', 'success': '#2F855A',
                  'warning': '#C05621', 'dark_text': '#1A202C',
                  'muted': '#718096'}

fig, ax = plt.subplots(figsize=(14, 6.5), dpi=140)

_x = np.arange(len(_BINS) + 1)   # 12 bars + "Never"
_x_labels = [f"M{m + 1}" for m in _BINS] + ['Never']
_width = 0.4

_ics_vals = list(_ics_pct) + [_ics_never_pct]
_non_vals = list(_non_pct) + [_non_never_pct]

ax.bar(_x - _width / 2, _non_vals, _width, color=GEN_COLORS['info'],
       edgecolor='white', label=f'Non-ICS  (n={_non_total:,})')
ax.bar(_x + _width / 2, _ics_vals, _width, color=GEN_COLORS['success'],
       edgecolor='white', label=f'ICS {STAT_LABEL}  (n={_ics_total:,})')

# Median lines on the numeric bars (not on the Never column)
if not np.isnan(_non_med) and _non_med <= 11:
    ax.axvline(_non_med - _width / 2, color=GEN_COLORS['info'], linestyle='--', alpha=0.7,
               label=f'Non-ICS median: {_non_med:.0f} mo')
if not np.isnan(_ics_med) and _ics_med <= 11:
    ax.axvline(_ics_med + _width / 2, color=GEN_COLORS['success'], linestyle='--', alpha=0.7,
               label=f'ICS median: {_ics_med:.0f} mo')

ax.set_title(f"Time to First Swipe — ICS {STAT_LABEL} vs Non-ICS  "
             f"(opened in last 24 months)",
             fontsize=16, weight='bold', pad=12, color=GEN_COLORS['dark_text'])
ax.set_xlabel("Month of first swipe (since account opened)",
              fontsize=13, fontweight='bold')
ax.set_ylabel("% of cohort", fontsize=13, fontweight='bold')
ax.set_xticks(_x)
ax.set_xticklabels(_x_labels, fontsize=11)
ax.tick_params(axis='y', labelsize=11)
ax.grid(True, axis='y', linestyle=':', alpha=0.5)
ax.legend(loc='upper right', frameon=False, fontsize=11)
ax.yaxis.set_major_formatter(_mtick_47.PercentFormatter(decimals=0))
for s in ('top', 'right'):
    ax.spines[s].set_visible(False)

plt.tight_layout()
fig.savefig("ttfs_distribution.png", dpi=160, bbox_inches='tight')
plt.show()
plt.close(fig)

print(f"\n✅ Rendered (saved: ttfs_distribution.png)")
print(f"   ICS  median TTFS : {_ics_med:.1f} months  "
      f"({_ics_total - _ics_never:,}/{_ics_total:,} swiped)")
print(f"   Non-ICS median   : {_non_med:.1f} months  "
      f"({_non_total - _non_never:,}/{_non_total:,} swiped)")
