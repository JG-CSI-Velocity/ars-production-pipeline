# ===========================================================================
# BANKS-ONLY VIEW -- Category Donut + Summary
# ===========================================================================
# Variant of 09_category_donut.py that EXCLUDES wallets / P2P / BNPL so
# the donut only shows competitor BANK categories (big nationals, digital
# banks, credit unions, local banks, top 25 fed district, etc.).
#
# The original cell 09 gives wallets/P2P their own slice; those dominate
# volume and drown out the bank story.  This version reports on banks
# only and notes the exclusion prominently.
# ===========================================================================

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.gridspec import GridSpec

# ------------------------------------------------------------------
# Defensive: rebuild anything missing from what's available.
# ------------------------------------------------------------------
if 'BANK_CATEGORIES' not in dir():
    if 'COMPETITOR_MERCHANTS' in dir():
        BANK_CATEGORIES = [k for k in COMPETITOR_MERCHANTS
                           if k not in ('wallets', 'p2p', 'bnpl')]
        print("    (derived BANK_CATEGORIES from COMPETITOR_MERCHANTS)")
    else:
        print("    BANK_CATEGORIES + COMPETITOR_MERCHANTS both missing. "
              "Run competition/01 first.")

if 'competitor_txns' not in dir():
    if 'combined_df' in dir() and 'tag_competitors' in dir():
        _tagged = tag_competitors(combined_df, merchant_col='merchant_consolidated')
        competitor_txns = _tagged[_tagged['competitor_category'].notna()].copy()
        if 'normalize_competitor_name' in dir():
            competitor_txns['competitor_match'] = (
                competitor_txns['merchant_consolidated'].apply(normalize_competitor_name)
            )
        print(f"    (rebuilt competitor_txns: {len(competitor_txns):,} rows)")
    else:
        print("    competitor_txns missing and cannot rebuild. "
              "Run competition/01 + 02 first.")

if 'CATEGORY_PALETTE' not in dir():
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

_required = ('competitor_txns', 'BANK_CATEGORIES', 'CATEGORY_PALETTE')
_missing = [n for n in _required if n not in dir()]
if _missing:
    print(f"    Still missing: {_missing}.")
