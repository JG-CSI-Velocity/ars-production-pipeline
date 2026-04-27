# ===========================================================================
# CROSS-COHORT PANEL -- ARS Performance by Acquisition Channel
# ===========================================================================
# ONE question, answered four ways:
#   "Of accounts that received at least one ARS mailer, do ICS-acquired
#    accounts respond better and grow usage more than Non-ICS?"
#
# Denominator for every card = accounts mailed >= 1 ARS offer.
# Never-mailed accounts are NOT in any of these numbers (shown separately
# at the bottom of the print-out as a baseline count only).
#
# No invented terms:
#   - "Mailed"     = at least one non-null "<Mmm>YY Mail" column
#   - "Responded"  = at least one "<Mmm>YY Resp" column with a response
#                    code that format_odd counts as a response (not 'NU 1-4')
#   - "Tier"       = monthly-swipe bucket using the SAME cutoffs as
#                    shared/format_odd.py (<1 = Non-user, 1-5, 6-10, 11-15,
#                    16-20, 21-25, 26-40, 41+ Swipes). "Climbed >=1 tier"
#                    means bucket at most-recent active month is ranked
#                    higher than bucket at first active month.
# ===========================================================================

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch

if 'cross_df' not in dir() or len(cross_df) == 0:
    print('    cross_df not available. Run cross_cohort/01 first.')
