# ===========================================================================
# COMPETITION DEEP DIVE -- Banks + BNPL (Excludes Wallets + P2P)
# ===========================================================================
# Self-contained rich cell. Six panels:
#   1. Headline KPI strip          -- % accounts, % txns, # competitors, BNPL %
#   2. Category donut + stats      -- share by category (banks + BNPL)
#   3. Top 15 competitors          -- named ranking with reach % and spend
#   4. Monthly trend               -- transaction volume + unique accts over time
#   5. Category momentum           -- recent-3-mo vs previous-3-mo per category
#   6. Top growers / decliners     -- per-competitor momentum
#
# Uses observed=True on groupby because competitor_category is pd.Categorical.
#
# Assumes competitor_txns, combined_df, GEN_COLORS, CATEGORY_PALETTE are in globals.
# ===========================================================================

import matplotlib.pyplot as plt
import matplotlib.patheffects as _pe
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch
import numpy as np

EXCLUDE_CATS = ('wallets', 'p2p')
banks_bnpl_txns = competitor_txns[~competitor_txns['competitor_category'].isin(EXCLUDE_CATS)].copy()
excluded_txns = len(competitor_txns) - len(banks_bnpl_txns)
excluded_pct = excluded_txns / max(len(competitor_txns), 1) * 100
SCOPE_NOTE = (f"Excludes wallets + P2P ({excluded_txns:,} txns, "
              f"{excluded_pct:.1f}% of competitor activity). BNPL retained.")

total_all_trans = len(combined_df)
total_all_accts = combined_df['primary_account_num'].nunique()
total_scope_trans = len(banks_bnpl_txns)
total_scope_accts = banks_bnpl_txns['primary_account_num'].nunique()
total_scope_comps = banks_bnpl_txns['competitor_match'].nunique()

print("=" * 72)
print("COMPETITION DEEP DIVE — Banks + BNPL (Ex Wallets + P2P)")
print("=" * 72)
print(f"  Excluded wallets + P2P          : {excluded_txns:,} txns ({excluded_pct:.1f}%)")
print(f"  In-scope competitor txns        : {total_scope_trans:,}")
print(f"  In-scope competitor accounts    : {total_scope_accts:,} "
      f"({total_scope_accts / max(total_all_accts, 1) * 100:.1f}% of all accounts)")
print(f"  Distinct competitors detected   : {total_scope_comps}")
print()

# --- Panel 1: KPI strip --------------------------------------------------
pct_accts = total_scope_accts / total_all_accts * 100 if total_all_accts else 0
pct_txns = total_scope_trans / total_all_trans * 100 if total_all_trans else 0
bnpl = banks_bnpl_txns[banks_bnpl_txns['competitor_category'] == 'bnpl']
bnpl_pct_accts = bnpl['primary_account_num'].nunique() / max(total_all_accts, 1) * 100

kpis = [
    (f"{pct_accts:.1f}%",      "of Accounts\nUsing Bank + BNPL Competitors", GEN_COLORS['accent']),
    (f"{pct_txns:.1f}%",       "of Transactions\nto Bank + BNPL",            GEN_COLORS['info']),
    (f"{total_scope_comps}",   "Distinct Competitors\nDetected",             GEN_COLORS['warning']),
    (f"{bnpl_pct_accts:.1f}%", "of Accounts\nCarrying BNPL Balances",        GEN_COLORS['success']),
]
fig1, axes1 = plt.subplots(1, 4, figsize=(22, 5.8))
fig1.patch.set_facecolor('#FFFFFF')
for ax, (value, label, color) in zip(axes1, kpis):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.add_patch(FancyBboxPatch(
        (0.03, 0.05), 0.94, 0.90, boxstyle="round,pad=0.05",
        facecolor=color, alpha=0.08, edgecolor=color, linewidth=2.8))
    ax.text(0.5, 0.62, value, transform=ax.transAxes,
            fontsize=52, fontweight='bold', color=color, ha='center', va='center')
    ax.text(0.5, 0.20, label, transform=ax.transAxes,
            fontsize=16, fontweight='bold', color=GEN_COLORS['dark_text'],
            ha='center', va='center', linespacing=1.4)
fig1.suptitle("Competitive Exposure — Banks + BNPL",
              fontsize=28, fontweight='bold',
              color=GEN_COLORS['dark_text'], y=1.03)
