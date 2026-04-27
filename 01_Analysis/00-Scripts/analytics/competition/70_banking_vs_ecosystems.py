# ===========================================================================
# BANKING vs DIGITAL ECOSYSTEMS
# ===========================================================================
# Head-to-head comparison of traditional banking (banks + BNPL) against
# digital payment ecosystems (wallets + P2P, i.e. Cash App, Venmo, Zelle,
# PayPal, Apple Pay). Built specifically to expose clients whose members
# are deep inside the ecosystem world even if bank-side exposure looks
# moderate.
#
# Panels:
#   1. Headline KPI strip: top ecosystem reach vs top bank reach vs
#      combined ecosystem reach, with a Cash App callout row if present.
#   2. Dual-side bar chart: traditional banking (banks + BNPL) on left,
#      digital ecosystems (wallets + P2P) on right, top 8 each by reach %.
#      Cash App gets a distinctive highlight treatment.
#   3. Monthly trend: ecosystem unique-accts vs bank+BNPL unique-accts per
#      month, so the trajectory is visible.
#
# Assumes competitor_txns, combined_df, GEN_COLORS are in globals.
# ===========================================================================

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

BANK_BNPL_EXCLUDE = ('wallets', 'p2p')
ECO_CATS = ('wallets', 'p2p')

bank_side = competitor_txns[~competitor_txns['competitor_category'].isin(BANK_BNPL_EXCLUDE)].copy()
eco_side = competitor_txns[competitor_txns['competitor_category'].isin(ECO_CATS)].copy()

total_all_accts = combined_df['primary_account_num'].nunique()
total_all_trans = len(combined_df)

bank_accts = bank_side['primary_account_num'].nunique()
eco_accts = eco_side['primary_account_num'].nunique()
bank_reach = bank_accts / max(total_all_accts, 1) * 100
eco_reach = eco_accts / max(total_all_accts, 1) * 100

# Spotlight competitor: Cash App first, else top ecosystem player
def _reach_by_competitor(frame):
    return (frame.groupby('competitor_match')['primary_account_num']
            .nunique().sort_values(ascending=False))

eco_reach_by_comp = _reach_by_competitor(eco_side)
bank_reach_by_comp = _reach_by_competitor(bank_side)

spotlight = None
for candidate in eco_reach_by_comp.index:
    if 'CASH APP' in str(candidate).upper() or 'SQUARE CASH' in str(candidate).upper():
        spotlight = candidate
        break
if spotlight is None and len(eco_reach_by_comp):
    spotlight = eco_reach_by_comp.index[0]

spotlight_accts = int(eco_reach_by_comp.get(spotlight, 0)) if spotlight else 0
spotlight_reach = spotlight_accts / max(total_all_accts, 1) * 100

top_bank = bank_reach_by_comp.index[0] if len(bank_reach_by_comp) else None
top_bank_accts = int(bank_reach_by_comp.iloc[0]) if len(bank_reach_by_comp) else 0
top_bank_reach = top_bank_accts / max(total_all_accts, 1) * 100

print("=" * 72)
print("BANKING vs DIGITAL ECOSYSTEMS")
print("=" * 72)
print(f"  Banks + BNPL reach      : {bank_reach:.1f}% of accounts ({bank_accts:,})")
print(f"  Ecosystem reach         : {eco_reach:.1f}% of accounts ({eco_accts:,})")
if spotlight:
    print(f"  Spotlight               : {spotlight} -- {spotlight_reach:.1f}% of accounts "
          f"({spotlight_accts:,})")
if top_bank and spotlight:
    ratio = spotlight_reach / max(top_bank_reach, 0.01)
    print(f"  {spotlight} vs {top_bank}: {ratio:.1f}x reach "
          f"({spotlight_reach:.1f}% vs {top_bank_reach:.1f}%)")
print()

