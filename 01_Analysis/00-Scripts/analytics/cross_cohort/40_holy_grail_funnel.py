# ===========================================================================
# CROSS-COHORT 40 -- Holy-Grail Funnel
# ===========================================================================
# The one-slide story.  For ICS and Non-ICS separately, count:
#
#   Step 1: Accounts opened (denominator for everything else)
#   Step 2: Activated  -- swiped at least once within ACTIVATION_WINDOW_DAYS
#   Step 3: Mailed     -- received >=1 ARS offer AFTER open
#   Step 4: Responded  -- responded to >=1 ARS offer
#   Step 5: Tier-up    -- current swipe tier > first-active swipe tier
#
# Each step's % is reported against the TOTAL opened (Step 1), not against
# the previous step, so you can read each bar independently.  A parallel
# "relative to previous step" print-out is also shown for drop-off context.
#
# Activation window is configurable below.
# ===========================================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ACTIVATION_WINDOW_DAYS = 90

if 'cross_df' not in dir() or 'CROSS_SWIPE_COLS' not in dir():
    print('    cross_df / swipe columns not ready. Run cross_cohort/01 first.')
else:
    if 'GEN_COLORS' not in dir():
        GEN_COLORS = {'info': '#2B6CB0', 'success': '#2F855A',
                      'warning': '#C05621', 'dark_text': '#1A202C',
                      'muted': '#718096'}

    _MONTH_MAP = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                  'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}

    def _swipe_col_to_ts(c):
        tag = c.replace(' Swipes', '').strip()
        return pd.Timestamp(year=2000 + int(tag[3:]), month=_MONTH_MAP[tag[:3]], day=1)

    _swipe_ts = np.array([_swipe_col_to_ts(c) for c in CROSS_SWIPE_COLS])

    # ------------------------------------------------------------------
    # Step 2 -- "activated within N days"
    # ------------------------------------------------------------------
    def _activated_mask(frame):
        if len(frame) == 0:
            return np.zeros(0, dtype=bool)
        sw = frame[CROSS_SWIPE_COLS].apply(pd.to_numeric, errors='coerce').fillna(0).to_numpy()
        opened = frame['open_date'].values.astype('datetime64[ns]')

        month_ts = _swipe_ts.astype('datetime64[ns]')
        # Month-START dates, so a swipe in the same month counts as "within N days"
        # whenever N>=1 and open was on the 1st. Good enough at monthly granularity.
        deltas_days = (month_ts[None, :] - opened[:, None]).astype('timedelta64[D]').astype(int)
        within_window = (deltas_days >= 0) & (deltas_days <= ACTIVATION_WINDOW_DAYS + 31)
        has_swipe = sw > 0
        # +31 buffer because a Mar-opened account can only show swipes at the Mar column,
        # which is already ~0 days. Real cap is 90 days since open.
        real_within = (deltas_days >= 0) & (deltas_days <= ACTIVATION_WINDOW_DAYS)
        return (real_within & has_swipe).any(axis=1) | ((within_window & has_swipe).any(axis=1) & False)

    # ------------------------------------------------------------------
    # Step 3 -- "mailed AFTER open"
    # ------------------------------------------------------------------
    def _mailed_after_open_mask(frame):
        # We use first_mail_period from cell 01 and the open_date.
        # "Mailed after open" := first_mail_period month-end >= open_date month-start.
        fm = frame['first_mail_period']
        has_mail = frame['ever_mailed']

        def _ok(row_fm, row_open):
            if not isinstance(row_fm, pd.Period) or pd.isna(row_open):
                return False
            return row_fm.to_timestamp(how='end') >= pd.Timestamp(row_open).normalize()

        return np.array([
            h and _ok(f, o) for h, f, o in zip(has_mail, fm, frame['open_date'])
        ])

    # ------------------------------------------------------------------
    # Compute funnel for one group
    # ------------------------------------------------------------------
    def _funnel(frame):
        opened_mask = frame['open_date'].notna().values
        active_mask = _activated_mask(frame) & opened_mask
        mailed_after = _mailed_after_open_mask(frame) & opened_mask
        responded = (frame['ever_responded'].values) & mailed_after
        tier_up = (frame['tier_rank_delta'].values > 0) & opened_mask
        return {
            'opened': int(opened_mask.sum()),
            'activated': int(active_mask.sum()),
            'mailed_after_open': int(mailed_after.sum()),
            'responded': int(responded.sum()),
            'tier_up': int(tier_up.sum()),
        }

    ics_f = _funnel(cross_df[cross_df['is_ics']])
    non_f = _funnel(cross_df[~cross_df['is_ics']])

    steps = ['Opened', f'Activated\n(<= {ACTIVATION_WINDOW_DAYS}d)',
             'Mailed\n(after open)', 'Responded', 'Climbed\n>=1 tier']
    ics_vals = [ics_f['opened'], ics_f['activated'], ics_f['mailed_after_open'],
                ics_f['responded'], ics_f['tier_up']]
    non_vals = [non_f['opened'], non_f['activated'], non_f['mailed_after_open'],
                non_f['responded'], non_f['tier_up']]

    ics_pct = [v / ics_f['opened'] * 100 if ics_f['opened'] else 0 for v in ics_vals]
    non_pct = [v / non_f['opened'] * 100 if non_f['opened'] else 0 for v in non_vals]

    # ------------------------------------------------------------------
    # Chart: side-by-side funnels
    # ------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(18, 7), sharey=True)

    def _draw_funnel(ax, vals, pct, label, color):
        y = np.arange(len(steps))[::-1]
        width = np.array(pct) / 100.0
        ax.barh(y, width, color=color, alpha=0.85, edgecolor='white')
        for i, (v, p) in enumerate(zip(vals, pct)):
            ax.text(min(width[i] + 0.01, 1.01), y[i],
                    f'{v:,}  ({p:.1f}%)',
                    va='center', ha='left', fontsize=11, color=GEN_COLORS['dark_text'])
        ax.set_yticks(y)
        ax.set_yticklabels(steps)
        ax.set_xlim(0, 1.3)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
        ax.set_xlabel('% of opened accounts')
        ax.set_title(label, fontsize=15, fontweight='bold', color=GEN_COLORS['dark_text'])
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)

    _draw_funnel(axes[0], ics_vals, ics_pct,
                 f'ICS   (opened: {ics_f["opened"]:,})', GEN_COLORS['success'])
    _draw_funnel(axes[1], non_vals, non_pct,
                 f'Non-ICS   (opened: {non_f["opened"]:,})', GEN_COLORS['info'])

    fig.suptitle('Holy-Grail Funnel: Open -> Activate -> Mail -> Respond -> Tier-Up',
                 fontsize=17, fontweight='bold', color=GEN_COLORS['dark_text'], y=1.02)
    fig.text(0.5, -0.02,
             f'Percentages are against OPEN (step 1), not previous step.  '
             f'Activation window = {ACTIVATION_WINDOW_DAYS} days.  '
             f'Mail must occur AFTER open date.',
             ha='center', fontsize=10, color=GEN_COLORS['muted'], style='italic')
    plt.tight_layout()
    plt.savefig('cross_cohort_40_funnel.png', dpi=160, bbox_inches='tight')
    plt.show()
    plt.close(fig)

    # ------------------------------------------------------------------
    # Print relative drop-offs (step-to-step conversion)
    # ------------------------------------------------------------------
    def _rel(curr, prev):
        return f'{curr / prev * 100:.1f}%' if prev else '--'

    print('\n    Step-to-step conversion (relative to previous step)')
    print('    Step                 ICS               Non-ICS')
    print(f'    Opened              {ics_f["opened"]:>8,}         {non_f["opened"]:>8,}')
    print(f'    Activated           {_rel(ics_f["activated"], ics_f["opened"]):>8}  '
          f'of opened    {_rel(non_f["activated"], non_f["opened"]):>8}  of opened')
    print(f'    Mailed after open   {_rel(ics_f["mailed_after_open"], ics_f["activated"]):>8}  '
          f'of activated {_rel(non_f["mailed_after_open"], non_f["activated"]):>8}  of activated')
    print(f'    Responded           {_rel(ics_f["responded"], ics_f["mailed_after_open"]):>8}  '
          f'of mailed    {_rel(non_f["responded"], non_f["mailed_after_open"]):>8}  of mailed')
    print(f'    Climbed >=1 tier    {_rel(ics_f["tier_up"], ics_f["responded"]):>8}  '
          f'of responded {_rel(non_f["tier_up"], non_f["responded"]):>8}  of responded')
