# ===========================================================================
# RECENCY HEATMAP: Where Is Leakage Active vs Dormant?
# ===========================================================================

recency_data = []
for category, acct_df in all_financial_accounts.items():
    for tier in ['Active (0-30d)', 'Cooling (30-90d)', 'Dormant (90-365d)', 'Lapsed (365d+)']:
        count = len(acct_df[acct_df['Recency_Tier'] == tier])
        recency_data.append({
            'category': category,
            'recency_tier': tier,
            'account_count': count
        })

rec_df = pd.DataFrame(recency_data)
pivot = rec_df.pivot(index='category', columns='recency_tier', values='account_count').fillna(0)

# Order columns logically
tier_order = ['Active (0-30d)', 'Cooling (30-90d)', 'Dormant (90-365d)', 'Lapsed (365d+)']
pivot = pivot[[t for t in tier_order if t in pivot.columns]]

# Order rows by total active accounts
pivot['_sort'] = pivot.get('Active (0-30d)', 0)
pivot = pivot.sort_values('_sort', ascending=False).drop(columns='_sort')

fig, ax = plt.subplots(figsize=(14, max(8, len(pivot) * 0.7)))

# Normalize each column (recency tier) independently so gradient is per date range
from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list('leakage', ['#FFFFFF', '#FF9F1C', '#E63946'])

pivot_normed = pivot.copy()
for col in pivot_normed.columns:
    col_max = pivot_normed[col].max()
    pivot_normed[col] = pivot_normed[col] / col_max if col_max > 0 else 0

# Draw heatmap with normalized colors but show raw counts as annotations
sns.heatmap(
    pivot_normed, annot=pivot.values, fmt=',.0f', cmap=cmap,
    linewidths=2, linecolor='white', vmin=0, vmax=1,
    cbar=False,
    annot_kws={'fontsize': 16, 'fontweight': 'bold'},
    ax=ax
)

ax.set_xlabel('', fontsize=1)
ax.set_ylabel('', fontsize=1)
# Move column headers to the top
ax.xaxis.tick_top()
ax.xaxis.set_label_position('top')
ax.set_xticklabels(ax.get_xticklabels(), fontsize=15, fontweight='bold', rotation=0)
ax.set_yticklabels(ax.get_yticklabels(), fontsize=14, fontweight='bold', rotation=0)

# Title and subtitle above chart via fig.text (absolute positioning)
fig.subplots_adjust(top=0.82, left=0.18, right=0.95, bottom=0.05)
fig.text(0.18, 0.94, "Leakage Recency Heatmap",
         fontsize=26, fontweight='bold', color=GEN_COLORS['dark_text'])
fig.text(0.18, 0.89, "Hot zones = active leakage you can still intercept",
         fontsize=15, color=GEN_COLORS['muted'], style='italic')

plt.show()

# Opportunity callout
total_active = pivot.get('Active (0-30d)', pd.Series([0])).sum()
total_cooling = pivot.get('Cooling (30-90d)', pd.Series([0])).sum()
print(f"\n    OPPORTUNITY: {int(total_active):,} accounts with activity in the last 30 days.")
print(f"    Another {int(total_cooling):,} cooling (30-90 days) -- still saveable with timely outreach.")
