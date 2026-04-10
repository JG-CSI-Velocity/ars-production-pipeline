# ===========================================================================
# MCC CONCENTRATION: Cumulative Curve (Conference Edition)
# ===========================================================================
# How many MCCs does it take to reach 80% of transactions? (14,7).

if 'mcc_agg' not in dir() or len(mcc_agg) == 0:
    print("    No MCC data available. Skipping concentration curve.")
else:
    fig, ax = plt.subplots(figsize=(14, 7))

    # Plot cumulative curve (top 50 MCCs)
    plot_data = mcc_top50.copy()
    x_pos = range(1, len(plot_data) + 1)

    ax.fill_between(x_pos, plot_data['cumulative_txn_pct'],
                    alpha=0.15, color=GEN_COLORS['info'])
    ax.plot(x_pos, plot_data['cumulative_txn_pct'],
            color=GEN_COLORS['info'], linewidth=3.5,
            marker='o', markersize=4, zorder=4)

    # Reference lines at 50%, 80%, 90%
    for threshold, label_x_offset in [(50, 2), (80, 2), (90, 2)]:
        ax.axhline(y=threshold, color=GEN_COLORS['muted'], linewidth=1, linestyle='--', alpha=0.6)
        # Find how many MCCs to reach threshold
        above = plot_data[plot_data['cumulative_txn_pct'] >= threshold]
        if len(above) > 0:
            n_mccs = above.index[0] + 1  # 0-indexed in dataframe
            rank = above.iloc[0]['rank']
            ax.plot(rank, threshold, 'o', color=GEN_COLORS['accent'],
                    markersize=10, zorder=5)
            ax.text(rank + label_x_offset, threshold + 1,
                    f"{int(rank)} MCCs = {threshold}%",
                    fontsize=12, fontweight='bold', color=GEN_COLORS['accent'])

    ax.set_xlabel("MCC Category Rank", fontsize=16, fontweight='bold', labelpad=10)
    ax.set_ylabel("Cumulative % of Transactions", fontsize=16, fontweight='bold', labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
    ax.set_xlim(0.5, len(plot_data) + 0.5)
    ax.set_ylim(0, 105)

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    ax.set_title("MCC Concentration Curve",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "How concentrated is card activity across merchant categories?",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
