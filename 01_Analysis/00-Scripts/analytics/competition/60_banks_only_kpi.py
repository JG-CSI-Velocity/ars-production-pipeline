# ===========================================================================
# BANKS-ONLY VIEW -- KPI Dashboard
# ===========================================================================
# Variant of 07_kpi_dashboard.py that EXCLUDES wallets / P2P / BNPL so the
# headline numbers reflect TRUE competitor banks only (Chase, Chime, SoFi,
# local banks, etc.) -- not AFFIRM / KLARNA / VENMO / ZELLE / APPLE PAY /
# CASH APP.
#
# When to use:
#   - Client views wallets and BNPL as complementary, not competing.
#   - You want the "bank-to-bank" deposit/card-share story without the
#     payment-ecosystem noise.
#
# When NOT to use:
#   - Client explicitly sees Chime/Zelle/Cash App as one displacement risk
#     and wants the full competitive exposure number.  (Use cell 07.)
# ===========================================================================

from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

# ------------------------------------------------------------------
# Defensive bootstrap.  try/except NameError is portable across any
# runner (Jupyter, pipeline.exec, pytest, subprocess) -- `in dir()`
# only sees local scope when the cell is exec'd with separate globals
# and locals.
# ------------------------------------------------------------------
_BOOT_OK = True

# BANK_CATEGORIES: derive from COMPETITOR_MERCHANTS if missing
try:
    BANK_CATEGORIES
except NameError:
    try:
        BANK_CATEGORIES = [k for k in COMPETITOR_MERCHANTS
                           if k not in ('wallets', 'p2p', 'bnpl')]
        print("    (derived BANK_CATEGORIES from COMPETITOR_MERCHANTS)")
    except NameError:
        print("    Missing BANK_CATEGORIES + COMPETITOR_MERCHANTS. "
              "Run competition/01 first.")
        _BOOT_OK = False

# competitor_txns: rebuild from combined_df if missing
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
        print(f"    (rebuilt competitor_txns from combined_df: "
              f"{len(competitor_txns):,} rows)")
    except NameError:
        print("    Missing competitor_txns and cannot rebuild "
              "(need combined_df + tag_competitors). Run competition/01 + 02 first.")
        _BOOT_OK = False

# combined_df required for totals
try:
    combined_df
except NameError:
    print("    Missing combined_df.  Run setup/txn_setup first.")
    _BOOT_OK = False

# GEN_COLORS fallback
try:
    GEN_COLORS
except NameError:
    GEN_COLORS = {'accent': '#E63946', 'info': '#2B6CB0',
                  'warning': '#C05621', 'success': '#2F855A',
                  'dark_text': '#1A202C', 'muted': '#718096'}

if not _BOOT_OK:
    print("    Skipping -- required inputs missing.")
else:

    # ------------------------------------------------------------------
    # Filter to banks only (exclude wallets / P2P / BNPL)
    # ------------------------------------------------------------------
    banks_only = competitor_txns[
        competitor_txns['competitor_category'].isin(BANK_CATEGORIES)
    ]

    _eco_txns = len(competitor_txns) - len(banks_only)
    _eco_pct = (_eco_txns / max(len(competitor_txns), 1)) * 100

    print(f"    Banks-only filter applied.")
    print(f"    Excluded {_eco_txns:,} wallet/P2P/BNPL transactions "
          f"({_eco_pct:.1f}% of all competitor txns).")

    if len(banks_only) == 0:
        print("    No bank-category competitor transactions. Skipping.")
    else:
        total_bank_trans    = len(banks_only)
        total_bank_accounts = banks_only['primary_account_num'].nunique()
        total_banks_found   = banks_only['competitor_match'].nunique()

        total_all_trans    = len(combined_df)
        total_all_accounts = combined_df['primary_account_num'].nunique()

        pct_trans = (total_bank_trans / total_all_trans * 100) if total_all_trans else 0
        pct_accounts = (total_bank_accounts / total_all_accounts * 100) if total_all_accounts else 0
        avg_txn_per_account = (total_bank_trans / total_bank_accounts) if total_bank_accounts else 0

        kpis = [
            (f"{pct_accounts:.1f}%",   "of Accounts\nUsing Competitor Banks", GEN_COLORS['accent']),
            (f"{pct_trans:.1f}%",      "of Transactions\nGo to Competitor Banks", GEN_COLORS['info']),
            (f"{total_banks_found}",   "Bank Competitors\nDetected",              GEN_COLORS['warning']),
            (f"{avg_txn_per_account:.1f}", "Avg Transactions\nper Account",       GEN_COLORS['success']),
        ]

        fig, axes = plt.subplots(1, 4, figsize=(22, 6))
        fig.patch.set_facecolor('#FFFFFF')

        for ax, (value, label, color) in zip(axes, kpis):
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            card = FancyBboxPatch(
                (0.03, 0.05), 0.94, 0.90,
                boxstyle="round,pad=0.05",
                facecolor=color, alpha=0.08,
                edgecolor=color, linewidth=2.8,
            )
            ax.add_patch(card)
            ax.text(0.5, 0.62, value, transform=ax.transAxes,
                    fontsize=54, fontweight='bold', color=color,
                    ha='center', va='center')
            ax.text(0.5, 0.20, label, transform=ax.transAxes,
                    fontsize=17, fontweight='bold', color=GEN_COLORS['dark_text'],
                    ha='center', va='center', linespacing=1.4)

        fig.suptitle("Competitive Exposure — Banks Only",
                     fontsize=30, fontweight='bold',
                     color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
        fig.text(0.5, GEN_SUBTITLE_Y,
                 f"Excludes wallets / P2P / BNPL ({_eco_txns:,} txns, {_eco_pct:.1f}% of competitor activity)",
                 ha='center', fontsize=14, color=GEN_COLORS['muted'], style='italic')

        plt.tight_layout()
        plt.savefig('competition_60_banks_only_kpi.png', dpi=160, bbox_inches='tight')
        plt.show()
        plt.close(fig)

        if pct_accounts < 20:
            print(f"\n    OPPORTUNITY: Only {pct_accounts:.1f}% of accounts show BANK competitor activity.")
            print("    Bank-to-bank competitive exposure is limited -- defend these relationships.")
        elif pct_accounts > 40:
            print(f"\n    WARNING: {pct_accounts:.1f}% of accounts show BANK competitor activity.")
            print("    Significant bank-to-bank overlap -- targeted retention strategy needed.")
