# ===========================================================================
# BANKS-ONLY VIEW -- Top 10 Competitor Banks
# ===========================================================================
# Banks-only ranking of the top 10 competitor institutions by transaction
# volume, account reach, and (optionally) dollar spend.  Excludes wallets /
# P2P / BNPL so the leaderboard surfaces real competitor banks (Chase,
# Chime, SoFi, etc.) rather than ecosystem aggregators.
#
# Companion to 60 (KPI) and 61 (donut).  Use this as the "name names"
# slide in the deck.
# ===========================================================================

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# ------------------------------------------------------------------
# Defensive bootstrap via try/except NameError (portable across any
# runner -- Jupyter, pipeline.exec, pytest, subprocess).
# ------------------------------------------------------------------
_BOOT_OK = True

try:
    BANK_CATEGORIES
except NameError:
    try:
        BANK_CATEGORIES = [k for k in COMPETITOR_MERCHANTS
                           if k not in ('wallets', 'p2p', 'bnpl')]
        print("    (derived BANK_CATEGORIES from COMPETITOR_MERCHANTS)")
    except NameError:
        print("    Missing BANK_CATEGORIES + COMPETITOR_MERCHANTS.  "
              "Run competition/01 first.")
        _BOOT_OK = False

try:
    competitor_txns
except NameError:
    try:
        _tagged = tag_competitors(combined_df, merchant_col='merchant_consolidated')
        competitor_txns = _tagged[_tagged['competitor_category'].notna()].copy()
        try:
            competitor_txns['competitor_match'] = (
                competitor_txns['merchant_consolidated'].apply(normalize_competitor_name)
            )
        except NameError:
            pass
        print(f"    (rebuilt competitor_txns: {len(competitor_txns):,} rows)")
    except NameError:
        print("    Missing competitor_txns and cannot rebuild.  "
              "Run competition/01 + 02 first.")
        _BOOT_OK = False

try:
    CATEGORY_PALETTE
except NameError:
    CATEGORY_PALETTE = {
        'Big Nationals':        '#E63946',
        'Top 25 Fed District':  '#C0392B',
        'Credit Unions':        '#2EC4B6',
        'Local Banks':          '#264653',
        'Digital Banks':        '#FF9F1C',
        'Custom':               '#F4A261',
        'Wallets':              '#6C757D',
        'P2p':                  '#A8DADC',
        'Bnpl':                 '#E76F51',
    }
    print("    (CATEGORY_PALETTE fallback applied; run competition/06 for full theme)")

try:
    GEN_COLORS
except NameError:
    GEN_COLORS = {'accent': '#E63946', 'info': '#2B6CB0',
                  'warning': '#C05621', 'dark_text': '#1A202C',
                  'muted': '#718096', 'grid': '#DDDDDD'}

if not _BOOT_OK:
    print("    Skipping -- required inputs missing.")
else:

    banks_only = competitor_txns[
        competitor_txns['competitor_category'].isin(BANK_CATEGORIES)
    ]
    _eco_txns = len(competitor_txns) - len(banks_only)
    _eco_pct = (_eco_txns / max(len(competitor_txns), 1)) * 100

    if len(banks_only) == 0:
        print("    No bank-category competitor transactions. Skipping.")
    else:
        top10 = (
            banks_only.groupby('competitor_match')
            .agg(
                txns=('amount', 'count'),
                accounts=('primary_account_num', 'nunique'),
                spend=('amount', 'sum'),
                category=('competitor_category', 'first'),
            )
            .sort_values('txns', ascending=False)
            .head(10)
        )

        total_bank_accts = banks_only['primary_account_num'].nunique()
        top10['reach_pct'] = top10['accounts'] / max(total_bank_accts, 1) * 100

        # ---- Render as a wide table-style chart ----
        fig, ax = plt.subplots(figsize=(22, 8))
        fig.patch.set_facecolor('#FFFFFF')
        ax.axis('off')
        ax.set_xlim(0, 22)
        ax.set_ylim(-0.6, len(top10) + 1.8)
        ax.invert_yaxis()

        ax.text(0.3, 0, "Top 10 Competitor Banks — by Transaction Volume",
                fontsize=26, fontweight='bold', color=GEN_COLORS['dark_text'])

        ax.text(0.3, 0.7,
                f"Excludes wallets / P2P / BNPL  "
                f"({_eco_txns:,} excluded txns, {_eco_pct:.1f}% of all competitor activity)",
                fontsize=13, color=GEN_COLORS['muted'], style='italic')

        headers = ['Rank', 'Competitor', 'Transactions', 'Accounts', 'Reach %',
                   'Total Spend', 'Category']
        h_x = [0.3, 1.6, 8.5, 11.0, 13.4, 15.5, 18.2]
        for hx, h in zip(h_x, headers):
            ax.text(hx, 1.8, h, fontsize=14, fontweight='bold',
                    color=GEN_COLORS['muted'])
        ax.plot([0.3, 21.5], [2.1, 2.1],
                color=GEN_COLORS['grid'], linewidth=1.5)

        for i, (merchant, row) in enumerate(top10.iterrows()):
            y = i + 2.6
            cat_label = row['category'].replace('_', ' ').title()
            cat_color = CATEGORY_PALETTE.get(cat_label, GEN_COLORS['muted'])
            name = str(merchant)[:36] + '..' if len(str(merchant)) > 38 else str(merchant)

            ax.text(h_x[0] + 0.3, y, f"{i + 1}",
                    fontsize=18, fontweight='bold',
                    color=GEN_COLORS['dark_text'], ha='center')
            ax.text(h_x[1], y, name, fontsize=15, fontweight='bold',
                    color=GEN_COLORS['dark_text'])
            ax.text(h_x[2], y, f"{row['txns']:,}",
                    fontsize=15, fontweight='bold',
                    color=GEN_COLORS['accent'])
            ax.text(h_x[3], y, f"{row['accounts']:,}",
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
        plt.savefig('competition_62_banks_only_top10.png', dpi=160, bbox_inches='tight')
        plt.show()
        plt.close(fig)

        # ---- Summary print ----
        _top1 = top10.iloc[0]
        _top1_name = top10.index[0]
        print(f"\n    Top bank competitor: {_top1_name} — "
              f"{int(_top1['txns']):,} txns across {int(_top1['accounts']):,} accounts "
              f"({_top1['reach_pct']:.1f}% reach).")
        print(f"    10 banks account for {int(top10['txns'].sum()):,} of "
              f"{len(banks_only):,} banks-only transactions "
              f"({top10['txns'].sum() / len(banks_only) * 100:.1f}%).")
