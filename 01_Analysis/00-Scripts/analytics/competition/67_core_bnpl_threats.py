# ===========================================================================
# BNPL THREATS (Ex Wallets + P2P)
# ===========================================================================
# Parallel to cell 33 (non_bank_threats) but limited to BNPL, since wallets
# and P2P are excluded from the 60-series. Ranks BNPL providers (Affirm,
# Klarna, Afterpay, etc.) by threat metrics: spend, account reach,
# transactions, $/account/month.
#
# Assumes competitor_txns, combined_df, GEN_COLORS are in globals.
# ===========================================================================

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

EXCLUDE_CATS = ('wallets', 'p2p')
banks_bnpl_txns = competitor_txns[~competitor_txns['competitor_category'].isin(EXCLUDE_CATS)].copy()
excluded_txns = len(competitor_txns) - len(banks_bnpl_txns)
excluded_pct = excluded_txns / max(len(competitor_txns), 1) * 100
SCOPE_NOTE = (f"Excludes wallets + P2P ({excluded_txns:,} txns, "
              f"{excluded_pct:.1f}% of competitor activity). BNPL retained.")

bnpl = banks_bnpl_txns[banks_bnpl_txns['competitor_category'] == 'bnpl']
if len(bnpl) == 0:
    print("    No BNPL activity detected. Skipping.")
