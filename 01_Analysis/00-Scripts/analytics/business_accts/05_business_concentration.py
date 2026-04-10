# ===========================================================================
# BUSINESS CONCENTRATION: Cumulative Curve (Conference Edition)
# ===========================================================================
# How many business merchants cover 80% of transactions? (14,7).

if 'biz_top50' not in dir() or len(biz_top50) == 0:
    print("    No business data available. Skipping concentration curve.")
else:
    fig, ax = plt.subplots(figsize=(14, 7))

    plot_data = biz_top50.copy()
    x_pos = range(1, len(plot_data) + 1)

    ax.fill_between(x_pos, plot_data['cumulative_txn_pct'],
                    alpha=0.15, color=GEN_COLORS['primary'])
    ax.plot(x_pos, plot_data['cumulative_txn_pct'],
            color=GEN_COLORS['primary'], linewidth=3.5,
            marker='o', markersize=4, zorder=4)

    for threshold, x_off in [(50, 2), (80, 2), (90, 2)]:
        ax.axhline(y=threshold, color=GEN_COLORS['muted'], linewidth=1, linestyle='--', alpha=0.6)
        above = plot_data[plot_data['cumulative_txn_pct'] >= threshold]
        if len(above) > 0:
            rank = above.iloc[0]['rank']
            ax.plot(rank, threshold, 'o', color=GEN_COLORS['accent'], markersize=10, zorder=5)
            ax.text(rank + x_off, threshold + 1,
                    f"{int(rank)} merchants = {threshold}%",
                    fontsize=12, fontweight='bold', color=GEN_COLORS['accent'])

    ax.set_xlabel("Merchant Rank", fontsize=16, fontweight='bold', labelpad=10)
    ax.set_ylabel("Cumulative % of Business Transactions", fontsize=16, fontweight='bold', labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
    ax.set_xlim(0.5, len(plot_data) + 0.5)
    ax.set_ylim(0, 105)

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    ax.set_title("Business Merchant Concentration Curve",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "How many merchants cover 80% of business card activity?",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
