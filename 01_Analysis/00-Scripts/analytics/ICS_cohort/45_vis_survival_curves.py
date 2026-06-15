# ============================================
# ics-45-vis-survival-curves — Kaplan-Meier survival curves: ICS vs Non-ICS
# ============================================
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
# Optional:   lifelines (nicer CI bands) and scipy (log-rank p-value).
#
# Survival = "% of accounts still open at month N after opening".
# Two curves overlaid (ICS vs Non-ICS).
# If `lifelines` is installed we use its KaplanMeierFitter + log-rank.
# Otherwise we fall back to a pure-NumPy step function + chi-squared
# log-rank (requires scipy for the p-value; if scipy is missing we just
# skip the p-value annotation).
#
# Memory: operates on boolean masks + a 2-column slice of `data`
# (['Date Opened', 'Date Closed']).  Never copies the frame.

import matplotlib.pyplot as plt
import matplotlib.ticker as _mtick_45

# Optional heavy deps
try:
    from lifelines import KaplanMeierFitter
    from lifelines.statistics import logrank_test
    _HAS_LIFELINES = True
except Exception:
    _HAS_LIFELINES = False

try:
    from scipy.stats import chi2 as _chi2_45
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False

print(f"\n📊 ics-45 — Survival curves, ICS {STAT_LABEL} vs Non-ICS...")
print(f"   lifelines: {'installed' if _HAS_LIFELINES else 'NOT installed (using NumPy fallback)'}")
print(f"   scipy    : {'installed' if _HAS_SCIPY else 'NOT installed (p-value will be skipped)'}")

if 'GEN_COLORS' not in dir():
    GEN_COLORS = {'info': '#2B6CB0', 'success': '#2F855A',
                  'warning': '#C05621', 'dark_text': '#1A202C',
                  'muted': '#718096'}

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


def _duration_event(mask):
    """Pull only (Date Opened, Date Closed) for rows in `mask`.
    Returns (duration_months_array, event_observed_array)."""
    _sub = data.loc[mask & data['Date Opened'].notna(), ['Date Opened', 'Date Closed']]
    if _sub.empty:
        return np.array([]), np.array([])
    _closed_mask = _sub['Date Closed'].notna().to_numpy()
    _closed_days = np.where(
        _closed_mask,
        (_sub['Date Closed'] - _sub['Date Opened']).dt.days.to_numpy(),
        (ACTIVITY_END_DATE - _sub['Date Opened']).dt.days.to_numpy(),
    )
    _dur = np.clip(_closed_days / 30.4375, a_min=0, a_max=None)
    _event = _closed_mask.astype(int)
    return _dur, _event


_ics_dur, _ics_event = _duration_event(_ics_mask)
_non_dur, _non_event = _duration_event(_non_mask)

if len(_ics_dur) == 0 or len(_non_dur) == 0:
    raise RuntimeError("Need both ICS and Non-ICS rows with Date Opened.")


# ------------------------------------------------------------------
# Kaplan-Meier step function (pure NumPy)
# ------------------------------------------------------------------
def _km_curve(dur, event):
    """Return (times, survival) as step-function arrays starting at t=0, S=1."""
    if len(dur) == 0:
        return np.array([0.0]), np.array([1.0])
    order = np.argsort(dur)
    d = dur[order]
    e = event[order]
    n = len(d)
    # unique event times (only count closures)
    event_times = np.unique(d[e == 1])
    times = [0.0]
    surv = [1.0]
    s = 1.0
    n_at_risk = n
    last_t = 0.0
    for t in event_times:
        # censor anything strictly between last_t and t
        # (just update n_at_risk by counting remaining)
        n_at_risk = int(((d >= t)).sum())
        if n_at_risk == 0:
            break
        d_t = int(((d == t) & (e == 1)).sum())
        if d_t > 0:
            s *= (1 - d_t / n_at_risk)
        times.append(float(t))
        surv.append(float(s))
        last_t = t
    return np.array(times), np.array(surv)


# ------------------------------------------------------------------
# Manual log-rank test (chi-squared, 2 groups).  Needs scipy for p-value.
# ------------------------------------------------------------------
def _logrank_manual(dur1, ev1, dur2, ev2):
    all_times = np.unique(np.concatenate([
        dur1[ev1 == 1], dur2[ev2 == 1],
    ]))
    if len(all_times) == 0:
        return float('nan'), float('nan')
    O_minus_E = 0.0
    V = 0.0
    for t in all_times:
        n1 = int((dur1 >= t).sum())
        n2 = int((dur2 >= t).sum())
        n = n1 + n2
        if n <= 1:
            continue
        d1 = int(((dur1 == t) & (ev1 == 1)).sum())
        d2 = int(((dur2 == t) & (ev2 == 1)).sum())
        d = d1 + d2
        if d == 0:
            continue
        e1 = d * n1 / n
        v = (n1 * n2 * d * (n - d)) / (n * n * (n - 1)) if n > 1 else 0
        O_minus_E += (d1 - e1)
        V += v
    if V <= 0:
        return float('nan'), float('nan')
    chi2_stat = (O_minus_E ** 2) / V
    if _HAS_SCIPY:
        p = 1 - _chi2_45.cdf(chi2_stat, df=1)
    else:
        p = float('nan')
    return chi2_stat, p