else:
    if 'GEN_COLORS' not in dir():
        GEN_COLORS = {
            'info': '#2B6CB0', 'primary': '#2D3748', 'success': '#2F855A',
            'warning': '#C05621', 'dark_text': '#1A202C', 'muted': '#718096',
        }

    # ------------------------------------------------------------------
    # 1. Restrict to the ONLY population this panel talks about: mailed.
    # ------------------------------------------------------------------
    mailed = cross_df[cross_df['ever_mailed']].copy()
    ics_mailed = mailed[mailed['is_ics']]
    non_mailed = mailed[~mailed['is_ics']]

    n_ics_mailed = len(ics_mailed)
    n_non_mailed = len(non_mailed)

    # Never-mailed baseline (for the print-out only, not the cards)
    never = cross_df[cross_df['never_mailed']]
    n_ics_never = int(never['is_ics'].sum())
    n_non_never = int((~never['is_ics']).sum())

    def _pct(numer_mask, df_):
        if len(df_) == 0:
            return float('nan')
        return numer_mask.sum() / len(df_) * 100

    def _mean(series):
        if len(series) == 0:
            return float('nan')
        return float(series.mean())

    # ------------------------------------------------------------------
    # 2. Metrics (all denominators = mailed accounts of each channel)
    # ------------------------------------------------------------------
    resp_rate_ics = _pct(ics_mailed['ever_responded'], ics_mailed)
    resp_rate_non = _pct(non_mailed['ever_responded'], non_mailed)

    # Depth: among mailed accounts, avg number of responses
    avg_resp_ics = _mean(ics_mailed['n_responded'])
    avg_resp_non = _mean(non_mailed['n_responded'])

    # Usage growth: climbed >=1 tier bucket since first active month
    up_mask_ics = ics_mailed['tier_rank_delta'] > 0
    up_mask_non = non_mailed['tier_rank_delta'] > 0
    up_rate_ics = _pct(up_mask_ics, ics_mailed)
    up_rate_non = _pct(up_mask_non, non_mailed)

    # ------------------------------------------------------------------
    # 3. Formatting helpers
    # ------------------------------------------------------------------
    def _fmt_pct(x):
        return '--' if x != x else f'{x:.1f}%'

    def _fmt_num(x, prec=1):
        return '--' if x != x else f'{x:.{prec}f}'

    def _pp(a, b):
        if a != a or b != b:
            return ''
        d = a - b
        sign = '+' if d >= 0 else ''
        return f'ICS {sign}{d:.1f}pp vs Non-ICS'

    def _abs_diff(a, b):
        if a != a or b != b:
            return ''
        d = a - b
        sign = '+' if d >= 0 else ''
        return f'ICS {sign}{d:.2f} vs Non-ICS'

    # ------------------------------------------------------------------
    # 4. Card content -- ICS value shown FIRST on every card, always
    # ------------------------------------------------------------------
    kpi_data = [
        {
            'label': 'Mailed Accounts',
            'value': f'{n_ics_mailed:,}  |  {n_non_mailed:,}',
            'sub': 'ICS  |  Non-ICS   (denominator for all other cards)',
            'color': GEN_COLORS['info'],
        },
        {
            'label': 'Responded to >=1 Mailer',
            'value': f'{_fmt_pct(resp_rate_ics)}  |  {_fmt_pct(resp_rate_non)}',
            'sub': f'share of mailed accounts   |   {_pp(resp_rate_ics, resp_rate_non)}',
            'color': GEN_COLORS['success'],
        },
        {
            'label': 'Avg Responses per Mailed Account',
            'value': f'{_fmt_num(avg_resp_ics, 2)}  |  {_fmt_num(avg_resp_non, 2)}',
            'sub': f'includes zero-response accounts   |   {_abs_diff(avg_resp_ics, avg_resp_non)}',
            'color': GEN_COLORS['primary'],
        },
        {
            'label': 'Climbed >=1 Swipe Tier',
            'value': f'{_fmt_pct(up_rate_ics)}  |  {_fmt_pct(up_rate_non)}',
            'sub': f'current bucket above first-active bucket   |   {_pp(up_rate_ics, up_rate_non)}',
            'color': GEN_COLORS['warning'],
        },
    ]

    fig, axes = plt.subplots(1, 4, figsize=(20, 5.5))

    for ax, kpi in zip(axes, kpi_data):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')

        card = FancyBboxPatch(
            (0.3, 0.3), 9.4, 9.4,
            boxstyle='round,pad=0.3',
            facecolor=kpi['color'], edgecolor='white', linewidth=3,
        )
        ax.add_patch(card)

        ax.text(5, 7.2, kpi['label'],
                ha='center', va='center', fontsize=13, fontweight='bold',
                color='white', alpha=0.88)
        ax.text(5, 4.7, kpi['value'],
                ha='center', va='center', fontsize=26, fontweight='bold',
                color='white',
                path_effects=[pe.withStroke(linewidth=2, foreground=kpi['color'])])
        ax.text(5, 2.0, kpi['sub'],
                ha='center', va='center', fontsize=9.5,
                color='white', alpha=0.85, style='italic')

    fig.suptitle('ARS Performance by Acquisition Channel',
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
    fig.text(0.5, 0.98,
             'Scope: accounts mailed >=1 ARS offer.  Each card: ICS value | Non-ICS value.',
             ha='center', fontsize=12, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.savefig('cross_cohort_02_ars_by_ics.png', dpi=160, bbox_inches='tight')
    plt.show()
    plt.close(fig)

    # ------------------------------------------------------------------
    # 5. Plain-English recap (includes the never-mailed baseline here,
    #    OUT of the cards so it doesn't muddy the headline question)
    # ------------------------------------------------------------------
    print()
    print('    ARS Performance by Acquisition Channel')
    print('    Scope: mailed accounts only   ICS={:,}   Non-ICS={:,}'.format(n_ics_mailed, n_non_mailed))
    print()
    print('    Responded to >=1 mailer :  ICS {}   Non-ICS {}'
          .format(_fmt_pct(resp_rate_ics), _fmt_pct(resp_rate_non)))
    print('    Avg responses per acct  :  ICS {}   Non-ICS {}'
          .format(_fmt_num(avg_resp_ics, 2), _fmt_num(avg_resp_non, 2)))
    print('    Climbed >=1 swipe tier  :  ICS {}   Non-ICS {}'
          .format(_fmt_pct(up_rate_ics), _fmt_pct(up_rate_non)))
    print()
    print('    Never-mailed baseline (not in any card above):')
    print('        ICS never mailed     : {:,}'.format(n_ics_never))
    print('        Non-ICS never mailed : {:,}'.format(n_non_never))
