# ============================================
# ics-48-vis-activation-curves — Weighted activation comparison (ICS vs Non-ICS)
# ============================================
# Depends on: ics-34-activation-by-cohort (consumes ics_activation_by_cohort
#             and nonics_activation_by_cohort from the kernel).
#
# The "tell the story in one chart" version of ics-34's weighted-average
# summary table.  X-axis = milestone in months (1, 3, 6, 9, 12, 24).
# Y-axis = % activated.  Two curves: ICS (success green) and Non-ICS
# (info blue).  The area between the curves is shaded in ICS green to
# make the cumulative lift visually obvious.  Percentage-point delta is
# annotated above each milestone pair.
#
# Large fonts throughout so it reads from a deck at a distance.

import matplotlib.pyplot as plt
import matplotlib.patheffects as _pe_48
import numpy as np

_required = ('ics_activation_by_cohort', 'nonics_activation_by_cohort')
if not all(n in dir() for n in _required):
    print("   Need ics-34 to have run first (ics_activation_by_cohort + "
          "nonics_activation_by_cohort).  Run ics-34 then re-run this cell.")
else:
    if 'GEN_COLORS' not in dir():
        GEN_COLORS = {'info': '#2B6CB0', 'success': '#2F855A',
                      'warning': '#C05621', 'dark_text': '#1A202C',
                      'muted': '#718096'}

    # (display-name, months-after-open)  -- must match _MILESTONES from ics-34
    _MS = [('M1', 1), ('M3', 3), ('M6', 6), ('M9', 9), ('M12', 12), ('M24', 24)]
    _COLS = [f'{m} %' for m, _ in _MS]
    _X = np.array([k for _, k in _MS])

    _ics_avg = ics_activation_by_cohort.iloc[-1]
    _non_avg = nonics_activation_by_cohort.iloc[-1]
    _ics_y = np.array([_ics_avg[c] * 100 if pd.notna(_ics_avg[c]) else np.nan for c in _COLS])
    _non_y = np.array([_non_avg[c] * 100 if pd.notna(_non_avg[c]) else np.nan for c in _COLS])

    _ics_n = int(_ics_avg['Cohort Size'])
    _non_n = int(_non_avg['Cohort Size'])

    fig, ax = plt.subplots(figsize=(16, 9))

    # Shaded gap between the two curves (only where both are defined)
    _both = ~np.isnan(_ics_y) & ~np.isnan(_non_y)
    ax.fill_between(
        _X[_both], _non_y[_both], _ics_y[_both],
        where=_ics_y[_both] >= _non_y[_both],
        color=GEN_COLORS['success'], alpha=0.12, interpolate=True, zorder=1,
        label='ICS lift',
    )

    # Non-ICS curve (behind)
    ax.plot(_X, _non_y, '-o', color=GEN_COLORS['info'],
            linewidth=3.4, markersize=12, markerfacecolor='white',
            markeredgewidth=2.8, markeredgecolor=GEN_COLORS['info'],
            label=f'ICS = No   (n = {_non_n:,})', zorder=2)

    # ICS curve (on top)
    ax.plot(_X, _ics_y, '-o', color=GEN_COLORS['success'],
            linewidth=3.8, markersize=14, markerfacecolor='white',
            markeredgewidth=3.0, markeredgecolor=GEN_COLORS['success'],
            label=f'ICS = Yes  (n = {_ics_n:,})', zorder=3)

    # Point labels
    for xi, (yi, yn) in enumerate(zip(_ics_y, _non_y)):
        if not np.isnan(yi):
            ax.annotate(
                f'{yi:.1f}%', (_X[xi], yi), xytext=(0, 14),
                textcoords='offset points', ha='center', fontsize=15,
                fontweight='bold', color=GEN_COLORS['success'],
                path_effects=[_pe_48.withStroke(linewidth=3, foreground='white')],
            )
        if not np.isnan(yn):
            ax.annotate(
                f'{yn:.1f}%', (_X[xi], yn), xytext=(0, -22),
                textcoords='offset points', ha='center', fontsize=15,
                fontweight='bold', color=GEN_COLORS['info'],
                path_effects=[_pe_48.withStroke(linewidth=3, foreground='white')],
            )

    # Lift annotation mid-gap for each milestone
    for xi, (yi, yn) in enumerate(zip(_ics_y, _non_y)):
        if np.isnan(yi) or np.isnan(yn):
            continue
        mid = (yi + yn) / 2
        dlt = yi - yn
        ax.annotate(
            f'{dlt:+.1f}pp', (_X[xi], mid), xytext=(22, 0),
            textcoords='offset points', ha='left', va='center',
            fontsize=12, fontweight='bold', color=GEN_COLORS['dark_text'],
            path_effects=[_pe_48.withStroke(linewidth=3, foreground='white')],
        )

    ax.set_xticks(_X)
    ax.set_xticklabels([m for m, _ in _MS], fontsize=16, fontweight='bold')
    ax.set_xlabel('Milestone (months after account open)',
                  fontsize=17, fontweight='bold', labelpad=12)
    ax.set_ylabel('% of cohort activated',
                  fontsize=17, fontweight='bold', labelpad=12)
    ax.tick_params(axis='y', labelsize=14)

    # Percentage axis formatter
    _ymax = max(np.nanmax(_ics_y), np.nanmax(_non_y))
    ax.set_ylim(0, min(100, _ymax + 15))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0f}%'))

    # Light gridlines
    ax.grid(axis='y', linestyle='--', linewidth=0.6, color=GEN_COLORS['muted'], alpha=0.5)

    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)

    ax.legend(loc='lower right', frameon=False, fontsize=15)

    ax.set_title(
        f'Activation Curve  —  ICS vs Non-ICS  ({STAT_LABEL})',
        fontsize=24, fontweight='bold', color=GEN_COLORS['dark_text'], pad=18, loc='left',
    )
    fig.text(
        0.12, 0.905,
        'Weighted average across opening-year cohorts.  Higher line = faster and deeper activation.',
        fontsize=13, color=GEN_COLORS['muted'], style='italic',
    )

    plt.tight_layout()
    plt.savefig('ics_48_activation_curves.png', dpi=160, bbox_inches='tight')
    plt.show()
    plt.close(fig)

    print(f"\n✅ Activation curve rendered")
    print(f"   ICS = Yes  : n = {_ics_n:,}")
    print(f"   ICS = No   : n = {_non_n:,}")
