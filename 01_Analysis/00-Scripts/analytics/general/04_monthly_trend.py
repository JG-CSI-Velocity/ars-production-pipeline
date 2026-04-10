# ===========================================================================
# MONTHLY TREND: Transaction Volume Over Time (Conference Edition)
# ===========================================================================
# Dual-axis: txn count bars + rolling line + account rolling line
# No dollar figures.

# Prepare timestamp index for plotting
plot_monthly = monthly_summary.copy()
plot_monthly.index = plot_monthly.index.to_timestamp()

fig, ax1 = plt.subplots(figsize=(14, 7))

# Transaction bars (light background)
ax1.bar(
    plot_monthly.index, plot_monthly['txn_count'],
    width=25, color=GEN_COLORS['info'], alpha=0.25,
    label='Monthly Transactions', zorder=2
)

# Transaction rolling line (bold foreground)
ax1.plot(
    plot_monthly.index, plot_monthly['txn_rolling'],
    color=GEN_COLORS['info'], linewidth=3.5,
    label='Transaction Trend (3mo avg)', zorder=4
)

ax1.set_ylabel("Transaction Count", fontsize=18, fontweight='bold',
                color=GEN_COLORS['info'], labelpad=12)
ax1.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
ax1.tick_params(axis='y', colors=GEN_COLORS['info'])

# Second axis: unique accounts
ax2 = ax1.twinx()
ax2.plot(
    plot_monthly.index, plot_monthly['acct_rolling'],
    color=GEN_COLORS['accent'], linewidth=3.5, linestyle='--',
    label='Unique Accounts (3mo avg)', zorder=4
)
ax2.set_ylabel("Unique Accounts", fontsize=18, fontweight='bold',
                color=GEN_COLORS['accent'], labelpad=12)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
ax2.tick_params(axis='y', colors=GEN_COLORS['accent'])

# Axes cleanup
gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
ax2.spines['top'].set_visible(False)
ax2.spines['left'].set_visible(False)
ax2.grid(False)

# Light horizontal grid on primary axis
ax1.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
ax1.set_axisbelow(True)

# X-axis formatting
ax1.set_xlabel("")
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
ax1.tick_params(axis='x', rotation=45)

# Title + subtitle
ax1.set_title("Monthly Transaction Activity",
              fontsize=26, fontweight='bold',
              color=GEN_COLORS['dark_text'], pad=35, loc='left')
ax1.text(0.0, 1.02, "How is portfolio activity trending month over month?",
         transform=ax1.transAxes, fontsize=15,
         color=GEN_COLORS['muted'], style='italic')

# Growth callout
growth_val = portfolio_kpis['latest_txn_growth']
growth_color = GEN_COLORS['success'] if growth_val >= 0 else GEN_COLORS['accent']
growth_label = "GROWING" if growth_val >= 0 else "DECLINING"
ax1.text(
    0.99, 0.95,
    f"Latest month: {growth_val:+.1f}% ({growth_label})",
    transform=ax1.transAxes,
    fontsize=16, fontweight='bold', color=growth_color,
    ha='right', va='top',
    bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
              edgecolor=growth_color, alpha=0.9)
)

# Combined legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(
    lines1 + lines2, labels1 + labels2,
    loc='upper center', bbox_to_anchor=(0.5, -0.15),
    ncol=3, fontsize=14, frameon=False
)

plt.tight_layout()
plt.subplots_adjust(bottom=0.18)
plt.show()
