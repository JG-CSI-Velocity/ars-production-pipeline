# ===========================================================================
# TOP 15 COMPETITORS: Horizontal Bar Chart (Conference Edition)
# ===========================================================================
# Ranked by transaction count (no dollars). Color-coded by category.

if len(all_competitor_data) > 0:
    summary_df = pd.DataFrame(summary_data).sort_values('total_transactions', ascending=False)
    top_15 = summary_df.head(15).copy()

    top_15['category_label'] = top_15['category'].str.replace('_', ' ').str.title()
    top_15['bar_color'] = top_15['category_label'].map(
        lambda c: CATEGORY_PALETTE.get(c, GEN_COLORS['muted'])
    )

    # Shorten names for readability
    top_15['short_name'] = top_15['competitor'].apply(
        lambda n: n[:25] + '..' if len(str(n)) > 27 else n
    )

    # ----- Build chart -----
    fig, ax = plt.subplots(figsize=(14, 9))

    # Reverse so #1 is at top
    plot_data = top_15.iloc[::-1]

    bars = ax.barh(
        range(len(plot_data)),
        plot_data['total_transactions'],
        color=plot_data['bar_color'].values,
        edgecolor='white',
        linewidth=1,
        height=0.7,
        zorder=3
    )

    # Value labels at end of each bar
    for i, (_, row) in enumerate(plot_data.iterrows()):
        ax.text(
            row['total_transactions'] * 1.01,
            i,
            f"{row['total_transactions']:,.0f}  ({row['unique_accounts']:,.0f} accts)",
            fontsize=12, fontweight='bold',
            color=GEN_COLORS['dark_text'],
            va='center'
        )

    ax.set_yticks(range(len(plot_data)))
    ax.set_yticklabels(plot_data['short_name'], fontsize=13, fontweight='bold')
    ax.set_xlabel("Transaction Count", fontsize=18, fontweight='bold', labelpad=12)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    # Extend x-axis for labels
    max_val = plot_data['total_transactions'].max()
    ax.set_xlim(0, max_val * 1.35)

    # Title
    ax.set_title("Top 15 Competitors by Transaction Volume",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=20, loc='left')
    ax.text(0.0, 0.97, "Where are your customers transacting?",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    # Category legend
    legend_cats = top_15['category_label'].unique()
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, fc=CATEGORY_PALETTE.get(c, GEN_COLORS['muted']),
                       edgecolor='white', linewidth=1, label=c)
        for c in legend_cats
    ]
    ax.legend(
        handles=legend_handles,
        loc='lower right',
        fontsize=13,
        frameon=False,
        handletextpad=0.5
    )

    plt.tight_layout()
    plt.show()
