# ===========================================================================
# CROSS-COHORT KPI PANEL -- ICS vs Non-ICS at a glance
# ===========================================================================
# 4 KPI cards. Each card shows paired ICS / Non-ICS numbers so the delta is
# immediate: who mails better, who responds better, who ends up heavy-tier,
# who climbed at least one tier.
#
# Heavy-tier = top 3 tier buckets ('16-20 Swipes','21-25 Swipes','26-40
# Swipes','41+ Swipes' -- i.e. rank >= 4).
# ===========================================================================

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch

if 'cross_df' not in dir() or len(cross_df) == 0:
    print('    cross_df not available. Run cross_cohort/01 first.')
else:
    # Defensive theme fallbacks (conference theme may not be loaded yet)
    if 'GEN_COLORS' not in dir():
        GEN_COLORS = {
            'info': '#2B6CB0', 'primary': '#2D3748', 'success': '#2F855A',
            'warning': '#C05621', 'dark_text': '#1A202C', 'muted': '#718096',
        }

    _ics_mask = cross_df['is_ics']
    _non_mask = ~cross_df['is_ics']

    def _pct(mask_numerator, mask_denominator):
        d = int(mask_denominator.sum())
        if d == 0:
            return float('nan'), 0
        return int(mask_numerator.sum()) / d * 100, d

    # Card 1 -- account count + share
    n_total = len(cross_df)
    n_ics = int(_ics_mask.sum())
    n_non = int(_non_mask.sum())

    # Card 2 -- mailed rate (of all accounts; ICS vs non-ICS)
    mail_pct_ics, _ = _pct(cross_df['ever_mailed'] & _ics_mask, _ics_mask)
    mail_pct_non, _ = _pct(cross_df['ever_mailed'] & _non_mask, _non_mask)

    # Card 3 -- ARS response rate (of MAILED accounts)
    resp_pct_ics, mailed_ics = _pct(cross_df['ever_responded'] & _ics_mask,
                                    cross_df['ever_mailed'] & _ics_mask)
    resp_pct_non, mailed_non = _pct(cross_df['ever_responded'] & _non_mask,
                                    cross_df['ever_mailed'] & _non_mask)

    # Card 4 -- heavy-tier share (current_tier_rank >= 4)
    heavy_mask = cross_df['current_tier_rank'] >= 4
    heavy_pct_ics, _ = _pct(heavy_mask & _ics_mask, _ics_mask)
    heavy_pct_non, _ = _pct(heavy_mask & _non_mask, _non_mask)

    # Bonus signal for subtitle: tier-up rate
    up_mask = cross_df['tier_rank_delta'] > 0
    up_pct_ics, _ = _pct(up_mask & _ics_mask, _ics_mask)
    up_pct_non, _ = _pct(up_mask & _non_mask, _non_mask)

    def _fmt_pct(x):
        return '--' if x != x else f'{x:.1f}%'  # NaN-safe

    def _delta(a, b):
        if a != a or b != b:
            return ''
        d = a - b
        sign = '+' if d >= 0 else ''
        return f'{sign}{d:.1f}pp'

    kpi_data = [
        {
            'label': 'Portfolio Share',
            'value': f'{n_ics:,} / {n_non:,}',
            'sub': f'ICS  {n_ics / n_total * 100:.1f}%   vs   Non-ICS  {n_non / n_total * 100:.1f}%',
            'color': GEN_COLORS['info'],
        },
        {
            'label': 'ARS Mailed Rate',
            'value': f'{_fmt_pct(mail_pct_ics)} / {_fmt_pct(mail_pct_non)}',
            'sub': f'ICS vs Non-ICS   {_delta(mail_pct_ics, mail_pct_non)}',
            'color': GEN_COLORS['primary'],
        },
        {
            'label': 'ARS Response Rate',
            'value': f'{_fmt_pct(resp_pct_ics)} / {_fmt_pct(resp_pct_non)}',
            'sub': f'of mailed ({mailed_ics:,} ICS | {mailed_non:,} Non)   {_delta(resp_pct_ics, resp_pct_non)}',
            'color': GEN_COLORS['success'],
        },
        {
            'label': 'Heavy-Tier Share',
            'value': f'{_fmt_pct(heavy_pct_ics)} / {_fmt_pct(heavy_pct_non)}',
            'sub': f'ICS vs Non-ICS today   {_delta(heavy_pct_ics, heavy_pct_non)}',
            'color': GEN_COLORS['warning'],
        },
    ]

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))

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

        ax.text(5, 7.0, kpi['label'],
                ha='center', va='center', fontsize=14, fontweight='bold',
                color='white', alpha=0.85)
        ax.text(5, 4.7, kpi['value'],
                ha='center', va='center', fontsize=28, fontweight='bold',
                color='white',
                path_effects=[pe.withStroke(linewidth=2, foreground=kpi['color'])])
        ax.text(5, 2.0, kpi['sub'],
                ha='center', va='center', fontsize=10,
                color='white', alpha=0.85, style='italic')

    fig.suptitle('ICS vs Non-ICS  —  Cross-Cohort Overview',
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.04)
    fig.text(0.5, 0.97,
             f'Tier-up rate: ICS {_fmt_pct(up_pct_ics)}  vs  Non-ICS {_fmt_pct(up_pct_non)}'
             f'  ({_delta(up_pct_ics, up_pct_non)})',
             ha='center', fontsize=12, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.savefig('cross_cohort_02_kpi.png', dpi=160, bbox_inches='tight')
    plt.show()
    plt.close(fig)

    print(f'\n    Portfolio     : ICS {n_ics:,}  |  Non-ICS {n_non:,}')
    print(f'    Mailed        : ICS {_fmt_pct(mail_pct_ics)}  |  Non-ICS {_fmt_pct(mail_pct_non)}')
    print(f'    Response rate : ICS {_fmt_pct(resp_pct_ics)}  |  Non-ICS {_fmt_pct(resp_pct_non)}')
    print(f'    Heavy-tier    : ICS {_fmt_pct(heavy_pct_ics)}  |  Non-ICS {_fmt_pct(heavy_pct_non)}')
    print(f'    Tier-up rate  : ICS {_fmt_pct(up_pct_ics)}  |  Non-ICS {_fmt_pct(up_pct_non)}')
