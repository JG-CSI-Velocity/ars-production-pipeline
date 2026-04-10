# ===========================================================================
# CATEGORY BREAKDOWN: Donut Chart + Summary (Conference Edition)
# ===========================================================================
# Share of competitor transactions by category. No dollars.

if len(all_competitor_data) > 0:
    summary_df = pd.DataFrame(summary_data)

    cat_agg = summary_df.groupby('category').agg({
        'total_transactions': 'sum',
        'unique_accounts': 'sum',
        'competitor': 'count'
    }).sort_values('total_transactions', ascending=False)

    cat_agg['pct'] = cat_agg['total_transactions'] / cat_agg['total_transactions'].sum() * 100
    cat_agg.index = cat_agg.index.str.replace('_', ' ').str.title()

    # ----- Build chart: donut left, stats right -----
    fig = plt.figure(figsize=(16, 8))
    gs = GridSpec(1, 2, width_ratios=[1, 1.1], wspace=0.05)

    # --- LEFT: Donut ---
    ax_donut = fig.add_subplot(gs[0])

    colors = [CATEGORY_PALETTE.get(c, GEN_COLORS['muted']) for c in cat_agg.index]

    wedges, texts, autotexts = ax_donut.pie(
        cat_agg['total_transactions'],
        labels=None,
        autopct='%1.0f%%',
        colors=colors,
        startangle=90,
        pctdistance=0.78,
        wedgeprops=dict(width=0.45, edgecolor='white', linewidth=3)
    )

    for t in autotexts:
        t.set_fontsize(16)
        t.set_fontweight('bold')
        t.set_color('white')
        t.set_path_effects([pe.withStroke(linewidth=2, foreground='#333333')])

    # Center label
    ax_donut.text(0, 0, f"{cat_agg['total_transactions'].sum():,.0f}\nTransactions",
                  ha='center', va='center',
                  fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], linespacing=1.5)

    ax_donut.set_title("Transaction Share\nby Category",
                       fontsize=22, fontweight='bold',
                       color=GEN_COLORS['dark_text'], pad=15)

    # --- RIGHT: Category stats (visual, not a raw table) ---
    ax_stats = fig.add_subplot(gs[1])
    ax_stats.axis('off')

    y_start = 0.90
    y_step = 0.17

    for i, (cat, row) in enumerate(cat_agg.iterrows()):
        y_pos = y_start - (i * y_step)
        color = CATEGORY_PALETTE.get(cat, GEN_COLORS['muted'])

        # Color dot
        ax_stats.plot(0.02, y_pos, 'o', markersize=16, color=color,
                      transform=ax_stats.transAxes, clip_on=False)

        # Category name
        ax_stats.text(0.08, y_pos, cat, transform=ax_stats.transAxes,
                      fontsize=18, fontweight='bold', color=GEN_COLORS['dark_text'],
                      va='center')

        # Stats line
        stats_text = (
            f"{row['total_transactions']:,.0f} txn   |   "
            f"{row['unique_accounts']:,.0f} accounts   |   "
            f"{int(row['competitor'])} competitors"
        )
        ax_stats.text(0.08, y_pos - 0.045, stats_text,
                      transform=ax_stats.transAxes,
                      fontsize=13, color=GEN_COLORS['muted'], va='center')

    # Supertitle
    fig.suptitle("Competitive Landscape by Category",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.02)

    plt.tight_layout()
    plt.show()
