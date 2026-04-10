# ===========================================================================
# ENGAGEMENT BAR: Activity Tiers (Conference Edition)
# ===========================================================================
# Horizontal bar per tier + callout. (8,7) square.

fig, ax = plt.subplots(figsize=(8, 7))

y_pos = range(len(engagement_df))
colors = [ENGAGE_PALETTE[t] for t in engagement_df['tier']]

bars = ax.barh(
    y_pos, engagement_df['txn_count'],
    color=colors, edgecolor='white', linewidth=1.5, height=0.65
)

ax.set_yticks(y_pos)
ax.set_yticklabels(engagement_df['tier'], fontsize=14, fontweight='bold')
ax.invert_yaxis()

# Value labels
for bar, row in zip(bars, engagement_df.itertuples()):
    width = bar.get_width()
    ax.text(width + (engagement_df['txn_count'].max() * 0.01),
            bar.get_y() + bar.get_height() / 2,
            f"{width:,.0f} txns ({row.txn_pct:.1f}%)",
            va='center', fontsize=12, fontweight='bold',
            color=GEN_COLORS['dark_text'])

ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
gen_clean_axes(ax, keep_left=True, keep_bottom=True)
ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
ax.set_axisbelow(True)

ax.set_xlabel("Transaction Count", fontsize=16, fontweight='bold', labelpad=10)
ax.set_title("Member Engagement Tiers",
             fontsize=22, fontweight='bold',
             color=GEN_COLORS['dark_text'], pad=35, loc='left')
ax.text(0.0, 1.02, "Who drives portfolio volume?",
        transform=ax.transAxes, fontsize=14,
        color=GEN_COLORS['muted'], style='italic')

plt.tight_layout()
plt.show()

# Callout
power_row = engagement_df[engagement_df['tier'] == 'Power'].iloc[0]
print(f"\n    Power users = {power_row['acct_pct']:.0f}% of accounts, "
      f"drive {power_row['txn_pct']:.1f}% of transactions")
