# ===========================================================================
# COMPETITION KPI -- Banks + BNPL (Excludes Wallets + P2P)
# ===========================================================================
# Excludes digital wallets (Apple Pay, Venmo, PayPal, Cash App, ...) and P2P
# (Zelle). KEEPS BNPL (Affirm, Klarna, Afterpay) because BNPL balances
# substitute for credit-card / line-of-credit products.
#
# Assumes competitor_txns, combined_df, GEN_COLORS, CATEGORY_PALETTE are
# already in globals (run 01 -> 02 -> 06 first).
# ===========================================================================

from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

EXCLUDE_CATS = ('wallets', 'p2p')
banks_bnpl_txns = competitor_txns[~competitor_txns['competitor_category'].isin(EXCLUDE_CATS)].copy()
excluded_txns = len(competitor_txns) - len(banks_bnpl_txns)
excluded_pct = excluded_txns / max(len(competitor_txns), 1) * 100
SCOPE_NOTE = (f"Excludes wallets + P2P ({excluded_txns:,} txns, "
              f"{excluded_pct:.1f}% of competitor activity). BNPL retained.")

if len(banks_bnpl_txns) == 0:
    print("    No qualifying competitor transactions. Skipping.")
else:
    total_trans = len(banks_bnpl_txns)
    total_accts = banks_bnpl_txns['primary_account_num'].nunique()
    total_comps = banks_bnpl_txns['competitor_match'].nunique()

    total_all_trans = len(combined_df)
    total_all_accts = combined_df['primary_account_num'].nunique()

    pct_trans = (total_trans / total_all_trans * 100) if total_all_trans else 0
    pct_accts = (total_accts / total_all_accts * 100) if total_all_accts else 0

    bnpl = banks_bnpl_txns[banks_bnpl_txns['competitor_category'] == 'bnpl']
    bnpl_accts = bnpl['primary_account_num'].nunique()
    bnpl_pct = (bnpl_accts / max(total_all_accts, 1)) * 100

    kpis = [
        (f"{pct_accts:.1f}%", "of Accounts\nUsing Bank + BNPL Competitors", GEN_COLORS['accent']),
        (f"{pct_trans:.1f}%", "of Transactions\nto Bank + BNPL Competitors", GEN_COLORS['info']),
        (f"{total_comps}",    "Distinct Competitors\nDetected",              GEN_COLORS['warning']),
        (f"{bnpl_pct:.1f}%",  "of Accounts\nCarrying BNPL Balances",         GEN_COLORS['success']),
    ]

    fig, axes = plt.subplots(1, 4, figsize=(22, 6))
    fig.patch.set_facecolor('#FFFFFF')
    for ax, (value, label, color) in zip(axes, kpis):
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
        ax.add_patch(FancyBboxPatch(
            (0.03, 0.05), 0.94, 0.90, boxstyle="round,pad=0.05",
            facecolor=color, alpha=0.08, edgecolor=color, linewidth=2.8,
        ))
        ax.text(0.5, 0.62, value, transform=ax.transAxes,
                fontsize=54, fontweight='bold', color=color,
                ha='center', va='center')
        ax.text(0.5, 0.20, label, transform=ax.transAxes,
                fontsize=16, fontweight='bold', color=GEN_COLORS['dark_text'],
                ha='center', va='center', linespacing=1.4)

    fig.suptitle("Competitive Exposure — Banks + BNPL",
                 fontsize=30, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.04)
    fig.text(0.5, 0.97, SCOPE_NOTE,
             ha='center', fontsize=14, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.savefig('competition_60_banks_bnpl_kpi.png', dpi=160, bbox_inches='tight')
    plt.show()
    plt.close(fig)

    if pct_accts < 25:
        print(f"\n    OPPORTUNITY: Only {pct_accts:.1f}% of accounts show "
              f"bank + BNPL competitor activity.")
    elif pct_accts > 45:
        print(f"\n    WARNING: {pct_accts:.1f}% of accounts show bank + BNPL "
              f"competitor activity. Significant displacement risk.")