else:
    total_all_accts = combined_df['primary_account_num'].nunique()

    if 'DATASET_MONTHS' in dir() and DATASET_MONTHS:
        n_months = DATASET_MONTHS
    elif 'year_month' in bnpl.columns:
        n_months = max(bnpl['year_month'].nunique(), 1)
    else:
        n_months = 1

    providers = (bnpl.groupby('competitor_match')
                 .agg(spend=('amount', 'sum'),
                      accts=('primary_account_num', 'nunique'),
                      txns=('amount', 'count'))
                 .sort_values('spend', ascending=False))
    providers['reach_pct'] = providers['accts'] / max(total_all_accts, 1) * 100
    providers['spend_per_acct_month'] = (
        providers['spend'] / providers['accts'] / n_months
    ).fillna(0)
    providers['txns_per_acct'] = (
        providers['txns'] / providers['accts']
    ).fillna(0)

    total_bnpl_accts = bnpl['primary_account_num'].nunique()
    total_bnpl_spend = bnpl['amount'].sum()
    reach_pct = total_bnpl_accts / max(total_all_accts, 1) * 100
    spend_per_acct_month = (total_bnpl_spend / max(total_bnpl_accts, 1) / n_months)

    print("=" * 72)
    print("BNPL THREATS — Remaining non-bank displacement (ex wallets + P2P)")
    print("=" * 72)
    print(f"  Accounts using any BNPL : {total_bnpl_accts:,} "
          f"({reach_pct:.1f}% of all accounts)")
    print(f"  Total BNPL spend        : ${total_bnpl_spend:,.0f}")
    print(f"  $/account/month (avg)   : ${spend_per_acct_month:,.2f}")
    print(f"  Providers detected      : {len(providers)}")
    print()

    # --- Headline KPI strip ------------------------------------------------
    kpis = [
        (f"{reach_pct:.1f}%", "of Accounts\nCarry BNPL Balances", GEN_COLORS['accent']),
        (f"${total_bnpl_spend:,.0f}", "Total BNPL Spend\n(displaced from CU credit)", GEN_COLORS['warning']),
        (f"${spend_per_acct_month:,.0f}", "Avg BNPL Spend\nper Acct per Month", GEN_COLORS['info']),
        (f"{len(providers)}", "BNPL Providers\nDetected", GEN_COLORS['success']),
    ]
    fig0, axes0 = plt.subplots(1, 4, figsize=(22, 5.6))
    fig0.patch.set_facecolor('#FFFFFF')
    for ax, (value, label, color) in zip(axes0, kpis):
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
        ax.add_patch(FancyBboxPatch(
            (0.03, 0.05), 0.94, 0.90, boxstyle="round,pad=0.05",
            facecolor=color, alpha=0.08, edgecolor=color, linewidth=2.8))
        ax.text(0.5, 0.62, value, transform=ax.transAxes,
                fontsize=36, fontweight='bold', color=color,
                ha='center', va='center')
        ax.text(0.5, 0.20, label, transform=ax.transAxes,
                fontsize=14, fontweight='bold', color=GEN_COLORS['dark_text'],
                ha='center', va='center', linespacing=1.4)
    fig0.suptitle("BNPL Threat Snapshot",
                  fontsize=26, fontweight='bold',
                  color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
    fig0.text(0.5, 0.97, SCOPE_NOTE,
              ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')
    plt.tight_layout()
    plt.savefig('competition_67_bnpl_threats_kpi.png', dpi=160, bbox_inches='tight')
    plt.show(); plt.close(fig0)

    # --- Per-provider ranking table ---------------------------------------
    prov = providers.head(12)
    fig, ax = plt.subplots(figsize=(22, max(6, 0.7 * len(prov) + 2.5)))
    fig.patch.set_facecolor('#FFFFFF')
    ax.axis('off'); ax.set_xlim(0, 22); ax.set_ylim(-0.6, len(prov) + 1.8)
    ax.invert_yaxis()

    ax.text(0.3, 0, "BNPL Providers — Threat Ranking",
            fontsize=24, fontweight='bold', color=GEN_COLORS['dark_text'])
    ax.text(0.3, 0.7, SCOPE_NOTE,
            fontsize=13, color=GEN_COLORS['muted'], style='italic')

    headers = ['Rank', 'Provider', 'Spend', 'Accounts', 'Reach %',
               'Txns', '$/Acct/Mo']
    h_x = [0.3, 1.6, 8.0, 11.0, 13.5, 15.6, 18.2]
    for hx, h in zip(h_x, headers):
        ax.text(hx, 1.8, h, fontsize=13, fontweight='bold',
                color=GEN_COLORS['muted'])
    ax.plot([0.3, 21.5], [2.1, 2.1], color=GEN_COLORS['grid'], linewidth=1.5)

    for i, (name, row) in enumerate(prov.iterrows()):
        y = i + 2.6
        nm = str(name)[:32] + '..' if len(str(name)) > 34 else str(name)
        ax.text(h_x[0] + 0.3, y, f"{i + 1}", fontsize=16, fontweight='bold',
                color=GEN_COLORS['dark_text'], ha='center')
        ax.text(h_x[1], y, nm, fontsize=14, fontweight='bold',
                color=GEN_COLORS['dark_text'])
        ax.text(h_x[2], y, f"${row['spend']:,.0f}",
                fontsize=14, fontweight='bold', color=GEN_COLORS['accent'])
        ax.text(h_x[3], y, f"{int(row['accts']):,}",
                fontsize=13, color=GEN_COLORS['dark_text'])
        ax.text(h_x[4], y, f"{row['reach_pct']:.1f}%",
                fontsize=13, fontweight='bold', color=GEN_COLORS['info'])
        ax.text(h_x[5], y, f"{int(row['txns']):,}",
                fontsize=13, color=GEN_COLORS['dark_text'])
        ax.text(h_x[6], y, f"${row['spend_per_acct_month']:,.2f}",
                fontsize=13, color=GEN_COLORS['warning'], fontweight='bold')
        if i < len(prov) - 1:
            ax.plot([0.3, 21.5], [y + 0.42, y + 0.42],
                    color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)

    plt.tight_layout()
    plt.savefig('competition_67_bnpl_threats_ranking.png', dpi=160, bbox_inches='tight')
    plt.show(); plt.close(fig)

    if len(prov) > 0:
        lead = prov.iloc[0]
        print(f"    Top BNPL threat: {prov.index[0]} — "
              f"${lead['spend']:,.0f} across {int(lead['accts']):,} accounts "
              f"({lead['reach_pct']:.1f}% reach, ${lead['spend_per_acct_month']:,.2f}/acct/mo).")
    if reach_pct >= 10:
        print(f"    SIGNAL: {reach_pct:.1f}% BNPL reach suggests material "
              f"revolving-credit displacement — consider card / personal-loan campaign.")
