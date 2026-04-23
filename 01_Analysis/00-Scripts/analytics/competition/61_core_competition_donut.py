# ===========================================================================
# COMPETITION DONUT -- Banks + BNPL (Excludes Wallets + P2P)
# ===========================================================================
# Category breakdown of competitor activity EXCLUDING wallets + P2P,
# KEEPING BNPL. Companion to 60 (KPI strip).
#
# Uses observed=True on groupby because competitor_category is pd.Categorical
# (tag_competitors uses it for memory efficiency). Without observed=True,
# filtered-out levels (wallets, p2p) would appear as empty rows.
#
# Assumes competitor_txns, GEN_COLORS, CATEGORY_PALETTE are in globals.
# ===========================================================================

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.gridspec import GridSpec

EXCLUDE_CATS = ('wallets', 'p2p')
banks_bnpl_txns = competitor_txns[~competitor_txns['competitor_category'].isin(EXCLUDE_CATS)].copy()
excluded_txns = len(competitor_txns) - len(banks_bnpl_txns)
excluded_pct = excluded_txns / max(len(competitor_txns), 1) * 100
SCOPE_NOTE = (f"Excludes wallets + P2P ({excluded_txns:,} txns, "
              f"{excluded_pct:.1f}% of competitor activity). BNPL retained.")

if len(banks_bnpl_txns) == 0:
    print("    No qualifying competitor transactions. Skipping.")
else:
    cat_agg = (
        banks_bnpl_txns.groupby('competitor_category', observed=True)
        .agg(total_transactions=('amount', 'count'),
             total_spend=('amount', 'sum'))
        .sort_values('total_transactions', ascending=False)
    )
    cat_accts = (banks_bnpl_txns.groupby('competitor_category', observed=True)['primary_account_num']
                 .nunique().rename('unique_accounts'))
    cat_comps = (banks_bnpl_txns.groupby('competitor_category', observed=True)['competitor_match']
                 .nunique().rename('n_competitors'))
    cat_agg = cat_agg.join(cat_accts).join(cat_comps)
    cat_agg['unique_accounts'] = cat_agg['unique_accounts'].fillna(0).astype(int)
    cat_agg['n_competitors'] = cat_agg['n_competitors'].fillna(0).astype(int)
    cat_agg.index = cat_agg.index.str.replace('_', ' ').str.title()

    fig = plt.figure(figsize=(18, 9))
    gs = GridSpec(1, 2, width_ratios=[1, 1.1], wspace=0.05)

    ax_d = fig.add_subplot(gs[0])
    colors = [CATEGORY_PALETTE.get(c, GEN_COLORS['muted']) for c in cat_agg.index]
    wedges, _, autos = ax_d.pie(
        cat_agg['total_transactions'], labels=None, autopct='%1.0f%%',
        colors=colors, startangle=90, pctdistance=0.78,
        wedgeprops=dict(width=0.45, edgecolor='white', linewidth=3),
    )
    for t in autos:
        t.set_fontsize(18); t.set_fontweight('bold'); t.set_color('white')
        t.set_path_effects([pe.withStroke(linewidth=2, foreground='#333333')])
    ax_d.text(0, 0, f"{int(cat_agg['total_transactions'].sum()):,}\nCompetitor\nTxns",
              ha='center', va='center',
              fontsize=19, fontweight='bold', color=GEN_COLORS['dark_text'])
    ax_d.set_title("Transaction Share by Category",
                   fontsize=22, fontweight='bold',
                   color=GEN_COLORS['dark_text'], pad=18)

    ax_t = fig.add_subplot(gs[1]); ax_t.axis('off')
    y0 = 0.95
    step = 0.78 / max(len(cat_agg), 1)
    for h, x in [('Category', 0.02), ('Txns', 0.50), ('Accts', 0.66),
                 ('$ Spend', 0.78), ('# Comp', 0.92)]:
        ax_t.text(x, y0 + 0.02, h, fontsize=14, fontweight='bold',
                  color=GEN_COLORS['muted'], transform=ax_t.transAxes)
    for i, (cat, row) in enumerate(cat_agg.iterrows()):
        yy = y0 - (i + 1) * step
        color = CATEGORY_PALETTE.get(cat, GEN_COLORS['muted'])
        ax_t.add_patch(plt.Rectangle((0.0, yy - 0.02), 0.018, 0.03,
                                     facecolor=color, transform=ax_t.transAxes,
                                     clip_on=False))
        ax_t.text(0.02, yy, cat, fontsize=14, fontweight='bold',
                  color=GEN_COLORS['dark_text'], transform=ax_t.transAxes, va='center')
        ax_t.text(0.50, yy, f"{int(row['total_transactions']):,}",
                  fontsize=14, fontweight='bold', color=color,
                  transform=ax_t.transAxes, va='center')
        ax_t.text(0.66, yy, f"{int(row['unique_accounts']):,}",
                  fontsize=13, color=GEN_COLORS['dark_text'],
                  transform=ax_t.transAxes, va='center')
        ax_t.text(0.78, yy, f"${row['total_spend']:,.0f}",
                  fontsize=13, color=GEN_COLORS['dark_text'],
                  transform=ax_t.transAxes, va='center')
        ax_t.text(0.92, yy, f"{int(row['n_competitors'])}",
                  fontsize=13, color=GEN_COLORS['dark_text'],
                  transform=ax_t.transAxes, va='center')

    fig.suptitle("Category Breakdown — Banks + BNPL (Ex Wallets + P2P)",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.02)
    fig.text(0.5, 0.965, SCOPE_NOTE,
             ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.savefig('competition_61_banks_bnpl_donut.png', dpi=160, bbox_inches='tight')
    plt.show()
    plt.close(fig)

    print(f"\n    Donut: {len(cat_agg)} categories, "
          f"{int(cat_agg['total_transactions'].sum()):,} transactions, "
          f"{banks_bnpl_txns['primary_account_num'].nunique():,} accounts.")
