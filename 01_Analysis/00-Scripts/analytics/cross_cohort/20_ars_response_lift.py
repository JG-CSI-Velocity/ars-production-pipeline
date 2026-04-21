# ===========================================================================
# CROSS-COHORT 20 -- ARS Response Lift (cohort-matched)
# ===========================================================================
# Question: when we mail an ICS account, does it respond at a higher rate
# than a non-ICS account opened in the same month?
#
# Scope: accounts that were mailed >=1 ARS offer (never-mailed excluded).
# Cohort match: for each open_cohort month, require at least 30 mailed
# accounts in EACH group, otherwise bucket drops out (noise guard).
#
# Output:
#   1. Per-cohort table: mailed N and response rate, ICS vs Non-ICS, lift in pp.
#   2. Overall (scope-wide) response rate comparison.
#   3. Line chart: response rate by open_cohort month, ICS vs Non-ICS.
#   4. Companion card for never-mailed baseline (context only).
# ===========================================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

MIN_COHORT_N = 30   # per group, per open_cohort month

if 'cross_df' not in dir():
    print('    cross_df not available. Run cross_cohort/01 first.')
else:
    if 'GEN_COLORS' not in dir():
        GEN_COLORS = {'info': '#2B6CB0', 'success': '#2F855A',
                      'warning': '#C05621', 'dark_text': '#1A202C',
                      'muted': '#718096'}

    mailed = cross_df[cross_df['ever_mailed'] & cross_df['open_cohort'].notna()].copy()
    mailed['open_cohort'] = mailed['open_cohort'].astype(str)

    if len(mailed) == 0:
        print('    No mailed accounts in cross_df. Skipping.')
    else:
        g = (
            mailed.groupby(['open_cohort', 'is_ics'])
            .agg(mailed_n=('acct_number', 'size'),
                 responded_n=('ever_responded', 'sum'))
            .reset_index()
        )
        g['resp_rate'] = g['responded_n'] / g['mailed_n']

        ics = g[g['is_ics']].rename(columns={
            'mailed_n': 'ICS mailed', 'responded_n': 'ICS responded',
            'resp_rate': 'ICS resp rate',
        })[['open_cohort', 'ICS mailed', 'ICS responded', 'ICS resp rate']]

        non = g[~g['is_ics']].rename(columns={
            'mailed_n': 'Non-ICS mailed', 'responded_n': 'Non-ICS responded',
            'resp_rate': 'Non-ICS resp rate',
        })[['open_cohort', 'Non-ICS mailed', 'Non-ICS responded', 'Non-ICS resp rate']]

        by_cohort = ics.merge(non, on='open_cohort', how='inner')
        enough = ((by_cohort['ICS mailed'] >= MIN_COHORT_N)
                  & (by_cohort['Non-ICS mailed'] >= MIN_COHORT_N))
        by_cohort = by_cohort[enough].sort_values('open_cohort').reset_index(drop=True)

        if len(by_cohort) == 0:
            print(f'    No open_cohort month has >= {MIN_COHORT_N} mailed accounts in BOTH groups.')
            print(f'    Full group totals: mailed ICS={int(mailed["is_ics"].sum()):,}  '
                  f'Non-ICS={int((~mailed["is_ics"]).sum()):,}')
        else:
            by_cohort['Lift (pp)'] = (by_cohort['ICS resp rate']
                                      - by_cohort['Non-ICS resp rate']) * 100

            show = by_cohort.copy()
            for c in ('ICS resp rate', 'Non-ICS resp rate'):
                show[c] = show[c].map(lambda v: f'{v * 100:.1f}%' if pd.notna(v) else '--')
            show['Lift (pp)'] = show['Lift (pp)'].map(lambda v: f'{v:+.1f}')
            for c in ('ICS mailed', 'ICS responded', 'Non-ICS mailed', 'Non-ICS responded'):
                show[c] = show[c].map('{:,}'.format)

            try:
                display_formatted(show, f'Response Rate by Open-Cohort Month  (>= {MIN_COHORT_N}/group)')  # noqa: F821
            except NameError:
                print(f'\n   Response Rate by Open-Cohort Month  (>= {MIN_COHORT_N}/group)')
                print(show.to_string(index=False))

            # Scope-wide (headline) numbers
            ics_mail_N = int((mailed['is_ics']).sum())
            ics_resp_N = int(mailed.loc[mailed['is_ics'], 'ever_responded'].sum())
            non_mail_N = int((~mailed['is_ics']).sum())
            non_resp_N = int(mailed.loc[~mailed['is_ics'], 'ever_responded'].sum())
            ics_rate = ics_resp_N / ics_mail_N if ics_mail_N else float('nan')
            non_rate = non_resp_N / non_mail_N if non_mail_N else float('nan')
            lift_overall = (ics_rate - non_rate) * 100 if (ics_mail_N and non_mail_N) else float('nan')

            # Line chart
            fig, ax = plt.subplots(figsize=(14, 6))
            x = np.arange(len(by_cohort))
            ax.plot(x, by_cohort['ICS resp rate'] * 100, marker='o', color=GEN_COLORS['success'],
                    linewidth=2.4, label='ICS')
            ax.plot(x, by_cohort['Non-ICS resp rate'] * 100, marker='o', color=GEN_COLORS['info'],
                    linewidth=2.4, label='Non-ICS')

            ax.set_xticks(x)
            ax.set_xticklabels(by_cohort['open_cohort'], rotation=45, ha='right')
            ax.set_xlabel('Open-cohort month')
            ax.set_ylabel('Response rate  (% of mailed accounts)')
            ax.set_title('ARS Response Rate by Open-Cohort Month  —  ICS vs Non-ICS',
                         fontsize=16, fontweight='bold', color=GEN_COLORS['dark_text'], pad=14)

            # Lift bar at the bottom
            ax2 = ax.twinx()
            ax2.bar(x, by_cohort['Lift (pp)'].astype(float), alpha=0.12,
                    color=GEN_COLORS['warning'], label='ICS lift (pp)')
            ax2.set_ylabel('Lift (pp, bars)', color=GEN_COLORS['warning'])
            ax2.tick_params(axis='y', colors=GEN_COLORS['warning'])

            for s in ('top',):
                ax.spines[s].set_visible(False)
                ax2.spines[s].set_visible(False)

            ax.legend(loc='upper left', frameon=False)
            fig.text(0.5, 0.02,
                     f'Scope: mailed accounts, >= {MIN_COHORT_N} per group per cohort month.  '
                     f'Overall: ICS {ics_rate * 100:.1f}%  Non-ICS {non_rate * 100:.1f}%  '
                     f'({lift_overall:+.1f}pp).',
                     ha='center', fontsize=10, color=GEN_COLORS['muted'], style='italic')
            plt.tight_layout()
            plt.savefig('cross_cohort_20_response_lift.png', dpi=160, bbox_inches='tight')
            plt.show()
            plt.close(fig)

            print(f'\n    Overall (scope-wide, all mailed accounts):')
            print(f'        ICS     : {ics_resp_N:,} / {ics_mail_N:,} = {ics_rate * 100:.1f}%')
            print(f'        Non-ICS : {non_resp_N:,} / {non_mail_N:,} = {non_rate * 100:.1f}%')
            print(f'        Lift    : {lift_overall:+.1f}pp')

            # Never-mailed baseline
            never = cross_df[cross_df['never_mailed']]
            print()
            print(f'    Never-mailed (not in any chart above):')
            print(f'        ICS     never mailed : {int(never["is_ics"].sum()):,}')
            print(f'        Non-ICS never mailed : {int((~never["is_ics"]).sum()):,}')
