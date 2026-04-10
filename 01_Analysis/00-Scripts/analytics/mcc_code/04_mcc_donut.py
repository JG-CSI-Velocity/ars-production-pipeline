# ===========================================================================
# MCC DONUT: Category Share + Stats Panel (Conference Edition)
# ===========================================================================
# Top 8 categories donut + stats. (14,7).

if 'mcc_agg' not in dir() or len(mcc_agg) == 0:
    print("    No MCC data available. Skipping donut chart.")
else:
    top8 = mcc_agg.head(8).copy()
    other_pct = 100 - top8['txn_pct'].sum()

    # Donut data: top 8 + "Other"
    donut_vals = list(top8['txn_count']) + [total_txns_all - top8['txn_count'].sum()]
    donut_labels = list(top8['mcc_code']) + ['Other']
    donut_colors = BRACKET_PALETTE[:8] + [GEN_COLORS['grid']]

    fig = plt.figure(figsize=(14, 7))
    gs = GridSpec(1, 2, width_ratios=[1, 1.1], wspace=0.05)

    # --- LEFT: Donut ---
    ax_donut = fig.add_subplot(gs[0])

    wedges, texts, autotexts = ax_donut.pie(
        donut_vals, labels=None, autopct='%1.0f%%',
        colors=donut_colors, startangle=90, pctdistance=0.78,
        wedgeprops=dict(width=0.45, edgecolor='white', linewidth=3)
    )

    for t in autotexts:
        t.set_fontsize(13)
        t.set_fontweight('bold')
        t.set_color('white')
        t.set_path_effects([pe.withStroke(linewidth=2, foreground='#333333')])

    ax_donut.text(0, 0, f"{total_txns_all:,.0f}\nTransactions",
                  ha='center', va='center',
                  fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], linespacing=1.5)

    ax_donut.set_title("Transaction Share\nby MCC Category",
                        fontsize=22, fontweight='bold',
                        color=GEN_COLORS['dark_text'], pad=15)

    # --- RIGHT: Stats panel ---
    ax_stats = fig.add_subplot(gs[1])
    ax_stats.axis('off')

    y_start = 0.92
    y_step = 0.105

    for i, (_, row) in enumerate(top8.iterrows()):
        y_pos = y_start - (i * y_step)
        color = BRACKET_PALETTE[i]

        ax_stats.plot(0.02, y_pos, 'o', markersize=14, color=color,
                      transform=ax_stats.transAxes, clip_on=False)

        ax_stats.text(0.08, y_pos, f"MCC {row['mcc_code']}",
                      transform=ax_stats.transAxes,
                      fontsize=15, fontweight='bold', color=GEN_COLORS['dark_text'],
                      va='center')

        stats_text = (
            f"{row['txn_count']:,.0f} txn   |   "
            f"{row['unique_accounts']:,.0f} accts   |   "
            f"{row['txn_per_account']:.1f} txn/acct"
        )
        ax_stats.text(0.08, y_pos - 0.038, stats_text,
                      transform=ax_stats.transAxes,
                      fontsize=11, color=GEN_COLORS['muted'], va='center')

    # Other row
    _other_count = max(len(mcc_agg) - 8, 0)
    y_pos = y_start - (8 * y_step)
    ax_stats.plot(0.02, y_pos, 'o', markersize=14, color=GEN_COLORS['grid'],
                  transform=ax_stats.transAxes, clip_on=False)
    ax_stats.text(0.08, y_pos, f"Other ({_other_count} MCCs)",
                  transform=ax_stats.transAxes,
                  fontsize=15, fontweight='bold', color=GEN_COLORS['muted'],
                  va='center')
    ax_stats.text(0.08, y_pos - 0.038, f"{other_pct:.1f}% of transactions",
                  transform=ax_stats.transAxes,
                  fontsize=11, color=GEN_COLORS['muted'], va='center')

    fig.suptitle("MCC Category Breakdown",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.02)

    plt.tight_layout()
    plt.show()
