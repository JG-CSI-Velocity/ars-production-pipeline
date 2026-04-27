# ===========================================================================
# PRODUCT DONUT: Top Products + Stats Panel (Conference Edition)
# ===========================================================================
# Donut with stats panel via GridSpec. (14,7).

if 'prod_agg' not in dir() or len(prod_agg) == 0:
    print("    No product data available. Skipping donut chart.")
else:
    top_n = min(8, len(prod_agg))
    prod_top_donut = prod_agg.head(top_n).copy()
    other_pct = 100 - prod_top_donut['txn_pct'].sum()

    fig = plt.figure(figsize=(14, 7))
    gs = GridSpec(1, 2, width_ratios=[1.2, 0.8], figure=fig)
    ax_donut = fig.add_subplot(gs[0])
    ax_stats = fig.add_subplot(gs[1])

    # --- DONUT ---
    sizes = list(prod_top_donut['txn_pct']) + ([other_pct] if other_pct > 0.5 else [])
    labels = [p[:20] for p in prod_top_donut['product_label']] + (['Other'] if other_pct > 0.5 else [])

    donut_colors = BRACKET_PALETTE[:top_n] + ([GEN_COLORS['grid']] if other_pct > 0.5 else [])

    wedges, texts, autotexts = ax_donut.pie(
        sizes, labels=labels, colors=donut_colors,
        autopct='%1.1f%%', startangle=90, pctdistance=0.78,
        wedgeprops=dict(width=0.38, edgecolor='white', linewidth=2),
        textprops={'fontsize': 10, 'fontweight': 'bold'},
    )
    for t in autotexts:
        t.set_fontsize(9)
        t.set_fontweight('bold')
        t.set_color('white')

    centre = plt.Circle((0, 0), 0.58, fc='white')
    ax_donut.add_artist(centre)
    ax_donut.text(0, 0.05, f"{total_txns_prod:,}", ha='center', va='center',
                  fontsize=18, fontweight='bold', color=GEN_COLORS['dark_text'])
    ax_donut.text(0, -0.10, "transactions", ha='center', va='center',
                  fontsize=10, color=GEN_COLORS['muted'])

    # --- STATS PANEL ---
    ax_stats.axis('off')
    stats_lines = [
        f"Top {top_n} products = {prod_top_donut['txn_pct'].sum():.1f}% of txns",
        f"",
        f"#1: {prod_agg.iloc[0]['product_label'][:30]}",
        f"     {prod_agg.iloc[0]['txn_pct']:.1f}% share, {int(prod_agg.iloc[0]['unique_accounts']):,} accounts",
        f"",
        f"Total products: {len(prod_agg)}",
        f"Total accounts: {total_accts_prod:,}",
        f"Avg ticket range: ${prod_agg['avg_spend'].min():.2f} - ${prod_agg['avg_spend'].max():.2f}",
    ]
    for i, line in enumerate(stats_lines):
        weight = 'bold' if i in [0, 2, 5] else 'normal'
        color = GEN_COLORS['primary'] if i in [0, 2, 5] else GEN_COLORS['dark_text']
        ax_stats.text(0.05, 0.92 - i * 0.1, line,
                      fontsize=13, fontweight=weight, color=color,
                      transform=ax_stats.transAxes, va='top')

    fig.suptitle("Card Product Mix",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
    fig.text(0.5, GEN_SUBTITLE_Y, "How is transaction volume distributed across card products?",
             ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    plt.show()
