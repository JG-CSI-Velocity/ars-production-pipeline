# ===========================================================================
# MERCHANT CONCENTRATION: Top 15 + Cumulative Curve (Conference Edition)
# ===========================================================================
# Top 15 merchants bar + cumulative % line. (14,7).

# Top 15 merchants by transaction count
merchant_counts = (
    combined_df.groupby('merchant_consolidated')['transaction_date']
    .count()
    .sort_values(ascending=False)
)

top15 = merchant_counts.head(15).reset_index()
top15.columns = ['merchant', 'txn_count']
top15['txn_pct'] = top15['txn_count'] / len(combined_df) * 100
top15['cumulative_pct'] = top15['txn_pct'].cumsum()

fig, ax1 = plt.subplots(figsize=(14, 7))

# Bars
x_pos = range(len(top15))
ax1.bar(
    x_pos, top15['txn_count'],
    color=GEN_COLORS['info'], alpha=0.7,
    edgecolor='white', linewidth=1.5, zorder=2
)

ax1.set_xticks(x_pos)
ax1.set_xticklabels(top15['merchant'], fontsize=11, fontweight='bold', rotation=45, ha='right')
ax1.set_ylabel("Transaction Count", fontsize=16, fontweight='bold',
                color=GEN_COLORS['info'], labelpad=10)
ax1.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
ax1.tick_params(axis='y', colors=GEN_COLORS['info'])

# Cumulative line on secondary axis
ax2 = ax1.twinx()
ax2.plot(
    x_pos, top15['cumulative_pct'],
    color=GEN_COLORS['accent'], linewidth=3,
    marker='o', markersize=6, zorder=4
)
ax2.set_ylabel("Cumulative %", fontsize=16, fontweight='bold',
                color=GEN_COLORS['accent'], labelpad=10)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
ax2.tick_params(axis='y', colors=GEN_COLORS['accent'])

gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
ax2.spines['top'].set_visible(False)
ax2.spines['left'].set_visible(False)
ax2.grid(False)

ax1.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
ax1.set_axisbelow(True)

ax1.set_title("Merchant Concentration",
              fontsize=26, fontweight='bold',
              color=GEN_COLORS['dark_text'], pad=35, loc='left')
ax1.text(0.0, 1.02, "How concentrated is transaction volume among top merchants?",
         transform=ax1.transAxes, fontsize=15,
         color=GEN_COLORS['muted'], style='italic')

# Concentration callout
top10_cum = top15['cumulative_pct'].iloc[9] if len(top15) >= 10 else top15['cumulative_pct'].iloc[-1]
ax1.text(
    0.99, 0.50,
    f"Top 10 merchants = {top10_cum:.1f}% of txns",
    transform=ax1.transAxes,
    fontsize=16, fontweight='bold', color=GEN_COLORS['accent'],
    ha='right', va='center',
    bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
              edgecolor=GEN_COLORS['accent'], alpha=0.9)
)

# Combined legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(
    lines1 + lines2, ['Transaction Count', 'Cumulative %'],
    loc='upper center', bbox_to_anchor=(0.5, -0.22),
    ncol=2, fontsize=14, frameon=False
)

plt.tight_layout()
plt.subplots_adjust(bottom=0.25)
plt.show()
