# ===========================================================================
# CROSS-COHORT 30 -- Usage-Tier Progression
# ===========================================================================
# Question: do ICS accounts migrate into heavier swipe-tier buckets faster
# than Non-ICS accounts?
#
# Tier buckets = shared/format_odd._categorize_swipes cutoffs (<1 = Non-user,
# 1-5, 6-10, 11-15, 16-20, 21-25, 26-40, 41+ Swipes).
#
# Two views:
#   A. Transition matrix  first_tier -> current_tier, ICS vs Non-ICS,
#      rendered as a heatmap pair so diagonal = stayed in bucket, upper
#      triangle = climbed, lower triangle = slipped.
#   B. Share in each tier over time -- computed per-period by bucketizing
#      the per-month Swipes columns. Plotted as stacked lines (% of each
#      group in each tier at each period).
# ===========================================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

if 'cross_df' not in dir() or 'CROSS_SWIPE_COLS' not in dir() or 'CROSS_TIER_LABELS' not in dir():
    print('    cross_df / tier metadata not ready. Run cross_cohort/01 first.')
else:
    if 'GEN_COLORS' not in dir():
        GEN_COLORS = {'info': '#2B6CB0', 'success': '#2F855A',
                      'warning': '#C05621', 'dark_text': '#1A202C',
                      'muted': '#718096'}

    TIERS = CROSS_TIER_LABELS
    RANK = CROSS_TIER_RANK

    # -----------------------------------------------------------------
    # A. Transition matrices (first_tier -> current_tier)
    # -----------------------------------------------------------------
    def _matrix(frame):
        m = (frame.groupby(['first_tier', 'current_tier'])
             .size().unstack(fill_value=0)
             .reindex(index=TIERS, columns=TIERS, fill_value=0))
        row_sum = m.sum(axis=1).replace(0, 1)
        return m.div(row_sum, axis=0) * 100, m

    ics_pct, ics_raw = _matrix(cross_df[cross_df['is_ics']])
    non_pct, non_raw = _matrix(cross_df[~cross_df['is_ics']])

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    cmap = LinearSegmentedColormap.from_list('cc30', ['#F7FAFC', GEN_COLORS['success']])
    for ax, pct, raw, title in [
        (axes[0], ics_pct, ics_raw, f'ICS  (N={int(ics_raw.values.sum()):,})'),
        (axes[1], non_pct, non_raw, f'Non-ICS  (N={int(non_raw.values.sum()):,})'),
    ]:
        im = ax.imshow(pct.values, cmap=cmap, vmin=0, vmax=100, aspect='auto')
        for r in range(pct.shape[0]):
            for c in range(pct.shape[1]):
                v = pct.values[r, c]
                if v >= 1:
                    ax.text(c, r, f'{v:.0f}', ha='center', va='center',
                            color='white' if v > 55 else GEN_COLORS['dark_text'], fontsize=9)
        ax.set_xticks(range(len(TIERS)))
        ax.set_yticks(range(len(TIERS)))
        ax.set_xticklabels(TIERS, rotation=45, ha='right')
        ax.set_yticklabels(TIERS)
        ax.set_xlabel('Current tier')
        ax.set_ylabel('First-active tier')
        ax.set_title(title, fontsize=14, fontweight='bold', color=GEN_COLORS['dark_text'])

    fig.colorbar(im, ax=axes, shrink=0.7, label='% of first-tier row')
    fig.suptitle('Tier Transition: First-Active Month -> Most-Recent Active Month',
                 fontsize=17, fontweight='bold', color=GEN_COLORS['dark_text'], y=1.02)
    fig.text(0.5, -0.01,
             'Diagonal = stayed in bucket.  Above diagonal = climbed.  Below = slipped.  '
             'Buckets follow shared/format_odd.py cutoffs.',
             ha='center', fontsize=10, color=GEN_COLORS['muted'], style='italic')
    plt.tight_layout()
    plt.savefig('cross_cohort_30_transition.png', dpi=160, bbox_inches='tight')
    plt.show()
    plt.close(fig)

    # -----------------------------------------------------------------
    # B. Tier share over time (per-period bucketize)
    # -----------------------------------------------------------------
    _MONTH_MAP = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                  'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}

    def _tag_to_label(col):
        tag = col.replace(' Swipes', '').strip()
        return tag  # e.g. "Mar26"

    period_labels = [_tag_to_label(c) for c in CROSS_SWIPE_COLS]
    if len(period_labels) == 0:
        print('    No per-period Swipes columns. Skipping time-series view.')
    else:
        def _bucket(v):
            if np.isnan(v) or v < 1:
                return 'Non-user'
            if v <= 5:
                return '1-5 Swipes'
            if v <= 10:
                return '6-10 Swipes'
            if v <= 15:
                return '11-15 Swipes'
            if v <= 20:
                return '16-20 Swipes'
            if v <= 25:
                return '21-25 Swipes'
            if v <= 40:
                return '26-40 Swipes'
            return '41+ Swipes'

        def _share_over_time(frame):
            sw = frame[CROSS_SWIPE_COLS].apply(pd.to_numeric, errors='coerce').fillna(0).to_numpy()
            shares = np.zeros((len(period_labels), len(TIERS)))
            for j in range(sw.shape[1]):
                col = sw[:, j]
                tiers = np.array([_bucket(v) for v in col])
                for ti, tier in enumerate(TIERS):
                    shares[j, ti] = (tiers == tier).sum() / max(len(col), 1) * 100
            return shares  # rows = periods, cols = tiers

        ics_share = _share_over_time(cross_df[cross_df['is_ics']])
        non_share = _share_over_time(cross_df[~cross_df['is_ics']])

        # Focus: heavy-tier share (rank >= 4, i.e. >= 16 Swipes/mo)
        heavy_idx = [i for i, t in enumerate(TIERS) if RANK[t] >= 4]
        ics_heavy = ics_share[:, heavy_idx].sum(axis=1)
        non_heavy = non_share[:, heavy_idx].sum(axis=1)
        ics_nonuser = ics_share[:, 0]
        non_nonuser = non_share[:, 0]

        fig, axes = plt.subplots(1, 2, figsize=(18, 6), sharex=True)
        x = np.arange(len(period_labels))
        axes[0].plot(x, ics_heavy, marker='o', linewidth=2.2, color=GEN_COLORS['success'], label='ICS')
        axes[0].plot(x, non_heavy, marker='o', linewidth=2.2, color=GEN_COLORS['info'], label='Non-ICS')
        axes[0].set_title('% of group in >=16 Swipes/mo tiers',
                          fontsize=14, fontweight='bold', color=GEN_COLORS['dark_text'])
        axes[0].set_ylabel('Share of group (%)')
        axes[0].legend(frameon=False)

        axes[1].plot(x, ics_nonuser, marker='o', linewidth=2.2, color=GEN_COLORS['success'], label='ICS')
        axes[1].plot(x, non_nonuser, marker='o', linewidth=2.2, color=GEN_COLORS['info'], label='Non-ICS')
        axes[1].set_title('% of group with 0 swipes that month',
                          fontsize=14, fontweight='bold', color=GEN_COLORS['dark_text'])
        axes[1].set_ylabel('Share of group (%)')
        axes[1].legend(frameon=False)

        for ax in axes:
            ax.set_xticks(x)
            ax.set_xticklabels(period_labels, rotation=45, ha='right')
            for s in ('top', 'right'):
                ax.spines[s].set_visible(False)

        fig.suptitle('Tier Share Over Time  —  ICS vs Non-ICS',
                     fontsize=17, fontweight='bold', color=GEN_COLORS['dark_text'], y=1.02)
        fig.text(0.5, -0.02,
                 'Left: climbing into heavy-usage tiers.  Right: share that was inactive that month.  '
                 'Bucket cutoffs from shared/format_odd.py.',
                 ha='center', fontsize=10, color=GEN_COLORS['muted'], style='italic')
        plt.tight_layout()
        plt.savefig('cross_cohort_30_timeseries.png', dpi=160, bbox_inches='tight')
        plt.show()
        plt.close(fig)

        print(f'\n    Heavy-tier share (latest period, {period_labels[-1]}): '
              f'ICS {ics_heavy[-1]:.1f}%   Non-ICS {non_heavy[-1]:.1f}%   '
              f'(+{ics_heavy[-1] - non_heavy[-1]:.1f}pp)')
        print(f'    Inactive share (latest period):                      '
              f'ICS {ics_nonuser[-1]:.1f}%   Non-ICS {non_nonuser[-1]:.1f}%   '
              f'({ics_nonuser[-1] - non_nonuser[-1]:+.1f}pp)')
