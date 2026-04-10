# ===========================================================================
# BRANCH CONCENTRATION: Cumulative Curve (Conference Edition)
# ===========================================================================
# Do a few branches dominate? 50/80/90% thresholds. (14,7).

if 'br_agg' not in dir() or len(br_agg) == 0:
    print("    No branch data available. Skipping concentration curve.")
else:
    fig, ax = plt.subplots(figsize=(14, 7))

    x = br_agg['rank'].values
    y = br_agg['cumulative_txn_pct'].values

    ax.fill_between(x, y, alpha=0.15, color=GEN_COLORS['accent'])
    ax.plot(x, y, color=GEN_COLORS['accent'], linewidth=3, zorder=4)

    # Threshold markers
    for threshold, ls in [(50, '--'), (80, '--'), (90, ':')]:
        ax.axhline(y=threshold, color=GEN_COLORS['muted'], linestyle=ls,
                    linewidth=1.5, alpha=0.6, zorder=2)
        # Find the branch count at this threshold
        above = br_agg[br_agg['cumulative_txn_pct'] >= threshold]
        if len(above) > 0:
            n_at = int(above.iloc[0]['rank'])
            ax.plot(n_at, threshold, 'o', color=GEN_COLORS['accent'],
                    markersize=10, zorder=5)
            ax.text(n_at + len(br_agg) * 0.02, threshold + 1.5,
                    f"{threshold}% at {n_at} branches",
                    fontsize=12, fontweight='bold', color=GEN_COLORS['accent'])

    ax.set_xlabel("Number of Branches (ranked)", fontsize=16, fontweight='bold', labelpad=10)
    ax.set_ylabel("Cumulative % of Transactions", fontsize=16, fontweight='bold', labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
    ax.set_ylim(0, 105)
    ax.set_xlim(1, len(br_agg))

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    ax.set_title("Branch Concentration Curve",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "How concentrated is card activity across branches?",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
