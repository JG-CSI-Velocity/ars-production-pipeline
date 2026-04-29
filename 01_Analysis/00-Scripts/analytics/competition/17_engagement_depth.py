# ===========================================================================
# CELL 17: COMPETITOR ENGAGEMENT DEPTH
# ===========================================================================
# For members using each competitor: what share of their total transactions
# goes to that competitor? Segments users into Heavy / Moderate / Light.
# Uses transaction counts only (no dollar figures).

# --- False positive exclusion: food, retail, non-financial merchants ---
FALSE_POSITIVE_KEYWORDS = [
    'DONUT', 'CREAMERY', 'BOWL', 'PIZZA', 'TACO', 'BURGER', 'GRILL',
    'CAFE', 'COFFEE', 'BAKERY', 'RESTAURANT', 'KITCHEN', 'DINER',
    'BAR ', 'PUB ', 'BREWERY', 'WINERY', 'TAQUERIA', 'SUSHI',
    'ICE CREAM', 'YOGURT', 'SMOOTHIE', 'JUICE', 'TEA ', 'BOBA',
    'MARKET', 'GROCERY', 'FARM', 'FLORIST', 'SALON', 'SPA ',
    'AUTO REPAIR', 'TOWING', 'BODY SHOP', 'AUTO PARTS', 'AUTOZONE',
    'CLEANERS', 'LAUNDRY', 'PLUMBING', 'ELECTRIC', 'ROOFING',
]

def is_false_positive(merchant_name):
    name_upper = str(merchant_name).upper()
    return any(kw in name_upper for kw in FALSE_POSITIVE_KEYWORDS)

# --- Pre-compute total txn count per account ONCE ---
total_txn_by_acct = combined_df.groupby('primary_account_num')['amount'].count()

# --- Build competitor share data (vectorized, no per-row loop) ---
comp_frames = []
for competitor, competitor_trans in all_competitor_data.items():
    # Skip false positive merchants
    if is_false_positive(competitor):
        continue

    category = competitor_trans['competitor_category'].iloc[0]
    norm_name = normalize_competitor_name(competitor)

    comp_txn = competitor_trans.groupby('primary_account_num')['amount'].count()
    share_df = pd.DataFrame({
        'competitor': norm_name,
        'category': clean_category(category),
        'comp_txns': comp_txn,
        'total_txns': total_txn_by_acct.reindex(comp_txn.index),
    })
    share_df['share_pct'] = (share_df['comp_txns'] / share_df['total_txns'] * 100)
    share_df = share_df.dropna(subset=['share_pct'])
    comp_frames.append(share_df)

eng_acct_df = pd.concat(comp_frames, ignore_index=False)
eng_acct_df.index.name = 'account'

# Roll up normalized names
eng_summary = eng_acct_df.groupby(['competitor', 'category']).agg(
    accounts=('comp_txns', 'count'),
    avg_share=('share_pct', 'mean'),
    heavy=('share_pct', lambda x: (x >= 50).sum()),
    moderate=('share_pct', lambda x: ((x >= 20) & (x < 50)).sum()),
    light=('share_pct', lambda x: (x < 20).sum()),
).reset_index()

eng_summary['heavy_pct'] = eng_summary['heavy'] / eng_summary['accounts'] * 100
eng_summary['moderate_pct'] = eng_summary['moderate'] / eng_summary['accounts'] * 100
eng_summary['light_pct'] = eng_summary['light'] / eng_summary['accounts'] * 100

# Top 12 by account count
eng_top = eng_summary.sort_values('accounts', ascending=False).head(12)
eng_top = eng_top.sort_values('avg_share', ascending=True)

# --- Conference visual: Engagement Depth Distribution ---
fig, ax = plt.subplots(figsize=(8, 7))

y_pos = range(len(eng_top))

# Stacked bars: Light (left), Moderate (middle), Heavy (right)
bars_light = ax.barh(y_pos, eng_top['light_pct'],
                     color=GEN_COLORS['success'], alpha=0.7,
                     edgecolor='white', linewidth=1.5, height=0.65,
                     label='Light (<20% of txns)', zorder=3)

bars_mod = ax.barh(y_pos, eng_top['moderate_pct'],
                   left=eng_top['light_pct'],
                   color=GEN_COLORS['warning'],
                   edgecolor='white', linewidth=1.5, height=0.65,
                   label='Moderate (20-50%)', zorder=3)

bars_heavy = ax.barh(y_pos, eng_top['heavy_pct'],
                     left=eng_top['light_pct'].values + eng_top['moderate_pct'].values,
                     color=GEN_COLORS['accent'],
                     edgecolor='white', linewidth=1.5, height=0.65,
                     label='Heavy (50%+ of txns)', zorder=3)

# Segment count labels inside bars (only if segment > 12%)
for i, (_, row) in enumerate(eng_top.iterrows()):
    left = 0
    for seg_pct, seg_count, color in [
        (row['light_pct'], int(row['light']), 'white'),
        (row['moderate_pct'], int(row['moderate']), 'white'),
        (row['heavy_pct'], int(row['heavy']), 'white'),
    ]:
        if seg_pct > 12:
            ax.text(left + seg_pct / 2, i, f"{seg_count:,}",
                    ha='center', va='center', fontsize=12, fontweight='bold',
                    color=color,
                    path_effects=[pe.withStroke(linewidth=2, foreground='#333333')])
        left += seg_pct

# Account count annotation on right
for i, (_, row) in enumerate(eng_top.iterrows()):
    ax.text(101, i, f"{int(row['accounts']):,} accts",
            fontsize=12, fontweight='bold', color=GEN_COLORS['dark_text'], va='center')

# Y-axis: competitor names with category color dot
labels = []
for _, row in eng_top.iterrows():
    labels.append(row['competitor'])

ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=12, fontweight='bold')
ax.set_xlabel('Share of Member Transactions (%)', fontsize=13, fontweight='bold', labelpad=10)
ax.set_xlim(0, 118)
ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

gen_clean_axes(ax)
ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
ax.set_axisbelow(True)

ax.set_title('Competitor Engagement Depth',
             fontsize=20, fontweight='bold', color=GEN_COLORS['dark_text'], pad=20, loc='left')
ax.text(0.0, 0.97,
        "What share of member transactions go to each competitor?",
        transform=ax.transAxes, fontsize=11, color=GEN_COLORS['muted'], style='italic')

ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08),
          ncol=3, fontsize=11, frameon=False)

# Summary callout
total_heavy = eng_summary['heavy'].sum()
total_accts = eng_summary['accounts'].sum()
avg_share_all = eng_acct_df['share_pct'].mean()
ax.text(0.97, 0.05,
        f"Avg share: {avg_share_all:.1f}%\nHeavy users: {total_heavy:,} / {total_accts:,}",
        transform=ax.transAxes, fontsize=14, fontweight='bold',
        color=GEN_COLORS['accent'], ha='right', va='bottom',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                  edgecolor=GEN_COLORS['accent'], alpha=0.9))

plt.tight_layout()
plt.subplots_adjust(bottom=0.12)
plt.show()

# Store for export
competitor_engagement_data = eng_summary.sort_values('accounts', ascending=False)

print(f"\n    INSIGHT: Members using competitors send an average of {avg_share_all:.1f}% of their transactions there.")
if total_heavy > 0:
    top_heavy = eng_summary.sort_values('heavy', ascending=False).iloc[0]
    print(f"    HIGHEST RISK: {top_heavy['competitor']} has {int(top_heavy['heavy']):,} heavy users (50%+ of txns).")
    print(f"    ACTION: Prioritize retention for {total_heavy:,} heavy-engagement members across all competitors.")
