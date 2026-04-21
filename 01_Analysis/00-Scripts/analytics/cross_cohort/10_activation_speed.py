# ===========================================================================
# CROSS-COHORT 10 -- Activation Speed (Time-to-First-Swipe)
# ===========================================================================
# Question: do ICS-acquired accounts start using their card faster?
#
# Scope: accounts with a known Date Opened, restricted to open_cohort months
# that exist in BOTH ICS and Non-ICS (so we never compare a 2021 ICS cohort
# to a 2024 Non-ICS cohort).
#
# TTFS definition: months between Date Opened (month-start) and the first
# monthly Swipes column where swipes > 0 AND the month is at/after the open
# month. NaN means no swipe found in the available window.
#
# Output:
#   1. Summary table: count, swiped/never, %-by-M1/M3/M6, median TTFS.
#   2. Histogram overlay ICS vs Non-ICS (months 0..12, plus "Never swiped").
# ===========================================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

_required = ('cross_df', 'CROSS_SWIPE_COLS')
if not all(n in dir() for n in _required):
    print('    cross_df / swipe columns not ready. Run cross_cohort/01 first.')
else:
    if 'GEN_COLORS' not in dir():
        GEN_COLORS = {'info': '#2B6CB0', 'success': '#2F855A',
                      'warning': '#C05621', 'dark_text': '#1A202C',
                      'muted': '#718096'}

    _MONTH_MAP = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                  'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}

    def _tag_to_ts(col, suffix=' Swipes'):
        tag = col.replace(suffix, '').strip()
        return pd.Timestamp(year=2000 + int(tag[3:]), month=_MONTH_MAP[tag[:3]], day=1)

    _swipe_ts = np.array([_tag_to_ts(c) for c in CROSS_SWIPE_COLS])

    # -----------------------------------------------------------------
    # 1. Cohort-match: keep open_cohort months that exist in BOTH groups
    # -----------------------------------------------------------------
    _has_date = cross_df['open_date'].notna()
    _shared_cohorts = (
        set(cross_df.loc[_has_date & cross_df['is_ics'], 'open_cohort'])
        & set(cross_df.loc[_has_date & ~cross_df['is_ics'], 'open_cohort'])
    )
    scope = cross_df[_has_date & cross_df['open_cohort'].isin(_shared_cohorts)].copy()

    if len(scope) == 0:
        print('    No open_cohort months overlap between ICS and Non-ICS. Skipping.')
    else:
        # -----------------------------------------------------------------
        # 2. Vectorized TTFS
        # -----------------------------------------------------------------
        def _ttfs_stats(frame):
            if len(frame) == 0:
                return None
            sw = frame[CROSS_SWIPE_COLS].apply(pd.to_numeric, errors='coerce').fillna(0).to_numpy()
            opened = frame['open_date'].values.astype('datetime64[M]').astype('datetime64[ns]')
            month_ts = _swipe_ts.astype('datetime64[ns]')
            eligible = month_ts[None, :] >= opened[:, None]
            hit = eligible & (sw > 0)
            any_hit = hit.any(axis=1)
            first_idx = hit.argmax(axis=1)

            # months between open and first-hit-month
            first_hit_ts = month_ts[first_idx]
            ttfs_months = np.where(
                any_hit,
                ((first_hit_ts.astype('datetime64[M]') - opened.astype('datetime64[M]'))
                 .astype('timedelta64[M]').astype(int)),
                -1,
            )
            return {
                'count': len(frame),
                'swiped': int(any_hit.sum()),
                'never': int((~any_hit).sum()),
                'ttfs': ttfs_months,   # -1 = never
                'any_hit': any_hit,
            }

        ics_s = _ttfs_stats(scope[scope['is_ics']])
        non_s = _ttfs_stats(scope[~scope['is_ics']])

        def _by_m(stats, k):
            if stats is None or stats['count'] == 0:
                return float('nan')
            return float(((stats['ttfs'] >= 0) & (stats['ttfs'] <= k)).sum()) / stats['count']

        def _median(stats):
            if stats is None or stats['swiped'] == 0:
                return float('nan')
            return float(np.median(stats['ttfs'][stats['any_hit']]))

        # -----------------------------------------------------------------
        # 3. Summary table
        # -----------------------------------------------------------------
        rows = [
            ('Accounts in cohort-matched scope', ics_s['count'], non_s['count']),
            ('Swiped at least once',              ics_s['swiped'], non_s['swiped']),
            ('Never swiped',                      ics_s['never'],  non_s['never']),
            ('% swiped by month 1',               _by_m(ics_s, 0), _by_m(non_s, 0)),
            ('% swiped by month 3',               _by_m(ics_s, 2), _by_m(non_s, 2)),
            ('% swiped by month 6',               _by_m(ics_s, 5), _by_m(non_s, 5)),
            ('Median months to first swipe',      _median(ics_s),  _median(non_s)),
        ]

        def _fmt(v, kind):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return '--'
            if kind == 'pct':
                return f'{v * 100:.1f}%'
            if kind == 'count':
                return f'{int(v):,}'
            return f'{v:.1f}'

        kinds = ['count', 'count', 'count', 'pct', 'pct', 'pct', 'num']
        summary = pd.DataFrame(
            [(r[0], _fmt(r[1], k), _fmt(r[2], k)) for r, k in zip(rows, kinds)],
            columns=['Metric', 'ICS', 'Non-ICS'],
        )
        try:
            display_formatted(summary, 'Activation Speed  (cohort-matched)')  # noqa: F821
        except NameError:
            print('\n   Activation Speed  (cohort-matched, ICS vs Non-ICS)')
            print(summary.to_string(index=False))

        # -----------------------------------------------------------------
        # 4. Histogram overlay
        # -----------------------------------------------------------------
        def _hist(stats, max_m=12):
            if stats is None:
                return np.zeros(max_m + 2)
            arr = stats['ttfs']
            counts = np.zeros(max_m + 2)  # 0..max_m, then "later", then "never"
            for m in range(max_m + 1):
                counts[m] = int((arr == m).sum())
            counts[max_m + 1] = int(((arr > max_m) & (arr >= 0)).sum()) + int((arr == -1).sum())
            return counts

        max_m = 12
        ics_h = _hist(ics_s, max_m)
        non_h = _hist(non_s, max_m)
        labels = [str(i) for i in range(max_m + 1)] + [f'>{max_m} / never']

        ics_share = ics_h / max(ics_h.sum(), 1) * 100
        non_share = non_h / max(non_h.sum(), 1) * 100

        fig, ax = plt.subplots(figsize=(14, 6))
        x = np.arange(len(labels))
        w = 0.38
        ax.bar(x - w / 2, ics_share, w, label='ICS', color=GEN_COLORS['success'])
        ax.bar(x + w / 2, non_share, w, label='Non-ICS', color=GEN_COLORS['info'])

        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_xlabel('Months from account open to first swipe')
        ax.set_ylabel('Share of cohort (%)')
        ax.set_title('Activation Speed  —  ICS vs Non-ICS (cohort-matched on open month)',
                     fontsize=16, fontweight='bold', color=GEN_COLORS['dark_text'], pad=14)
        ax.legend(frameon=False)
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)

        fig.text(0.5, 0.02,
                 f'Scope: {len(_shared_cohorts)} open-cohort months present in both groups.  '
                 f'N ICS={ics_s["count"]:,}  N Non-ICS={non_s["count"]:,}.',
                 ha='center', fontsize=10, color=GEN_COLORS['muted'], style='italic')

        plt.tight_layout()
        plt.savefig('cross_cohort_10_ttfs.png', dpi=160, bbox_inches='tight')
        plt.show()
        plt.close(fig)

        _ics_m3 = _by_m(ics_s, 2)
        _non_m3 = _by_m(non_s, 2)
        if _ics_m3 == _ics_m3 and _non_m3 == _non_m3:
            faster = 'faster' if _ics_m3 > _non_m3 else 'slower'
            print(f'\n    Activation by month 3: ICS {_ics_m3 * 100:.1f}%   Non-ICS {_non_m3 * 100:.1f}%   '
                  f'({(_ics_m3 - _non_m3) * 100:+.1f}pp, ICS {faster})')
