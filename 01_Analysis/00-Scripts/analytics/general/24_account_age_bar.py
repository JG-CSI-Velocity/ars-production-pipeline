# ===========================================================================
# ACCOUNT AGE BAR: Activity by Account Age Band (Conference Edition)
# ===========================================================================
# Grouped horizontal bar: account count + avg txns/month. (14,7).

fig, ax1 = plt.subplots(figsize=(16, 8))

plot_data = lifecycle_summary.copy()
plot_data['acct_age_band'] = pd.Categorical(
    plot_data['acct_age_band'], categories=ACCT_AGE_ORDER, ordered=True
)
plot_data = plot_data.sort_values('acct_age_band')

y_pos = np.arange(len(plot_data))
colors = [ACCT_AGE_PALETTE.get(b, GEN_COLORS['muted']) for b in plot_data['acct_age_band']]

# Account count bars
bars = ax1.barh(
    y_pos, plot_data['account_count'],
    color=colors, edgecolor='white', linewidth=1.5, height=0.6
)

ax1.set_yticks(y_pos)
ax1.set_yticklabels(plot_data['acct_age_band'], fontsize=15, fontweight='bold')
ax1.invert_yaxis()
ax1.set_xlabel("Account Count", fontsize=18, fontweight='bold',
                color=GEN_COLORS['info'], labelpad=10)
ax1.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
ax1.tick_params(axis='x', colors=GEN_COLORS['info'])

# Avg txns/month on secondary axis
ax2 = ax1.twiny()
ax2.plot(
    plot_data['avg_txns_per_month'].values, y_pos,
    color=GEN_COLORS['accent'], linewidth=3,
    marker='o', markersize=10, zorder=5
)
ax2.set_xlabel("Avg Txns / Month", fontsize=18, fontweight='bold',
                color=GEN_COLORS['accent'], labelpad=10)
ax2.tick_params(axis='x', colors=GEN_COLORS['accent'])

gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
ax2.spines['top'].set_visible(True)
ax2.spines['top'].set_color(GEN_COLORS['grid'])
ax2.spines['right'].set_visible(False)
ax2.spines['left'].set_visible(False)
ax2.spines['bottom'].set_visible(False)

ax1.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
ax1.set_axisbelow(True)

ax1.set_title("Account Activity by Account Age",
              fontsize=28, fontweight='bold',
              color=GEN_COLORS['dark_text'], pad=40, loc='left')
ax1.text(0.0, 1.12, "Are newer or older accounts more active? (monthly txn rate)",
         transform=ax1.transAxes, fontsize=16,
         color=GEN_COLORS['muted'], style='italic')

# Legend
from matplotlib.lines import Line2D
legend_elements = [
    plt.Rectangle((0, 0), 1, 1, fc=GEN_COLORS['info'], alpha=0.5, label='Account Count'),
    Line2D([0], [0], color=GEN_COLORS['accent'], linewidth=3, marker='o',
           markersize=8, label='Avg Txns/Month'),
]
ax1.legend(
    handles=legend_elements,
    loc='upper center', bbox_to_anchor=(0.5, -0.08),
    ncol=2, fontsize=15, frameon=False
)

plt.tight_layout()
plt.subplots_adjust(bottom=0.12)
plt.show()
