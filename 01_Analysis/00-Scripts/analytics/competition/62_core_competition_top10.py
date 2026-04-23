# ===========================================================================
# COMPETITION -- Top 10 Competitors (Banks + BNPL, Excludes Wallets + P2P)
# ===========================================================================
# Named ranking of the top 10 competitor institutions by transaction volume.
# Excludes wallets + P2P; BNPL is retained so Affirm/Klarna/Afterpay can
# appear alongside banks on the leaderboard.
#
# Assumes competitor_txns, GEN_COLORS, CATEGORY_PALETTE are in globals.
# ===========================================================================

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

EXCLUDE_CATS = ('wallets', 'p2p')
banks_bnpl_txns = competitor_txns[~competitor_txns['competitor_category'].isin(EXCLUDE_CATS)].copy()
excluded_txns = len(competitor_txns) - len(banks_bnpl_txns)
excluded_pct = excluded_txns / max(len(competitor_txns), 1) * 100
SCOPE_NOTE = (f"Excludes wallets + P2P ({excluded_txns:,} txns, "
              f"{excluded_pct:.1f}% of competitor activity). BNPL retained.")

if len(banks_bnpl_txns) == 0:
    print("    No qualifying competitor transactions. Skipping.")
else:
    top10 = (
        banks_bnpl_txns.groupby('competitor_match')
        .agg(txns=('amount', 'count'),
             accounts=('primary_account_num', 'nunique'),
             spend=('amount', 'sum'),
             category=('competitor_category', 'first'))
        .sort_values('txns', ascending=False)
        .head(10)
    )
    total_scope_accts = banks_bnpl_txns['primary_account_num'].nunique()
    top10['reach_pct'] = top10['accounts'] / max(total_scope_accts, 1) * 100

    fig, ax = plt.subplots(figsize=(22, 8))
    fig.patch.set_facecolor('#FFFFFF')
    ax.axis('off')
    ax.set_xlim(0, 22)
    ax.set_ylim(-0.6, len(top10) + 1.8)
    ax.invert_yaxis()

    ax.text(0.3, 0, "Top 10 Competitors — by Transaction Volume",
            fontsize=26, fontweight='bold', color=GEN_COLORS['dark_text'])
    ax.text(0.3, 0.7, SCOPE_NOTE,
            fontsize=13, color=GEN_COLORS['muted'], style='italic')

    headers = ['Rank', 'Competitor', 'Transactions', 'Accounts', 'Reach %',
               'Total Spend', 'Category']
    h_x = [0.3, 1.6, 8.5, 11.0, 13.4, 15.5, 18.2]
    for hx, h in zip(h_x, headers):
        ax.text(hx, 1.8, h, fontsize=14, fontweight='bold',
                color=GEN_COLORS['muted'])
    ax.plot([0.3, 21.5], [2.1, 2.1], color=GEN_COLORS['grid'], linewidth=1.5)

    for i, (merchant, row) in enumerate(top10.iterrows()):
        y = i + 2.6
        cat_label = row['category'].replace('_', ' ').title()
        cat_color = CATEGORY_PALETTE.get(cat_label, GEN_COLORS['muted'])
        name = str(merchant)[:36] + '..' if len(str(merchant)) > 38 else str(merchant)

        ax.text(h_x[0] + 0.3, y, f"{i + 1}", fontsize=18, fontweight='bold',
                color=GEN_COLORS['dark_text'], ha='center')
        ax.text(h_x[1], y, name, fontsize=15, fontweight='bold',
                color=GEN_COLORS['dark_text'])
        ax.text(h_x[2], y, f"{int(row['txns']):,}",
                fontsize=15, fontweight='bold', color=GEN_COLORS['accent'])
        ax.text(h_x[3], y, f"{int(row['accounts']):,}",
                fontsize=14, color=GEN_COLORS['dark_text'])
        ax.text(h_x[4], y, f"{row['reach_pct']:.1f}%",
                fontsize=14, fontweight='bold', color=GEN_COLORS['info'])
        ax.text(h_x[5], y, f"${row['spend']:,.0f}",
                fontsize=14, color=GEN_COLORS['dark_text'])

        badge = FancyBboxPatch(
            (h_x[6] - 0.1, y - 0.28), max(len(cat_label) * 0.19 + 0.4, 2.2), 0.55,
            boxstyle="round,pad=0.08", facecolor=cat_color,
            alpha=0.12, edgecolor=cat_color, linewidth=1.2,
        )
        ax.add_patch(badge)
        ax.text(h_x[6] + 0.1, y, cat_label,
                fontsize=12, fontweight='bold', color=cat_color)

        if i < len(top10) - 1:
            ax.plot([0.3, 21.5], [y + 0.42, y + 0.42],
                    color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)

    plt.tight_layout()
    plt.savefig('competition_62_banks_bnpl_top10.png', dpi=160, bbox_inches='tight')
    plt.show()
    plt.close(fig)

    _top1 = top10.iloc[0]
    _top1_name = top10.index[0]
    print(f"\n    Top competitor: {_top1_name} — "
          f"{int(_top1['txns']):,} txns across {int(_top1['accounts']):,} accounts "
          f"({_top1['reach_pct']:.1f}% reach).")
    print(f"    10 competitors account for {int(top10['txns'].sum()):,} of "
          f"{len(banks_bnpl_txns):,} in-scope transactions "
          f"({top10['txns'].sum() / max(len(banks_bnpl_txns), 1) * 100:.1f}%).")
