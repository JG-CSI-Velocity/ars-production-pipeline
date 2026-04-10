# ===========================================================================
# MERCHANT TOP 20: Horizontal Bar (Conference Edition)
# ===========================================================================
# Top 20 merchants by transaction count with concentration callout. (14,7).

fig, ax = plt.subplots(figsize=(14, 7))

plot_data = merch_top20.sort_values('txn_count', ascending=True).copy()
plot_data['short_name'] = plot_data['merchant_consolidated'].str[:30]

y_pos = range(len(plot_data))

# Gradient from info to primary
n = len(plot_data)
bar_colors = [
    f'#{int(69 + (i / max(n - 1, 1)) * (27 - 69)):02x}'
    f'{int(123 + (i / max(n - 1, 1)) * (42 - 123)):02x}'
    f'{int(157 + (i / max(n - 1, 1)) * (74 - 157)):02x}'
    for i in range(n)
]

ax.barh(y_pos, plot_data['txn_count'],
        color=bar_colors, edgecolor='white', linewidth=0.5, height=0.7)

ax.set_yticks(y_pos)
ax.set_yticklabels(plot_data['short_name'], fontsize=11, fontweight='bold')
ax.set_xlabel("Transaction Count", fontsize=16, fontweight='bold', labelpad=10)
ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))

# Value labels
for i, (_, row) in enumerate(plot_data.iterrows()):
    ax.text(row['txn_count'] + merch_top20['txn_count'].max() * 0.01, i,
            f"{row['txn_pct']:.1f}%", va='center', fontsize=10,
            fontweight='bold', color=GEN_COLORS['dark_text'])

gen_clean_axes(ax, keep_left=True, keep_bottom=True)
ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
ax.set_axisbelow(True)

# Concentration callout
ax.text(0.98, 0.05,
        f"Top 20 = {merch_top20['txn_pct'].sum():.1f}% of all transactions",
        transform=ax.transAxes, ha='right', va='bottom',
        fontsize=14, fontweight='bold', color=GEN_COLORS['accent'],
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                  edgecolor=GEN_COLORS['accent'], alpha=0.9))

ax.set_title("Top 20 Merchants by Transaction Volume",
             fontsize=26, fontweight='bold',
             color=GEN_COLORS['dark_text'], pad=35, loc='left')
ax.text(0.0, 1.02, "Which merchants dominate card activity?",
        transform=ax.transAxes, fontsize=15,
        color=GEN_COLORS['muted'], style='italic')

plt.tight_layout()
plt.show()