else:
    if 'GEN_COLORS' not in dir():
        GEN_COLORS = {'info': '#2B6CB0', 'warning': '#C05621',
                      'dark_text': '#1A202C', 'muted': '#718096'}

    banks_only = competitor_txns[
        competitor_txns['competitor_category'].isin(BANK_CATEGORIES)
    ]
    _eco_txns = len(competitor_txns) - len(banks_only)
    _eco_pct = (_eco_txns / max(len(competitor_txns), 1)) * 100

    if len(banks_only) == 0:
        print("    No bank-category competitor transactions. Skipping.")
    else:
        cat_agg = (
            banks_only.groupby('competitor_category')
            .agg(total_transactions=('amount', 'count'))
            .sort_values('total_transactions', ascending=False)
        )
        cat_accts = (
            banks_only.groupby('competitor_category')['primary_account_num']
            .nunique().rename('unique_accounts')
        )
        cat_comps = (
            banks_only.groupby('competitor_category')['competitor_match']
            .nunique().rename('n_competitors')
        )
        cat_agg = cat_agg.join(cat_accts).join(cat_comps)
        cat_agg['unique_accounts'] = cat_agg['unique_accounts'].fillna(0).astype(int)
        cat_agg['n_competitors'] = cat_agg['n_competitors'].fillna(0).astype(int)
        cat_agg['pct'] = cat_agg['total_transactions'] / cat_agg['total_transactions'].sum() * 100
        cat_agg.index = cat_agg.index.str.replace('_', ' ').str.title()

        fig = plt.figure(figsize=(18, 9))
        gs = GridSpec(1, 2, width_ratios=[1, 1.1], wspace=0.05)

        # --- LEFT: Donut ---
        ax_donut = fig.add_subplot(gs[0])
        colors = [CATEGORY_PALETTE.get(c, GEN_COLORS['muted']) for c in cat_agg.index]

        wedges, texts, autotexts = ax_donut.pie(
            cat_agg['total_transactions'],
            labels=None,
            autopct='%1.0f%%',
            colors=colors,
            startangle=90,
            pctdistance=0.78,
            wedgeprops=dict(width=0.45, edgecolor='white', linewidth=3),
        )
        for t in autotexts:
            t.set_fontsize(18)
            t.set_fontweight('bold')
            t.set_color('white')
            t.set_path_effects([pe.withStroke(linewidth=2, foreground='#333333')])

        ax_donut.text(0, 0, f"{cat_agg['total_transactions'].sum():,.0f}\nBank Txns",
                      ha='center', va='center',
                      fontsize=20, fontweight='bold', color=GEN_COLORS['dark_text'])

        ax_donut.set_title("Transaction Share by Bank Category",
                           fontsize=22, fontweight='bold',
                           color=GEN_COLORS['dark_text'], pad=18)

        # --- RIGHT: Per-category stats table ---
        ax_tbl = fig.add_subplot(gs[1])
        ax_tbl.axis('off')

        y0 = 0.95
        step = 0.78 / max(len(cat_agg), 1)
        ax_tbl.text(0.02, y0 + 0.02, "Category", fontsize=14, fontweight='bold',
                    color=GEN_COLORS['muted'], transform=ax_tbl.transAxes)
        ax_tbl.text(0.55, y0 + 0.02, "Txns", fontsize=14, fontweight='bold',
                    color=GEN_COLORS['muted'], transform=ax_tbl.transAxes)
        ax_tbl.text(0.72, y0 + 0.02, "Accts", fontsize=14, fontweight='bold',
                    color=GEN_COLORS['muted'], transform=ax_tbl.transAxes)
        ax_tbl.text(0.88, y0 + 0.02, "# Comp.", fontsize=14, fontweight='bold',
                    color=GEN_COLORS['muted'], transform=ax_tbl.transAxes)

        for i, (cat, row) in enumerate(cat_agg.iterrows()):
            yy = y0 - (i + 1) * step
            color = CATEGORY_PALETTE.get(cat, GEN_COLORS['muted'])
            ax_tbl.add_patch(
                plt.Rectangle((0.0, yy - 0.02), 0.018, 0.03,
                              facecolor=color, transform=ax_tbl.transAxes,
                              clip_on=False)
            )
            ax_tbl.text(0.02, yy, cat, fontsize=15, fontweight='bold',
                        color=GEN_COLORS['dark_text'], transform=ax_tbl.transAxes,
                        va='center')
            ax_tbl.text(0.55, yy, f"{row['total_transactions']:,}",
                        fontsize=15, fontweight='bold', color=color,
                        transform=ax_tbl.transAxes, va='center')
            ax_tbl.text(0.72, yy, f"{row['unique_accounts']:,}",
                        fontsize=14, color=GEN_COLORS['dark_text'],
                        transform=ax_tbl.transAxes, va='center')
            ax_tbl.text(0.88, yy, f"{row['n_competitors']}",
                        fontsize=14, color=GEN_COLORS['dark_text'],
                        transform=ax_tbl.transAxes, va='center')

        fig.suptitle("Category Breakdown — Banks Only",
                     fontsize=28, fontweight='bold',
                     color=GEN_COLORS['dark_text'], y=1.02)
        fig.text(0.5, 0.965,
                 f"Excludes wallets / P2P / BNPL ({_eco_txns:,} txns, {_eco_pct:.1f}% of competitor activity)",
                 ha='center', fontsize=14, color=GEN_COLORS['muted'], style='italic')

        plt.tight_layout()
        plt.savefig('competition_61_banks_only_donut.png', dpi=160, bbox_inches='tight')
        plt.show()
        plt.close(fig)

        print(f"\n    Banks-only donut: {len(cat_agg)} categories, "
              f"{cat_agg['total_transactions'].sum():,} transactions, "
              f"{banks_only['primary_account_num'].nunique():,} accounts.")
