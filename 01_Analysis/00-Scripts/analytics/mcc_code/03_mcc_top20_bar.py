# ===========================================================================
# TOP 20 MCC BAR: Transaction Volume (Conference Edition)
# ===========================================================================
# Horizontal bar with cumulative line. (14,7).

if 'mcc_agg' not in dir() or len(mcc_agg) == 0:
    print("    No MCC data available. Skipping top 20 bar chart.")
else:
    fig, ax1 = plt.subplots(figsize=(14, 7))

    plot_data = mcc_top20.sort_values('txn_count', ascending=True)

    y_pos = range(len(plot_data))
    ax1.barh(
        y_pos, plot_data['txn_count'],
        color=GEN_COLORS['info'], alpha=0.75,
        edgecolor='white', linewidth=1.5, height=0.7
    )

    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(plot_data['mcc_code'], fontsize=12, fontweight='bold')
    ax1.set_xlabel("Transaction Count", fontsize=16, fontweight='bold',
                    color=GEN_COLORS['info'], labelpad=10)
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
    ax1.tick_params(axis='x', colors=GEN_COLORS['info'])

    # Value labels
    for bar, pct in zip(ax1.patches, plot_data['txn_pct']):
        width = bar.get_width()
        ax1.text(width + (plot_data['txn_count'].max() * 0.01),
                 bar.get_y() + bar.get_height() / 2,
                 f"{pct:.1f}%", va='center', fontsize=11,
                 fontweight='bold', color=GEN_COLORS['dark_text'])

    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)

    ax1.set_title("Top 20 MCC Categories by Transaction Volume",
                  fontsize=26, fontweight='bold',
                  color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax1.text(0.0, 0.97, "Which merchant categories dominate card activity?",
             transform=ax1.transAxes, fontsize=15,
             color=GEN_COLORS['muted'], style='italic')

    # Concentration callout
    top5_cum = mcc_agg.head(5)['txn_pct'].sum()
    ax1.text(
        0.99, 0.05,
        f"Top 5 MCCs = {top5_cum:.1f}% of all transactions",
        transform=ax1.transAxes,
        fontsize=15, fontweight='bold', color=GEN_COLORS['accent'],
        ha='right', va='bottom',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                  edgecolor=GEN_COLORS['accent'], alpha=0.9)
    )

    plt.tight_layout()
    plt.show()
