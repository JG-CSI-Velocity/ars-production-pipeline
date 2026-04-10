# ===========================================================================
# HOURLY HEATMAP: When Do Members Transact? (Conference Edition)
# ===========================================================================
# Day-of-week x hour-of-day heatmap (overall). (14,8).

# Build pivot: day-of-week rows, hour columns
DOW_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

heatmap_data = demo_df.groupby(['txn_dow_name', 'txn_hour']).size().reset_index(name='count')
heatmap_pivot = heatmap_data.pivot(index='txn_dow_name', columns='txn_hour', values='count').fillna(0)

# Reorder rows
heatmap_pivot = heatmap_pivot.reindex(DOW_ORDER)

# Fill missing hour columns (0-23)
for h in range(24):
    if h not in heatmap_pivot.columns:
        heatmap_pivot[h] = 0
heatmap_pivot = heatmap_pivot[sorted(heatmap_pivot.columns)]

fig, ax = plt.subplots(figsize=(14, 8))

# Custom colormap: white -> warning -> accent
cmap = LinearSegmentedColormap.from_list('activity', ['#FFFFFF', '#FF9F1C', '#E63946'])

sns.heatmap(
    heatmap_pivot, annot=True, fmt=',.0f', cmap=cmap,
    linewidths=2, linecolor='white',
    cbar_kws={'label': 'Transaction Count', 'shrink': 0.6},
    annot_kws={'fontsize': 10, 'fontweight': 'bold'},
    ax=ax
)

ax.set_xlabel('Hour of Day', fontsize=16, fontweight='bold', labelpad=10)
ax.set_ylabel('', fontsize=1)
ax.set_xticklabels([f"{h}:00" for h in range(24)], fontsize=10, fontweight='bold', rotation=45)
ax.set_yticklabels(ax.get_yticklabels(), fontsize=14, fontweight='bold', rotation=0)

ax.set_title("When Do Members Transact?",
             fontsize=26, fontweight='bold',
             color=GEN_COLORS['dark_text'], pad=35, loc='left')
ax.text(0.0, 1.02, "Hot zones = peak transaction windows across the week",
        transform=ax.transAxes, fontsize=15,
        color=GEN_COLORS['muted'], style='italic')

plt.tight_layout()
plt.show()

# Callout
peak_hour = heatmap_pivot.sum(axis=0).idxmax()
peak_day = heatmap_pivot.sum(axis=1).idxmax()
print(f"\n    Peak hour: {peak_hour}:00")
print(f"    Peak day: {peak_day}")
