# ===========================================================================
# CROSS-COHORT 50 -- ICS vs Non-ICS Competition Overlay
# ===========================================================================
# Question: are ICS-acquired accounts less heavily using competitor
# products (Chime, Cash App, wallets, etc.) than Non-ICS accounts?
#
# Joins cross_df (account-level, ICS flag) with competitor_txns from the
# competition pipeline (transaction-level, competitor_match + category).
# Excludes wallets / p2p / bnpl ecosystems so the comparison is apples-to-
# apples "true competitor banks only" unless INCLUDE_ECOSYSTEMS = True.
#
# Output:
#   1. Per-category reach: % of each group's accounts that transacted with
#      any competitor in that category.
#   2. Top-10 competitor merchants by account reach, side-by-side ICS vs
#      Non-ICS, sorted by the Non-ICS reach so the rows stay stable.
# ===========================================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

INCLUDE_ECOSYSTEMS = False

_required = ('cross_df', 'competitor_txns')
_missing = [n for n in _required if n not in dir()]
if _missing:
    print(f'    Missing: {_missing}. Run cross_cohort/01 AND competition/02 first.')
else:
    if 'GEN_COLORS' not in dir():
        GEN_COLORS = {'info': '#2B6CB0', 'success': '#2F855A',
                      'warning': '#C05621', 'dark_text': '#1A202C',
                      'muted': '#718096'}

    # --------------------------------------------------------------
    # 1. Build an account-level ICS lookup from cross_df
    # --------------------------------------------------------------
    ics_lookup = cross_df[['acct_number', 'is_ics', 'ics_channel']].copy()
    ics_lookup['acct_number'] = ics_lookup['acct_number'].astype(str).str.strip()

    # --------------------------------------------------------------
    # 2. Filter competitor_txns (optional: drop ecosystems)
    # --------------------------------------------------------------
    ct = competitor_txns.copy()
    ct['primary_account_num'] = ct['primary_account_num'].astype(str).str.strip()

    if not INCLUDE_ECOSYSTEMS and 'category' in ct.columns:
        ecosystem_cats = {'wallets', 'p2p', 'bnpl',
                          'Wallets', 'P2P', 'BNPL',
                          'wallet', 'p2p_payments'}
        ct = ct[~ct['category'].astype(str).isin(ecosystem_cats)].copy()

    # --------------------------------------------------------------
    # 3. Join + tag each txn with ICS status
    # --------------------------------------------------------------
    ct = ct.merge(ics_lookup, left_on='primary_account_num',
                  right_on='acct_number', how='left')
    ct['is_ics'] = ct['is_ics'].fillna(False)

    if ct.empty:
        print('    After filtering, no competitor transactions remain. Skipping.')
    else:
        # ----------------------------------------------------------
        # 4. Per-category reach (% of each group's accounts using >=1
        #    competitor in that category)
        # ----------------------------------------------------------
        ics_total = int(cross_df['is_ics'].sum())
        non_total = int((~cross_df['is_ics']).sum())

        cat_reach = (
            ct.groupby(['category', 'is_ics'])['primary_account_num']
            .nunique().unstack(fill_value=0)
            .rename(columns={True: 'ICS_accts', False: 'Non_accts'})
        )
        # Ensure both columns exist
        for c in ('ICS_accts', 'Non_accts'):
            if c not in cat_reach.columns:
                cat_reach[c] = 0
        cat_reach['ICS %'] = cat_reach['ICS_accts'] / max(ics_total, 1) * 100
        cat_reach['Non-ICS %'] = cat_reach['Non_accts'] / max(non_total, 1) * 100
        cat_reach['Lift (pp)'] = cat_reach['ICS %'] - cat_reach['Non-ICS %']
        cat_reach = cat_reach.sort_values('Non-ICS %', ascending=False)

        show = cat_reach.copy()
        for c in ('ICS_accts', 'Non_accts'):
            show[c] = show[c].map('{:,}'.format)
        for c in ('ICS %', 'Non-ICS %'):
            show[c] = show[c].map('{:.1f}%'.format)
        show['Lift (pp)'] = show['Lift (pp)'].map('{:+.1f}'.format)
        show = show.reset_index().rename(columns={
            'category': 'Competitor Category',
            'ICS_accts': 'ICS accounts',
            'Non_accts': 'Non-ICS accounts',
        })

        try:
            display_formatted(show,  # noqa: F821
                              f'Competitor Reach by Category  '
                              f'(ecosystems {"included" if INCLUDE_ECOSYSTEMS else "excluded"})')
        except NameError:
            print(f'\n   Competitor Reach by Category  '
                  f'(ecosystems {"included" if INCLUDE_ECOSYSTEMS else "excluded"})')
            print(show.to_string(index=False))

        # ----------------------------------------------------------
        # 5. Top-10 competitor merchants by Non-ICS reach
        # ----------------------------------------------------------
        merch_reach = (
            ct.groupby(['competitor_match', 'is_ics'])['primary_account_num']
            .nunique().unstack(fill_value=0)
        )
        for c in (True, False):
            if c not in merch_reach.columns:
                merch_reach[c] = 0
        merch_reach['ICS %'] = merch_reach[True] / max(ics_total, 1) * 100
        merch_reach['Non-ICS %'] = merch_reach[False] / max(non_total, 1) * 100
        top10 = merch_reach.sort_values('Non-ICS %', ascending=False).head(10).reset_index()

        if len(top10) == 0:
            print('    No competitor merchants after filter. Skipping merchant chart.')
        else:
            fig, ax = plt.subplots(figsize=(14, 7))
            y = np.arange(len(top10))[::-1]
            w = 0.38
            ax.barh(y - w / 2, top10['ICS %'], w,
                    color=GEN_COLORS['success'], label='ICS')
            ax.barh(y + w / 2, top10['Non-ICS %'], w,
                    color=GEN_COLORS['info'], label='Non-ICS')

            ax.set_yticks(y)
            ax.set_yticklabels(top10['competitor_match'])
            ax.set_xlabel('% of group with >=1 transaction at this competitor')
            ax.set_title('Top-10 Competitor Reach  —  ICS vs Non-ICS',
                         fontsize=16, fontweight='bold',
                         color=GEN_COLORS['dark_text'], pad=14)
            for i, (ics_v, non_v) in enumerate(zip(top10['ICS %'], top10['Non-ICS %'])):
                ax.text(ics_v + 0.3, y[i] - w / 2, f'{ics_v:.1f}%', va='center',
                        fontsize=9, color=GEN_COLORS['dark_text'])
                ax.text(non_v + 0.3, y[i] + w / 2, f'{non_v:.1f}%', va='center',
                        fontsize=9, color=GEN_COLORS['dark_text'])
            for s in ('top', 'right'):
                ax.spines[s].set_visible(False)
            ax.legend(frameon=False, loc='lower right')

            fig.text(0.5, -0.02,
                     f'Scope: competitor_txns from competition/02, '
                     f'ecosystems {"included" if INCLUDE_ECOSYSTEMS else "excluded"}.  '
                     f'Denominators: {ics_total:,} ICS / {non_total:,} Non-ICS accounts.',
                     ha='center', fontsize=10, color=GEN_COLORS['muted'], style='italic')
            plt.tight_layout()
            plt.savefig('cross_cohort_50_competition_overlay.png', dpi=160, bbox_inches='tight')
            plt.show()
            plt.close(fig)

        # ----------------------------------------------------------
        # 6. One-line takeaway
        # ----------------------------------------------------------
        print(f'\n    Denominators: ICS accounts={ics_total:,}  Non-ICS={non_total:,}')
        print(f'    Ecosystem categories (wallets/p2p/bnpl) '
              f'{"INCLUDED" if INCLUDE_ECOSYSTEMS else "EXCLUDED"}')
        if len(cat_reach):
            worst_for_ics = cat_reach['Lift (pp)'].idxmax()
            best_for_ics = cat_reach['Lift (pp)'].idxmin()
            print(f'    ICS over-indexes most in   : {worst_for_ics}  '
                  f'({cat_reach.loc[worst_for_ics, "Lift (pp)"]:+.1f}pp)')
            print(f'    ICS under-indexes most in  : {best_for_ics}  '
                  f'({cat_reach.loc[best_for_ics, "Lift (pp)"]:+.1f}pp)')