# ---------------------------------------------------------------------------
# PANEL 1 -- Headline KPI strip
# ---------------------------------------------------------------------------
spot_label = f"{spotlight}" if spotlight else "Top Ecosystem"
kpis = [
    (f"{eco_reach:.1f}%",     "of Accounts Use\nDigital Ecosystems",        GEN_COLORS['accent']),
    (f"{bank_reach:.1f}%",    "of Accounts Use\nBanks + BNPL",              GEN_COLORS['info']),
    (f"{spotlight_reach:.1f}%", f"{spot_label}\nAccount Reach",             GEN_COLORS['warning']),
    (f"{top_bank_reach:.1f}%", f"{top_bank or 'Top Bank'}\nAccount Reach",  GEN_COLORS['success']),
]
fig1, axes1 = plt.subplots(1, 4, figsize=(22, 5.8))
fig1.patch.set_facecolor('#FFFFFF')
for ax, (value, label, color) in zip(axes1, kpis):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.add_patch(FancyBboxPatch(
        (0.03, 0.05), 0.94, 0.90, boxstyle="round,pad=0.05",
        facecolor=color, alpha=0.08, edgecolor=color, linewidth=2.8))
    ax.text(0.5, 0.62, value, transform=ax.transAxes,
            fontsize=48, fontweight='bold', color=color, ha='center', va='center')
    ax.text(0.5, 0.20, label, transform=ax.transAxes,
            fontsize=14, fontweight='bold', color=GEN_COLORS['dark_text'],
            ha='center', va='center', linespacing=1.4)
fig1.suptitle("Banking vs Digital Ecosystems — Account Reach Head-to-Head",
              fontsize=26, fontweight='bold',
              color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
sub = f"Ecosystem = wallets + P2P.  Banks + BNPL includes Affirm/Klarna/Afterpay."
if spotlight and top_bank:
    ratio = spotlight_reach / max(top_bank_reach, 0.01)
    sub += f"  {spotlight} reaches {ratio:.1f}x as many accounts as {top_bank}."
fig1.text(0.5, 0.96, sub, ha='center', fontsize=12,
          color=GEN_COLORS['muted'], style='italic')
plt.tight_layout()
plt.savefig('competition_70_headline_kpi.png', dpi=160, bbox_inches='tight')
plt.show(); plt.close(fig1)

# ---------------------------------------------------------------------------
# PANEL 2 -- Side-by-side bar race (top 8 traditional vs top 8 ecosystem)
# ---------------------------------------------------------------------------
N = 8
bank_top = bank_reach_by_comp.head(N).sort_values()
eco_top = eco_reach_by_comp.head(N).sort_values()

def _bar_panel(ax, series, title, base_color, highlight_name=None):
    yy = np.arange(len(series))
    reaches = [v / max(total_all_accts, 1) * 100 for v in series.values]
    bars = ax.barh(yy, reaches, color=base_color, alpha=0.85,
                   edgecolor='white', linewidth=1.4)
    if highlight_name is not None:
        for bar, name in zip(bars, series.index):
            if str(name) == str(highlight_name):
                bar.set_edgecolor(GEN_COLORS['dark_text'])
                bar.set_linewidth(3.2)
                bar.set_alpha(1.0)
    ax.set_yticks(yy)
    labels = []
    for n in series.index:
        s = str(n)
        labels.append(s[:30] + '..' if len(s) > 32 else s)
    ax.set_yticklabels(labels, fontsize=13, fontweight='bold')
    for i, (reach, v) in enumerate(zip(reaches, series.values)):
        label = f"{reach:.1f}%  ({int(v):,} accts)"
        ax.text(reach + max(reaches) * 0.01, i, label,
                va='center', ha='left', fontsize=11,
                fontweight='bold', color=GEN_COLORS['dark_text'])
    ax.set_title(title, fontsize=20, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=12, loc='left')
    ax.set_xlabel('Account reach (% of all accounts)',
                  fontsize=12, fontweight='bold')
    ax.set_xlim(0, max(reaches) * 1.28 if reaches else 1)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis='x', labelsize=11)

fig2, axes2 = plt.subplots(1, 2, figsize=(22, 9))
_bar_panel(axes2[0], bank_top, "Traditional Banking (Banks + BNPL)",
           GEN_COLORS['info'])
_bar_panel(axes2[1], eco_top, "Digital Ecosystems (Wallets + P2P)",
           GEN_COLORS['accent'], highlight_name=spotlight)

fig2.suptitle("Top 8 Competitors Each Side — Sorted by Account Reach",
              fontsize=24, fontweight='bold',
              color=GEN_COLORS['dark_text'], y=1.02)
if spotlight:
    fig2.text(0.5, -0.02,
              f"{spotlight} highlighted (thick border). "
              f"Reach = unique accounts using this competitor / all accounts in portfolio.",
              ha='center', fontsize=12, color=GEN_COLORS['muted'], style='italic')
plt.tight_layout()
plt.savefig('competition_70_side_by_side.png', dpi=160, bbox_inches='tight')
plt.show(); plt.close(fig2)

