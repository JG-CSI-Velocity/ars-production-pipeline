# ============================================
# ics-32-cohort-activation-curves — Activation % by milestone, one line per cohort group
# ============================================
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers,
#             ics-31-cohort-milestones  (consumes `cohort_milestones_activation`).
#
# Purpose: a cohort can span many months, which makes the heatmap tall and
# the raw table overwhelming. This cell collapses cohorts into year-groups
# and plots one activation curve per group — M1/M3/M6/M9/M12/M18/M24 on
# the x-axis, Activation % on the y-axis.
#
# Older cohorts intentionally stop short (no future data yet) — the curve
# just ends, which visually answers "where does the data run out?".

import re as _re_curve
import matplotlib.pyplot as plt

print(f"\n📊 ics-32 — Cohort activation curves for ICS {STAT_LABEL}...")

# Self-sufficient: get the milestones frame from the kernel if it exists,
# otherwise build it now via the shared helper. No dependency on ics-31
# having run first.
_frame, _src_name = get_or_build_cohort_milestones()
print(f"   (milestones source: {_src_name})")

# ---- Discover milestone columns present in the frame --------------------
_milestone_cols = {}                                   # e.g. {1: 'M1 Activation %'}
for _c in _frame.columns:
    _m = _re_curve.match(r'^M(\d+) Activation %$', _c)
    if _m:
        _milestone_cols[int(_m.group(1))] = _c
if not _milestone_cols:
    raise ValueError("No M* Activation % columns found on cohort_milestones_activation.")
_ms_nums = sorted(_milestone_cols.keys())              # e.g. [1, 3, 6, 9, 12, 18, 24]

# ---- Group cohorts by opening year --------------------------------------
_work = _frame[['Opening Month', 'Cohort Size'] + [_milestone_cols[n] for n in _ms_nums]].copy()
_work['Opening Year'] = _work['Opening Month'].str.slice(0, 4)

# Cohort-size-weighted average of Activation % per (year, milestone)
rows = []
for _year, _block in _work.groupby('Opening Year'):
    _size = _block['Cohort Size'].sum()
    _row  = {
        'Opening Year':  _year,
        'Cohorts':       int(len(_block)),
        'Total Accounts': int(_size),
    }
    for _n in _ms_nums:
        _col      = _milestone_cols[_n]
        _active_n = (pd.to_numeric(_block[_col], errors='coerce')
                     * _block['Cohort Size']).sum(skipna=True)
        _valid    = (_block['Cohort Size'].where(
                        pd.to_numeric(_block[_col], errors='coerce').notna()
                    )).sum(skipna=True)
        _row[f'M{_n}'] = (_active_n / _valid) if _valid else float('nan')
    rows.append(_row)

activation_curves_by_year = pd.DataFrame(rows).sort_values('Opening Year').reset_index(drop=True)

display_formatted(
    activation_curves_by_year,
    f"ICS {STAT_LABEL} — Cohort-weighted Activation % by Opening Year"
)

# ---- Plot ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5.5), dpi=140)

_years = activation_curves_by_year['Opening Year'].tolist()
_cmap  = plt.cm.viridis
_colors = [_cmap(i / max(len(_years) - 1, 1)) for i in range(len(_years))]

for _color, (_idx, _r) in zip(_colors, activation_curves_by_year.iterrows()):
    _xs = [n for n in _ms_nums if pd.notna(_r[f'M{n}'])]
    _ys = [float(_r[f'M{n}']) * 100 for n in _xs]
    if not _xs:
        continue
    ax.plot(
        _xs, _ys,
        marker='o', linewidth=2.2, markersize=6,
        color=_color,
        label=f"{_r['Opening Year']}  ({int(_r['Total Accounts']):,} accts)",
    )
    for _x, _y in zip(_xs, _ys):
        ax.annotate(f"{_y:.0f}%", (_x, _y),
                    textcoords='offset points', xytext=(0, 7),
                    ha='center', fontsize=8, color=_color)

ax.set_title(f"ICS {STAT_LABEL} — Cohort Activation Curves (by Opening Year)",
             fontsize=14, weight='bold', pad=10)
ax.set_xlabel("Months since account opened", fontsize=11)
ax.set_ylabel("Activation % (cohort-size weighted)", fontsize=11)
ax.set_xticks(_ms_nums)
ax.set_xticklabels([f"M{n}" for n in _ms_nums])
ax.set_ylim(0, 100)
ax.grid(True, linestyle=':', alpha=0.5)
ax.legend(loc='best', frameon=False, fontsize=9, title="Opening Year")

plt.tight_layout()
fig.savefig("cohort_activation_curves.png", dpi=160, bbox_inches='tight')
plt.show()
plt.close(fig)                                      # free memory

print(f"\n✅ Rendered (saved: cohort_activation_curves.png)")
print(f"   Year groups plotted : {len(activation_curves_by_year)}")
print(f"   Milestones covered  : {[f'M{n}' for n in _ms_nums]}")
