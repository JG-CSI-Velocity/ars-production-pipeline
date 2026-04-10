# ===========================================================================
# BRANCH TOP BAR: Top 15 Branches by Volume (Conference Edition)
# ===========================================================================
# Horizontal bar with % share labels. (14,7).

if 'br_agg' not in dir() or len(br_agg) == 0:
    print("    No branch data available. Skipping top branches bar.")
else:
    fig, ax = plt.subplots(figsize=(14, 7))

    plot_data = br_top15.sort_values('txn_pct', ascending=True)
    names = [str(b)[:25] for b in plot_data['branch']]
    y_pos = range(len(plot_data))

    # Gradient from accent to primary
    n = len(plot_data)
    bar_colors = [plt.cm.ScalarMappable(
        cmap=LinearSegmentedColormap.from_list('br', [GEN_COLORS['accent'], GEN_COLORS['primary']]),
        norm=plt.Normalize(0, n - 1)
    ).to_rgba(i) for i in range(n)]

    ax.barh(y_pos, plot_data['txn_pct'], color=bar_colors,
            edgecolor='white', linewidth=0.5, height=0.7)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=10, fontweight='bold')
    ax.set_xlabel("% of Transactions", fontsize=13, fontweight='bold', labelpad=8)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    max_val = plot_data['txn_pct'].max()
    for j, (_, row) in enumerate(plot_data.iterrows()):
        ax.text(row['txn_pct'] + max_val * 0.01, j,
                f"{row['txn_pct']:.1f}%  ({row['txn_count']:,.0f})",
                va='center', fontsize=9, fontweight='bold',
                color=GEN_COLORS['accent'])

    # Concentration callout
    top5_share_br = br_agg.head(5)['txn_pct'].sum()
    ax.text(0.98, 0.05,
            f"Top 5 branches = {top5_share_br:.1f}% of all transactions",
            transform=ax.transAxes, ha='right', va='bottom',
            fontsize=14, fontweight='bold', color=GEN_COLORS['accent'],
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                      edgecolor=GEN_COLORS['accent'], alpha=0.9))

    ax.set_title("Top 15 Branches by Transaction Volume",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "Which branches drive the most card activity?",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