# ---------------------------------------------------------------------------
# PANEL 3 -- Monthly trajectory (ecosystem vs bank+BNPL)
# ---------------------------------------------------------------------------
if 'year_month' in competitor_txns.columns and competitor_txns['year_month'].notna().any():
    bank_m = (bank_side.groupby('year_month')['primary_account_num']
              .nunique().rename('bank_bnpl_accts'))
    eco_m = (eco_side.groupby('year_month')['primary_account_num']
             .nunique().rename('ecosystem_accts'))
    spot_m = None
    if spotlight is not None:
        spot_m = (eco_side[eco_side['competitor_match'] == spotlight]
                  .groupby('year_month')['primary_account_num']
                  .nunique().rename(f'{spotlight}_accts'))

    all_months = sorted(set(bank_m.index) | set(eco_m.index))
    bank_m = bank_m.reindex(all_months, fill_value=0)
    eco_m = eco_m.reindex(all_months, fill_value=0)
    if spot_m is not None:
        spot_m = spot_m.reindex(all_months, fill_value=0)

    if len(all_months) >= 2:
        fig3, ax3 = plt.subplots(figsize=(20, 7))
        x = np.arange(len(all_months))
        ax3.plot(x, bank_m.values, marker='o', color=GEN_COLORS['info'],
                 linewidth=3, markersize=9, label='Banks + BNPL (unique accts)')
        ax3.plot(x, eco_m.values, marker='s', color=GEN_COLORS['accent'],
                 linewidth=3, markersize=9, label='Ecosystems (unique accts)')
        if spot_m is not None:
            ax3.plot(x, spot_m.values, marker='D', color=GEN_COLORS['warning'],
                     linewidth=2.5, markersize=8, linestyle='--',
                     label=f'{spotlight} only (unique accts)')
        ax3.set_xticks(x)
        ax3.set_xticklabels([str(m) for m in all_months],
                            rotation=45, ha='right', fontsize=11)
        ax3.set_ylabel('Unique accounts active in month',
                       fontsize=14, fontweight='bold',
                       color=GEN_COLORS['dark_text'])
        ax3.set_title("Monthly Account Activity — Banking vs Ecosystems",
                      fontsize=22, fontweight='bold',
                      color=GEN_COLORS['dark_text'], pad=14, loc='left')
        ax3.legend(frameon=False, fontsize=13, loc='best')
        for s in ('top', 'right'):
            ax3.spines[s].set_visible(False)
        ax3.tick_params(axis='y', labelsize=11)
        ax3.grid(axis='y', color=GEN_COLORS.get('grid', '#DDDDDD'),
                 linewidth=0.6, alpha=0.6)
        ax3.set_axisbelow(True)

        # Trailing callout
        if spot_m is not None and len(spot_m) >= 2:
            last = spot_m.iloc[-1]
            ax3.annotate(f"{spotlight}\n{int(last):,} accts\nmost recent month",
                         xy=(x[-1], last),
                         xytext=(x[-1] - len(all_months) * 0.15, last * 1.25),
                         fontsize=11, fontweight='bold',
                         color=GEN_COLORS['warning'],
                         arrowprops=dict(arrowstyle='->',
                                         color=GEN_COLORS['warning'],
                                         lw=1.5))
        plt.tight_layout()
        plt.savefig('competition_70_monthly_trajectory.png', dpi=160, bbox_inches='tight')
        plt.show(); plt.close(fig3)
    else:
        print("    (Not enough months for a trajectory -- skipped panel 3.)")
else:
    print("    (competitor_txns has no year_month -- skipped panel 3.)")

# ---------------------------------------------------------------------------
# Takeaway line
# ---------------------------------------------------------------------------
print("TAKEAWAYS")
print("-" * 72)
if eco_reach > bank_reach:
    print(f"  Ecosystems outreach banks: {eco_reach:.1f}% vs {bank_reach:.1f}%.")
    print(f"  Members are doing money movement OUTSIDE the CU -- wallets + P2P")
    print(f"  don't build balances or loyalty with you.")
else:
    print(f"  Banks + BNPL still outreach ecosystems: {bank_reach:.1f}% vs {eco_reach:.1f}%.")

if spotlight and top_bank:
    ratio = spotlight_reach / max(top_bank_reach, 0.01)
    if ratio >= 1.5:
        print(f"  {spotlight} reaches {ratio:.1f}x as many accounts as {top_bank}.")
        print(f"  This is the #1 channel siphoning transaction volume from the CU.")
    elif ratio >= 1.0:
        print(f"  {spotlight} reaches parity with {top_bank} "
              f"({spotlight_reach:.1f}% vs {top_bank_reach:.1f}%).")
    else:
        print(f"  {top_bank} still outreaches {spotlight} "
              f"({top_bank_reach:.1f}% vs {spotlight_reach:.1f}%).")
