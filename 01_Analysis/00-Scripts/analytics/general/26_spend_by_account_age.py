# ===========================================================================
# SPEND BY ACCOUNT AGE: Spend Ramp-Up Curve (Conference Edition)
# ===========================================================================
# Dual-axis: avg ODDD trailing-12mo spend bars + txns/month line. (14,7).

plot_data = lifecycle_summary.copy()
plot_data['acct_age_band'] = pd.Categorical(
    plot_data['acct_age_band'], categories=ACCT_AGE_ORDER, ordered=True
)
plot_data = plot_data.sort_values('acct_age_band')

fig, ax1 = plt.subplots(figsize=(16, 8))

x_pos = np.arange(len(plot_data))
colors = [ACCT_AGE_PALETTE.get(b, GEN_COLORS['muted']) for b in plot_data['acct_age_band']]

# Spend bars (ODDD trailing 12-month spend)
ax1.bar(
    x_pos, plot_data['avg_oddd_12mo'],
    color=colors, edgecolor='white', linewidth=1.5, width=0.65,
    alpha=0.8, zorder=2
)

ax1.set_xticks(x_pos)
ax1.set_xticklabels(plot_data['acct_age_band'], fontsize=15, fontweight='bold', rotation=45, ha='right')
ax1.set_ylabel("Avg ODDD Trailing 12mo Spend ($)", fontsize=18, fontweight='bold',
                color=GEN_COLORS['info'], labelpad=10)
ax1.tick_params(axis='y', colors=GEN_COLORS['info'])

# Value labels on bars
for i, (x, val) in enumerate(zip(x_pos, plot_data['avg_oddd_12mo'])):
    if pd.notna(val) and val > 0:
        ax1.text(x, val + (plot_data['avg_oddd_12mo'].max() * 0.02),
                 f"${val:,.0f}", ha='center', va='bottom',
                 fontsize=13, fontweight='bold', color=GEN_COLORS['dark_text'])

# Txns/month line on secondary axis
ax2 = ax1.twinx()
ax2.plot(
    x_pos, plot_data['avg_txns_per_month'],
    color=GEN_COLORS['accent'], linewidth=3,
    marker='o', markersize=10, zorder=5
)
ax2.set_ylabel("Avg Txns / Month", fontsize=18, fontweight='bold',
                color=GEN_COLORS['accent'], labelpad=10)
ax2.tick_params(axis='y', colors=GEN_COLORS['accent'])

gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
ax2.spines['top'].set_visible(False)
ax2.spines['left'].set_visible(False)
ax2.grid(False)

ax1.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
ax1.set_axisbelow(True)

ax1.set_title("Spend Ramp-Up by Account Age",
              fontsize=28, fontweight='bold',
              color=GEN_COLORS['dark_text'], pad=35, loc='left')
ax1.text(0.0, 1.02, "Do accounts spend more as they mature? (ODDD trailing 12-month spend)",
         transform=ax1.transAxes, fontsize=16,
         color=GEN_COLORS['muted'], style='italic')

# Legend
from matplotlib.lines import Line2D
legend_elements = [
    plt.Rectangle((0, 0), 1, 1, fc=GEN_COLORS['info'], alpha=0.5, label='Avg ODDD 12mo Spend'),
    Line2D([0], [0], color=GEN_COLORS['accent'], linewidth=3, marker='o',
           markersize=8, label='Avg Txns/Month'),
]
ax1.legend(
    handles=legend_elements,
    loc='upper center', bbox_to_anchor=(0.5, -0.18),
    ncol=2, fontsize=15, frameon=False
)

plt.tight_layout()
plt.subplots_adjust(bottom=0.2)
plt.show()
