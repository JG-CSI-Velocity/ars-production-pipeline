# ===========================================================================
# RECENCY BY CATEGORY: Stacked Bar (Active / Cooling / Dormant / Lapsed)
# ===========================================================================

recency_data = []
for category, acct_df in all_financial_accounts.items():
    tier_counts = acct_df['Recency_Tier'].value_counts()
    recency_data.append({
        'category': category,
        'Active (0-30d)': tier_counts.get('Active (0-30d)', 0),
        'Cooling (30-90d)': tier_counts.get('Cooling (30-90d)', 0),
        'Dormant (90-365d)': tier_counts.get('Dormant (90-365d)', 0),
        'Lapsed (365d+)': tier_counts.get('Lapsed (365d+)', 0),
    })

rec_df = pd.DataFrame(recency_data)
rec_df['total'] = rec_df[['Active (0-30d)', 'Cooling (30-90d)', 'Dormant (90-365d)', 'Lapsed (365d+)']].sum(axis=1)
rec_df = rec_df.sort_values('total', ascending=True)

fig, ax = plt.subplots(figsize=(14, max(8, len(rec_df) * 0.55)))

tier_colors = {
    'Active (0-30d)':   GEN_COLORS['accent'],
    'Cooling (30-90d)': GEN_COLORS['warning'],
    'Dormant (90-365d)': GEN_COLORS['info'],
    'Lapsed (365d+)':   GEN_COLORS['grid'],
}

left = np.zeros(len(rec_df))
tier_order = ['Active (0-30d)', 'Cooling (30-90d)', 'Dormant (90-365d)', 'Lapsed (365d+)']

for tier in tier_order:
    values = rec_df[tier].values
    ax.barh(range(len(rec_df)), values, left=left,
            color=tier_colors[tier], edgecolor='white', linewidth=1,
            height=0.65, label=tier, zorder=3)

    # Label segments > 5% of total
    for i, (val, total) in enumerate(zip(values, rec_df['total'])):
        if val > 0 and (val / total) > 0.08:
            ax.text(left[i] + val / 2, i, f"{int(val):,}",
                    ha='center', va='center', fontsize=11,
                    fontweight='bold', color='white',
                    path_effects=[pe.withStroke(linewidth=2, foreground='#333333')])
    left += values

ax.set_yticks(range(len(rec_df)))
ax.set_yticklabels(rec_df['category'], fontsize=13, fontweight='bold')
ax.set_xlabel("Number of Accounts", fontsize=18, fontweight='bold', labelpad=12)
ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))

gen_clean_axes(ax)
ax.set_axisbelow(True)

ax.set_title("Leakage Recency by Category",
             fontsize=26, fontweight='bold', color=GEN_COLORS['dark_text'], pad=20, loc='left')
ax.text(0.0, 0.97, "Red = active leakage (last 30 days)  |  Gray = lapsed (365d+)",
        transform=ax.transAxes, fontsize=14, color=GEN_COLORS['muted'], style='italic')

ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08),
          ncol=4, fontsize=13, frameon=False)

plt.tight_layout()
plt.subplots_adjust(bottom=0.12)
plt.show()