fig1.text(0.5, 0.96, SCOPE_NOTE,
          ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')
plt.tight_layout()
plt.savefig('competition_65_panel1_kpi.png', dpi=160, bbox_inches='tight')
plt.show(); plt.close(fig1)

# --- Panel 2: Category donut + stats -------------------------------------
cat = (banks_bnpl_txns.groupby('competitor_category', observed=True)
       .agg(txns=('amount', 'count'),
            accts=('primary_account_num', 'nunique'),
            comps=('competitor_match', 'nunique'),
            spend=('amount', 'sum'))
       .sort_values('txns', ascending=False))
cat.index = cat.index.str.replace('_', ' ').str.title()

fig2 = plt.figure(figsize=(20, 9))
gs2 = GridSpec(1, 2, width_ratios=[1, 1.1], wspace=0.04)

ax_d = fig2.add_subplot(gs2[0])
colors = [CATEGORY_PALETTE.get(c, GEN_COLORS['muted']) for c in cat.index]
wedges, _, autos = ax_d.pie(
    cat['txns'], labels=None, autopct='%1.0f%%', colors=colors,
    startangle=90, pctdistance=0.78,
    wedgeprops=dict(width=0.45, edgecolor='white', linewidth=3))
for t in autos:
    t.set_fontsize(18); t.set_fontweight('bold'); t.set_color('white')
    t.set_path_effects([_pe.withStroke(linewidth=2, foreground='#333333')])
ax_d.text(0, 0, f"{int(cat['txns'].sum()):,}\nCompetitor\nTxns",
          ha='center', va='center', fontsize=19, fontweight='bold',
          color=GEN_COLORS['dark_text'])
ax_d.set_title("Share by Category", fontsize=22, fontweight='bold',
               color=GEN_COLORS['dark_text'], pad=18)

ax_t = fig2.add_subplot(gs2[1]); ax_t.axis('off')
y0 = 0.95
step = 0.78 / max(len(cat), 1)
for h, x in [('Category', 0.02), ('Txns', 0.48), ('Accts', 0.64),
             ('$ Spend', 0.76), ('# Comp', 0.92)]:
    ax_t.text(x, y0 + 0.02, h, fontsize=14, fontweight='bold',
              color=GEN_COLORS['muted'], transform=ax_t.transAxes)
for i, (c_name, row) in enumerate(cat.iterrows()):
    yy = y0 - (i + 1) * step
    color = CATEGORY_PALETTE.get(c_name, GEN_COLORS['muted'])
    ax_t.add_patch(plt.Rectangle((0.0, yy - 0.02), 0.018, 0.03,
                                 facecolor=color, transform=ax_t.transAxes, clip_on=False))
    ax_t.text(0.02, yy, c_name, fontsize=14, fontweight='bold',
              color=GEN_COLORS['dark_text'], transform=ax_t.transAxes, va='center')
    ax_t.text(0.48, yy, f"{int(row['txns']):,}", fontsize=14, fontweight='bold',
              color=color, transform=ax_t.transAxes, va='center')
    ax_t.text(0.64, yy, f"{int(row['accts']):,}", fontsize=13,
              color=GEN_COLORS['dark_text'], transform=ax_t.transAxes, va='center')
    ax_t.text(0.76, yy, f"${row['spend']:,.0f}", fontsize=13,
              color=GEN_COLORS['dark_text'], transform=ax_t.transAxes, va='center')
    ax_t.text(0.92, yy, f"{int(row['comps'])}", fontsize=13,
              color=GEN_COLORS['dark_text'], transform=ax_t.transAxes, va='center')

fig2.suptitle("Category Breakdown — Banks + BNPL",
              fontsize=26, fontweight='bold',
              color=GEN_COLORS['dark_text'], y=1.01)
fig2.text(0.5, 0.97, SCOPE_NOTE,
          ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')
plt.tight_layout()
plt.savefig('competition_65_panel2_category.png', dpi=160, bbox_inches='tight')
plt.show(); plt.close(fig2)

# --- Panel 3: Top 15 competitors -----------------------------------------
top15 = (banks_bnpl_txns.groupby('competitor_match')
         .agg(txns=('amount', 'count'),
              accts=('primary_account_num', 'nunique'),
              spend=('amount', 'sum'),
              category=('competitor_category', 'first'))
         .sort_values('txns', ascending=False).head(15))
top15['reach'] = top15['accts'] / max(total_scope_accts, 1) * 100

fig3, ax3 = plt.subplots(figsize=(22, 10))
fig3.patch.set_facecolor('#FFFFFF')
ax3.axis('off'); ax3.set_xlim(0, 22); ax3.set_ylim(-0.6, len(top15) + 1.8)
ax3.invert_yaxis()
ax3.text(0.3, 0, "Top 15 Competitors — by Transaction Volume",
         fontsize=26, fontweight='bold', color=GEN_COLORS['dark_text'])
ax3.text(0.3, 0.7, SCOPE_NOTE,
         fontsize=13, color=GEN_COLORS['muted'], style='italic')
headers = ['Rank', 'Competitor', 'Transactions', 'Accounts', 'Reach %',
           'Total Spend', 'Category']
h_x = [0.3, 1.6, 8.5, 11.0, 13.4, 15.5, 18.2]
for hx, h in zip(h_x, headers):
    ax3.text(hx, 1.8, h, fontsize=13, fontweight='bold', color=GEN_COLORS['muted'])
ax3.plot([0.3, 21.5], [2.1, 2.1], color=GEN_COLORS['grid'], linewidth=1.5)

for i, (m_name, row) in enumerate(top15.iterrows()):
    y = i + 2.6
    cat_label = row['category'].replace('_', ' ').title()
    cat_color = CATEGORY_PALETTE.get(cat_label, GEN_COLORS['muted'])
    name = str(m_name)[:36] + '..' if len(str(m_name)) > 38 else str(m_name)
    ax3.text(h_x[0] + 0.3, y, f"{i + 1}", fontsize=16, fontweight='bold',
             color=GEN_COLORS['dark_text'], ha='center')
    ax3.text(h_x[1], y, name, fontsize=14, fontweight='bold',
             color=GEN_COLORS['dark_text'])
    ax3.text(h_x[2], y, f"{int(row['txns']):,}", fontsize=14,
             fontweight='bold', color=GEN_COLORS['accent'])
    ax3.text(h_x[3], y, f"{int(row['accts']):,}", fontsize=13,
             color=GEN_COLORS['dark_text'])
    ax3.text(h_x[4], y, f"{row['reach']:.1f}%", fontsize=13,
             fontweight='bold', color=GEN_COLORS['info'])
    ax3.text(h_x[5], y, f"${row['spend']:,.0f}", fontsize=13,
             color=GEN_COLORS['dark_text'])
    badge = FancyBboxPatch(
        (h_x[6] - 0.1, y - 0.28), max(len(cat_label) * 0.19 + 0.4, 2.2), 0.55,
        boxstyle="round,pad=0.08", facecolor=cat_color,
        alpha=0.12, edgecolor=cat_color, linewidth=1.2)
    ax3.add_patch(badge)
    ax3.text(h_x[6] + 0.1, y, cat_label, fontsize=12,
             fontweight='bold', color=cat_color)
    if i < len(top15) - 1:
        ax3.plot([0.3, 21.5], [y + 0.42, y + 0.42],
                 color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
plt.tight_layout()
plt.savefig('competition_65_panel3_top15.png', dpi=160, bbox_inches='tight')
plt.show(); plt.close(fig3)

# --- Panel 4: Monthly trend ----------------------------------------------
if 'year_month' in banks_bnpl_txns.columns and banks_bnpl_txns['year_month'].notna().any():
    monthly = (banks_bnpl_txns.groupby('year_month')
               .agg(txns=('amount', 'count'),
                    accts=('primary_account_num', 'nunique'),
                    spend=('amount', 'sum'))
               .sort_index())
    if len(monthly) >= 2:
        fig4, ax4 = plt.subplots(figsize=(20, 7))
        x = np.arange(len(monthly))
        ax4.bar(x, monthly['txns'], color=GEN_COLORS['info'], alpha=0.35,
                edgecolor='white', label='Transactions')
        ax4b = ax4.twinx()
        ax4b.plot(x, monthly['accts'], marker='o', color=GEN_COLORS['accent'],
                  linewidth=2.8, markersize=9, label='Unique accounts')
        ax4.set_xticks(x)
        ax4.set_xticklabels(monthly.index.astype(str), rotation=45, ha='right', fontsize=12)
        ax4.set_ylabel('Competitor transactions (Banks + BNPL)',
                       fontsize=14, fontweight='bold', color=GEN_COLORS['info'])
        ax4b.set_ylabel('Unique accounts with Banks + BNPL activity',
                        fontsize=14, fontweight='bold', color=GEN_COLORS['accent'])
        ax4.tick_params(axis='y', colors=GEN_COLORS['info'], labelsize=12)
        ax4b.tick_params(axis='y', colors=GEN_COLORS['accent'], labelsize=12)
        ax4.spines['top'].set_visible(False); ax4b.spines['top'].set_visible(False)
        ax4.set_title("Monthly Competitor Activity — Banks + BNPL",
                      fontsize=22, fontweight='bold',
                      color=GEN_COLORS['dark_text'], pad=14, loc='left')
        fig4.text(0.5, -0.02, SCOPE_NOTE, ha='center',
                  fontsize=13, color=GEN_COLORS['muted'], style='italic')
        h1, l1 = ax4.get_legend_handles_labels()
        h2, l2 = ax4b.get_legend_handles_labels()
        ax4.legend(h1 + h2, l1 + l2, frameon=False, fontsize=13, loc='upper left')
        plt.tight_layout()
        plt.savefig('competition_65_panel4_monthly.png', dpi=160, bbox_inches='tight')
        plt.show(); plt.close(fig4)
    else:
        print("    (Not enough months for a trend -- skipped panel 4.)")
else:
    print("    (banks_bnpl_txns has no year_month column -- skipped panel 4.)")

# --- Panels 5 + 6: Momentum ----------------------------------------------
if 'year_month' in banks_bnpl_txns.columns and banks_bnpl_txns['year_month'].notna().any():
    months_sorted = sorted(banks_bnpl_txns['year_month'].dropna().unique())
    if len(months_sorted) >= 6:
        recent_3 = months_sorted[-3:]
        prev_3 = months_sorted[-6:-3]

        def _acct_counts_in(frame, months, group_col, observed_flag=False):
            sub = frame[frame['year_month'].isin(months)]
            kwargs = {'observed': True} if observed_flag else {}
            return sub.groupby(group_col, **kwargs)['primary_account_num'].nunique()

        # Panel 5: category momentum (observed=True because Categorical)
        cat_recent = _acct_counts_in(banks_bnpl_txns, recent_3, 'competitor_category', True)
        cat_prev = _acct_counts_in(banks_bnpl_txns, prev_3, 'competitor_category', True)
        cat_idx = sorted(set(cat_recent.index) | set(cat_prev.index))
        cat_recent = cat_recent.reindex(cat_idx, fill_value=0)
        cat_prev = cat_prev.reindex(cat_idx, fill_value=0)
        cat_delta = (cat_recent - cat_prev)
        cat_delta_pct = np.where(cat_prev > 0,
                                 (cat_recent - cat_prev) / cat_prev * 100, np.nan)
        pretty = [c.replace('_', ' ').title() for c in cat_idx]
        palette = [CATEGORY_PALETTE.get(p, GEN_COLORS['muted']) for p in pretty]

        fig5, ax5 = plt.subplots(figsize=(18, max(5, 0.65 * len(pretty))))
        order = np.argsort(cat_delta.values)[::-1]
        y = np.arange(len(order))
        bars = ax5.barh(y, cat_delta.values[order],
                        color=[palette[i] for i in order],
                        edgecolor='white', linewidth=1.2)
        ax5.set_yticks(y)
        ax5.set_yticklabels([pretty[i] for i in order], fontsize=14, fontweight='bold')
        ax5.axvline(0, color=GEN_COLORS['muted'], linewidth=1.2)
        for i, b in enumerate(bars):
            v = b.get_width()
            pct = cat_delta_pct[order[i]]
            lbl = (f"{int(v):+,} accts"
                   + (f"  ({pct:+.1f}%)" if not np.isnan(pct) else ''))
            xoff = max(abs(v) * 0.02, 1)
            ax5.text(v + (xoff if v >= 0 else -xoff), i, lbl,
                     va='center', ha='left' if v >= 0 else 'right',
                     fontsize=12, fontweight='bold',
                     color=GEN_COLORS['dark_text'])
        ax5.set_xlabel('Net change in unique accounts (recent 3 − previous 3 months)',
                       fontsize=13, fontweight='bold')
        ax5.set_title("Category Momentum — Banks + BNPL",
                      fontsize=22, fontweight='bold',
                      color=GEN_COLORS['dark_text'], pad=14, loc='left')
        for s in ('top', 'right'):
            ax5.spines[s].set_visible(False)
        ax5.tick_params(axis='x', labelsize=12)
        fig5.text(0.5, -0.02,
                  f"Recent: {', '.join(str(m) for m in recent_3)}  |  "
                  f"Previous: {', '.join(str(m) for m in prev_3)}.  {SCOPE_NOTE}",
                  ha='center', fontsize=12, color=GEN_COLORS['muted'], style='italic')
        plt.tight_layout()
        plt.savefig('competition_65_panel5_cat_momentum.png', dpi=160, bbox_inches='tight')
        plt.show(); plt.close(fig5)

        # Panel 6: per-competitor growers + decliners
        bank_recent = _acct_counts_in(banks_bnpl_txns, recent_3, 'competitor_match')
        bank_prev = _acct_counts_in(banks_bnpl_txns, prev_3, 'competitor_match')
        bank_idx = sorted(set(bank_recent.index) | set(bank_prev.index))
        bank_recent = bank_recent.reindex(bank_idx, fill_value=0)
        bank_prev = bank_prev.reindex(bank_idx, fill_value=0)
        bank_delta = bank_recent - bank_prev
        min_floor = 10
        eligible = (bank_recent + bank_prev) >= min_floor
        bank_delta = bank_delta[eligible]
        growers = bank_delta.sort_values(ascending=False).head(10)
        decliners = bank_delta.sort_values().head(10)

        fig6, axes6 = plt.subplots(1, 2, figsize=(22, 8))
        for ax6, series, title, base_color in [
            (axes6[0], growers.sort_values(),
             "Top 10 Growers (recent vs previous 3 mo)", GEN_COLORS['warning']),
            (axes6[1], decliners,
             "Top 10 Decliners (recent vs previous 3 mo)", GEN_COLORS['success']),
        ]:
            yy = np.arange(len(series))
            ax6.barh(yy, series.values, color=base_color, alpha=0.85,
                     edgecolor='white', linewidth=1.2)
            ax6.set_yticks(yy)
            ax6.set_yticklabels([str(n)[:28] for n in series.index],
                                fontsize=12, fontweight='bold')
            ax6.axvline(0, color=GEN_COLORS['muted'], linewidth=1.0)
            for i, v in enumerate(series.values):
                ax6.text(v + (1 if v >= 0 else -1), i, f"{int(v):+,}",
                         va='center', ha='left' if v >= 0 else 'right',
                         fontsize=11, fontweight='bold', color=GEN_COLORS['dark_text'])
            ax6.set_title(title, fontsize=18, fontweight='bold',
                          color=GEN_COLORS['dark_text'], pad=10, loc='left')
            ax6.set_xlabel("Net account change")
            for s in ('top', 'right'):
                ax6.spines[s].set_visible(False)

        fig6.suptitle("Per-Competitor Momentum — Banks + BNPL",
                      fontsize=24, fontweight='bold',
                      color=GEN_COLORS['dark_text'], y=1.02)
        fig6.text(0.5, -0.02,
                  f"Growers = more accounts recently vs previous 3 mo (red = attention).  "
                  f"Decliners = losing accounts (green = opportunity).  "
                  f"Min floor: {min_floor} accts across both windows.  {SCOPE_NOTE}",
                  ha='center', fontsize=12, color=GEN_COLORS['muted'], style='italic')
        plt.tight_layout()
        plt.savefig('competition_65_panel6_comp_momentum.png', dpi=160, bbox_inches='tight')
        plt.show(); plt.close(fig6)

        # --- Takeaways ---
        print()
        print("TAKEAWAYS")
        print("-" * 72)
        top_grower = growers.index[0] if len(growers) else None
        top_decliner = decliners.index[0] if len(decliners) else None
        if top_grower and growers.iloc[0] > 0:
            print(f"  Fastest-growing competitor: {top_grower} "
                  f"(+{int(growers.iloc[0])} accts in recent 3 mo)")
        if top_decliner and decliners.iloc[0] < 0:
            print(f"  Fastest-declining         : {top_decliner} "
                  f"({int(decliners.iloc[0])} accts in recent 3 mo)")
        biggest_cat_delta = cat_delta.idxmax() if len(cat_delta) else None
        if biggest_cat_delta is not None:
            pretty_b = str(biggest_cat_delta).replace('_', ' ').title()
            print(f"  Category gaining most     : {pretty_b} "
                  f"(+{int(cat_delta.max())} accts)")
        print(f"  Top competitor by volume  : {top15.index[0]} "
              f"({int(top15.iloc[0]['txns']):,} txns, {top15.iloc[0]['reach']:.1f}% reach)")
    else:
        print("    (Need at least 6 months of data for momentum -- skipped panels 5/6.)")
else:
    print("    (banks_bnpl_txns has no year_month column -- skipped panels 5/6.)")
