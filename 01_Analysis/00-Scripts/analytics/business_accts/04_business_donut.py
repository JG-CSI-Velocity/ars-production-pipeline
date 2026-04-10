# ===========================================================================
# BUSINESS DONUT: Top 8 + Other with Stats Panel (Conference Edition)
# ===========================================================================
# Donut chart + stats table side by side. (14,7).

if 'biz_agg' not in dir() or len(biz_agg) == 0:
    print("    No business data available. Skipping donut chart.")
else:
    top8_b = biz_agg.head(8).copy()
    other_txns_b = total_txns_biz - top8_b['txn_count'].sum()

    labels = top8_b['merchant_consolidated'].str[:25].tolist() + ['Other']
    sizes = top8_b['txn_count'].tolist() + [other_txns_b]
    donut_colors = BRACKET_PALETTE[:8] + [GEN_COLORS['grid']]

    fig = plt.figure(figsize=(14, 7))
    gs = GridSpec(1, 2, width_ratios=[1, 1.1], wspace=0.05)

    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    wedges, _, autotexts = ax1.pie(
        sizes, labels=None, autopct='%1.0f%%',
        colors=donut_colors, startangle=90, pctdistance=0.78,
        wedgeprops=dict(width=0.45, edgecolor='white', linewidth=3)
    )
    for t in autotexts:
        t.set_fontsize(11)
        t.set_fontweight('bold')
        t.set_color('white')
        t.set_path_effects([pe.withStroke(linewidth=2, foreground='#333333')])

    ax1.text(0, 0, f"{total_txns_biz:,.0f}\nBusiness Txns",
             ha='center', va='center', fontsize=16, fontweight='bold',
             color=GEN_COLORS['dark_text'], linespacing=1.5)

    ax2.axis('off')
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)

    y_start = 9.0
    y_step = 0.95

    for i, (_, row) in enumerate(top8_b.iterrows()):
        y = y_start - i * y_step
        color = donut_colors[i]
        name = row['merchant_consolidated'][:28]
        ax2.plot(0.3, y, 'o', color=color, markersize=12, zorder=3)
        ax2.text(0.8, y, name, fontsize=11, fontweight='bold',
                 color=GEN_COLORS['dark_text'], va='center')
        ax2.text(6.8, y, f"{row['txn_count']:,.0f}", fontsize=11, fontweight='bold',
                 color=GEN_COLORS['dark_text'], va='center', ha='right')
        ax2.text(8.0, y, f"{row['unique_accounts']:,.0f}", fontsize=11,
                 color=GEN_COLORS['muted'], va='center', ha='right')
        ax2.text(9.5, y, f"{row['txn_pct']:.1f}%", fontsize=11, fontweight='bold',
                 color=color, va='center', ha='right')

    y = y_start - 8 * y_step
    ax2.plot(0.3, y, 'o', color=GEN_COLORS['grid'], markersize=12, zorder=3)
    ax2.text(0.8, y, 'All Other', fontsize=11, fontweight='bold',
             color=GEN_COLORS['muted'], va='center')
    ax2.text(6.8, y, f"{other_txns_b:,.0f}", fontsize=11, fontweight='bold',
             color=GEN_COLORS['muted'], va='center', ha='right')
    other_pct_b = other_txns_b / total_txns_biz * 100
    ax2.text(9.5, y, f"{other_pct_b:.1f}%", fontsize=11, fontweight='bold',
             color=GEN_COLORS['muted'], va='center', ha='right')

    y_header = y_start + 0.6
    ax2.text(6.8, y_header, 'Txns', fontsize=10, color=GEN_COLORS['muted'],
             ha='right', style='italic')
    ax2.text(8.0, y_header, 'Accts', fontsize=10, color=GEN_COLORS['muted'],
             ha='right', style='italic')
    ax2.text(9.5, y_header, 'Share', fontsize=10, color=GEN_COLORS['muted'],
             ha='right', style='italic')

    fig.suptitle("Business Account Merchant Breakdown",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.04)

    plt.tight_layout()
    plt.show()
