# ===========================================================================
# BNPL ACCOUNT SHARE (Ex Wallets + P2P)
# ===========================================================================
# Parallel to cell 29 (wallet_share) but for BNPL, since wallets are excluded
# from the 60-series. For each top BNPL provider, shows the top 20 accounts
# by BNPL spend (stacked against their in-CU spend if `competitor_spend_analysis`
# is available from cell 18).
#
# Assumes competitor_txns, GEN_COLORS are in globals.
# ===========================================================================

import matplotlib.pyplot as plt

EXCLUDE_CATS = ('wallets', 'p2p')
banks_bnpl_txns = competitor_txns[~competitor_txns['competitor_category'].isin(EXCLUDE_CATS)].copy()
excluded_txns = len(competitor_txns) - len(banks_bnpl_txns)
excluded_pct = excluded_txns / max(len(competitor_txns), 1) * 100
SCOPE_NOTE = (f"Excludes wallets + P2P ({excluded_txns:,} txns, "
              f"{excluded_pct:.1f}% of competitor activity). BNPL retained.")


def _fmt_currency(x, _pos=None):
    return f"${int(x):,}"


bnpl_txns = banks_bnpl_txns[banks_bnpl_txns['competitor_category'] == 'bnpl']
if len(bnpl_txns) == 0:
    print("    No BNPL activity detected (Affirm / Klarna / Afterpay). Skipping.")
else:
    bnpl_providers = (bnpl_txns.groupby('competitor_match')
                      .agg(spend=('amount', 'sum'),
                           accts=('primary_account_num', 'nunique'),
                           txns=('amount', 'count'))
                      .sort_values('spend', ascending=False))

    print(f"    BNPL providers detected: {len(bnpl_providers)}")
    print(f"    Total BNPL accounts (distinct): "
          f"{bnpl_txns['primary_account_num'].nunique():,}")
    print(f"    Total BNPL spend: ${bnpl_txns['amount'].sum():,.0f}")
    print()

    top_providers = bnpl_providers.head(5).index.tolist()
    use_cu_compare = 'competitor_spend_analysis' in dir() and \
                    isinstance(competitor_spend_analysis, dict)

    for provider in top_providers:
        prov_txns = bnpl_txns[bnpl_txns['competitor_match'] == provider]

        if use_cu_compare and provider in competitor_spend_analysis:
            df = competitor_spend_analysis[provider]
            top = df.sort_values('total_spend', ascending=False).head(20).sort_values('total_spend')
            n = len(top)
            fig, ax = plt.subplots(figsize=(14, max(5, n * 0.45 + 3)))
            ax.barh(range(n), top['your_spend'],
                    color=GEN_COLORS['success'], label='Your Spend',
                    edgecolor='white', linewidth=1, height=0.6, zorder=3)
            ax.barh(range(n), top['competitor_spend'],
                    left=top['your_spend'],
                    color=GEN_COLORS['accent'], label=f'{provider} Spend',
                    edgecolor='white', linewidth=1, height=0.6, zorder=3)
            ax.set_yticks(range(n))
            ax.set_yticklabels([f"Account {i + 1}" for i in range(n)],
                               fontsize=11, fontweight='bold')
            ax.set_xlabel('Total Spend ($)', fontsize=14, fontweight='bold', labelpad=10)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(_fmt_currency))
            for i, (_, row) in enumerate(top.iterrows()):
                total = row['total_spend']
                pct = row.get('competitor_pct', 0)
                ax.text(total * 1.02, i, f"${total:,.0f} ({pct:.0f}% at {provider})",
                        fontsize=10, va='center', color=GEN_COLORS['dark_text'])
            ax.set_title(f"{provider} — Top 20 Accounts by Total Spend",
                         fontsize=20, fontweight='bold',
                         color=GEN_COLORS['dark_text'], pad=14, loc='left')
            ax.legend(frameon=False, fontsize=12, loc='lower right')
            for s in ('top', 'right'):
                ax.spines[s].set_visible(False)
            fig.text(0.5, -0.02, SCOPE_NOTE,
                     ha='center', fontsize=12, color=GEN_COLORS['muted'],
                     style='italic')
            plt.tight_layout()
            safe_name = str(provider).lower().replace(' ', '_')
            plt.savefig(f'competition_66_bnpl_share_{safe_name}.png',
                        dpi=160, bbox_inches='tight')
            plt.show(); plt.close(fig)
        else:
            # Simpler fallback: top-20 accounts by BNPL spend with this provider
            acct_totals = (prov_txns.groupby('primary_account_num')['amount']
                           .sum().sort_values(ascending=False).head(20))
            if acct_totals.empty:
                continue
            acct_totals = acct_totals.sort_values()
            fig, ax = plt.subplots(figsize=(14, max(5, len(acct_totals) * 0.45 + 3)))
            ax.barh(range(len(acct_totals)), acct_totals.values,
                    color=GEN_COLORS['accent'], edgecolor='white',
                    linewidth=1, height=0.6, zorder=3)
            ax.set_yticks(range(len(acct_totals)))
            ax.set_yticklabels([f"Account {i + 1}" for i in range(len(acct_totals))],
                               fontsize=11, fontweight='bold')
            ax.set_xlabel('BNPL Spend ($)', fontsize=14, fontweight='bold', labelpad=10)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(_fmt_currency))
            for i, v in enumerate(acct_totals.values):
                ax.text(v * 1.02, i, f"${v:,.0f}",
                        fontsize=10, va='center', color=GEN_COLORS['dark_text'])
            ax.set_title(f"{provider} — Top 20 Accounts by BNPL Spend",
                         fontsize=20, fontweight='bold',
                         color=GEN_COLORS['dark_text'], pad=14, loc='left')
            for s in ('top', 'right'):
                ax.spines[s].set_visible(False)
            fig.text(0.5, -0.02,
                     f"{SCOPE_NOTE}  "
                     f"(Run cell 18 first for CU-vs-competitor stacked comparison.)",
                     ha='center', fontsize=12, color=GEN_COLORS['muted'], style='italic')
            plt.tight_layout()
            safe_name = str(provider).lower().replace(' ', '_')
            plt.savefig(f'competition_66_bnpl_share_{safe_name}.png',
                        dpi=160, bbox_inches='tight')
            plt.show(); plt.close(fig)

    print(f"    Rendered BNPL account-share for top {len(top_providers)} providers.")