# ------------------------------------------------------------------
# Compute + render
# ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(13, 7), dpi=140)

if _HAS_LIFELINES:
    _kmf_ics = KaplanMeierFitter().fit(
        durations=_ics_dur, event_observed=_ics_event,
        label=f'ICS {STAT_LABEL}  (n={len(_ics_dur):,})',
    )
    _kmf_non = KaplanMeierFitter().fit(
        durations=_non_dur, event_observed=_non_event,
        label=f'Non-ICS  (n={len(_non_dur):,})',
    )
    _kmf_ics.plot_survival_function(ax=ax, color=GEN_COLORS['success'], ci_alpha=0.18)
    _kmf_non.plot_survival_function(ax=ax, color=GEN_COLORS['info'], ci_alpha=0.18)
    _med_ics = float(_kmf_ics.median_survival_time_)
    _med_non = float(_kmf_non.median_survival_time_)
    _lr = logrank_test(_ics_dur, _non_dur,
                       event_observed_A=_ics_event,
                       event_observed_B=_non_event)
    _p = float(_lr.p_value)
    _chi2 = float(_lr.test_statistic)
else:
    t_ics, s_ics = _km_curve(_ics_dur, _ics_event)
    t_non, s_non = _km_curve(_non_dur, _non_event)
    ax.step(t_ics, s_ics, where='post', color=GEN_COLORS['success'],
            linewidth=2.8, label=f'ICS {STAT_LABEL}  (n={len(_ics_dur):,})')
    ax.step(t_non, s_non, where='post', color=GEN_COLORS['info'],
            linewidth=2.8, label=f'Non-ICS  (n={len(_non_dur):,})')
    # Median = first time S <= 0.5 (else NaN)
    _med_ics = float(t_ics[np.argmax(s_ics <= 0.5)]) if (s_ics <= 0.5).any() else float('nan')
    _med_non = float(t_non[np.argmax(s_non <= 0.5)]) if (s_non <= 0.5).any() else float('nan')
    _chi2, _p = _logrank_manual(_ics_dur, _ics_event, _non_dur, _non_event)

ax.set_title(f"Account Survival — ICS {STAT_LABEL} vs Non-ICS",
             fontsize=18, weight='bold', pad=12, color=GEN_COLORS['dark_text'])
ax.set_xlabel("Months since account opened", fontsize=14, fontweight='bold')
ax.set_ylabel("% still open", fontsize=14, fontweight='bold')
ax.set_ylim(0, 1.02)
ax.tick_params(axis='both', labelsize=12)
ax.yaxis.set_major_formatter(_mtick_45.PercentFormatter(1.0))
ax.grid(True, linestyle=':', alpha=0.5)
ax.legend(loc='lower left', frameon=False, fontsize=12)
for s in ('top', 'right'):
    ax.spines[s].set_visible(False)

# Significance annotation
if _p == _p:  # not NaN
    _sig = ("p < 0.001 (highly significant)" if _p < 0.001
            else (f"p = {_p:.3f} (significant)" if _p < 0.05
                  else f"p = {_p:.3f} (not significant)"))
    _note = f"Log-rank: χ² = {_chi2:.1f},  {_sig}"
else:
    _note = "Log-rank: χ² unavailable (scipy not installed)"

ax.text(0.98, 0.95, _note, transform=ax.transAxes, ha='right', va='top',
        fontsize=12, style='italic',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                  edgecolor='#cccccc', linewidth=1))

plt.tight_layout()
fig.savefig("survival_curves.png", dpi=160, bbox_inches='tight')
plt.show()
plt.close(fig)

print(f"\n✅ Rendered (saved: survival_curves.png)")
_fmt_med = lambda v: f"{v:.1f} months" if v == v else "not reached"
print(f"   Median survival ICS    : {_fmt_med(_med_ics)}")
print(f"   Median survival Non-ICS: {_fmt_med(_med_non)}")
if _p == _p:
    print(f"   Log-rank p-value       : {_p:.4g}")
else:
    print(f"   Log-rank p-value       : (scipy not installed)")
