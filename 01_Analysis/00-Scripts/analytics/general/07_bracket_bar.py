# ===========================================================================
# BRACKET BAR: Transaction Volume by Spending Bracket (Conference Edition)
# ===========================================================================
# Horizontal bar. (8,7) square. No dollars.

fig, ax = plt.subplots(figsize=(8, 7))

y_pos = range(len(bracket_df))
bars = ax.barh(
    y_pos, bracket_df['txn_count'],
    color=BRACKET_PALETTE, edgecolor='white', linewidth=1.5,
    height=0.7
)

ax.set_yticks(y_pos)
ax.set_yticklabels(bracket_df['bracket'], fontsize=14, fontweight='bold')
ax.invert_yaxis()

# Value labels on bars
for bar, pct in zip(bars, bracket_df['txn_pct']):
    width = bar.get_width()
    ax.text(width + (bracket_df['txn_count'].max() * 0.01), bar.get_y() + bar.get_height() / 2,
            f"{width:,.0f} ({pct:.1f}%)",
            va='center', fontsize=12, fontweight='bold', color=GEN_COLORS['dark_text'])

ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
gen_clean_axes(ax, keep_left=True, keep_bottom=True)

# Light vertical grid
ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
ax.set_axisbelow(True)

ax.set_xlabel("Transaction Count", fontsize=16, fontweight='bold', labelpad=10)
ax.set_title("Transactions by Spending Bracket",
             fontsize=22, fontweight='bold',
             color=GEN_COLORS['dark_text'], pad=35, loc='left')
ax.text(0.0, 1.02, "Where do most card swipes land?",
        transform=ax.transAxes, fontsize=14,
        color=GEN_COLORS['muted'], style='italic')

plt.tight_layout()
plt.show()
