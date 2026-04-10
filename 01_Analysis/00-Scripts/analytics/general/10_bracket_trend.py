# ===========================================================================
# BRACKET TREND: Top 5 Bracket Shares Over Time (Conference Edition)
# ===========================================================================
# Multi-line chart showing bracket % share evolution. (14,7).

# Find top 5 brackets by average share
avg_shares = monthly_bracket_pct.mean().sort_values(ascending=False)
top5_brackets = avg_shares.head(5).index.tolist()

# Prepare plotting data
plot_data = monthly_bracket_pct[top5_brackets].copy()
plot_data.index = plot_data.index.to_timestamp()

fig, ax = plt.subplots(figsize=(14, 7))

for i, bracket in enumerate(top5_brackets):
    color = BRACKET_PALETTE[BRACKET_LABELS.index(bracket)]
    ax.plot(
        plot_data.index, plot_data[bracket],
        color=color, linewidth=3, label=bracket,
        marker='o', markersize=6, zorder=4
    )

    # End-of-line label
    last_val = plot_data[bracket].iloc[-1]
    ax.text(
        plot_data.index[-1], last_val,
        f"  {last_val:.1f}%",
        fontsize=12, fontweight='bold', color=color,
        va='center'
    )

ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
gen_clean_axes(ax, keep_left=True, keep_bottom=True)

# Light grid
ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
ax.set_axisbelow(True)

ax.set_xlabel("")
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax.tick_params(axis='x', rotation=45)

ax.set_ylabel("Share of Transactions (%)", fontsize=16, fontweight='bold', labelpad=10)
ax.set_title("Top 5 Bracket Shares Over Time",
             fontsize=26, fontweight='bold',
             color=GEN_COLORS['dark_text'], pad=35, loc='left')
ax.text(0.0, 1.02, "Are spending patterns shifting month to month?",
        transform=ax.transAxes, fontsize=15,
        color=GEN_COLORS['muted'], style='italic')

ax.legend(
    loc='upper center', bbox_to_anchor=(0.5, -0.15),
    ncol=5, fontsize=13, frameon=False
)

plt.tight_layout()
plt.subplots_adjust(bottom=0.18)
plt.show()
