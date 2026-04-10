# ===========================================================================
# BRANCH SPEND COMPARISON: Multi-Metric (Conference Edition)
# ===========================================================================
# Grouped bar: top 10 branches comparing avg ticket and txns/account. (14,7).

if 'br_agg' not in dir() or len(br_agg) == 0:
    print("    No branch data available. Skipping spend comparison.")
else:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    top10_br = br_agg.head(10).sort_values('avg_spend', ascending=True)
    names = [str(b)[:20] for b in top10_br['branch']]
    y_pos = range(len(top10_br))

    # --- LEFT: Average ticket ---
    ax1.barh(y_pos, top10_br['avg_spend'],
             color=GEN_COLORS['accent'], edgecolor='white', linewidth=0.5, height=0.65)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(names, fontsize=10, fontweight='bold')
    ax1.set_xlabel("Avg Ticket ($)", fontsize=13, fontweight='bold', labelpad=8)
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)
    ax1.set_title("Avg Transaction Size", fontsize=20, fontweight='bold',
                   color=GEN_COLORS['accent'], pad=12)

    for j, (_, row) in enumerate(top10_br.iterrows()):
        ax1.text(row['avg_spend'] + 0.5, j, f"${row['avg_spend']:.2f}",
                 va='center', fontsize=9, fontweight='bold', color=GEN_COLORS['accent'])

    # --- RIGHT: Txns per account ---
    top10_br2 = br_agg.head(10).sort_values('txn_per_account', ascending=True)
    names2 = [str(b)[:20] for b in top10_br2['branch']]

    ax2.barh(y_pos, top10_br2['txn_per_account'],
             color=GEN_COLORS['info'], edgecolor='white', linewidth=0.5, height=0.65)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(names2, fontsize=10, fontweight='bold')
    ax2.set_xlabel("Txns per Account", fontsize=13, fontweight='bold', labelpad=8)
    gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
    ax2.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax2.set_axisbelow(True)
    ax2.set_title("Activity per Account", fontsize=20, fontweight='bold',
                   color=GEN_COLORS['info'], pad=12)

    for j, (_, row) in enumerate(top10_br2.iterrows()):
        ax2.text(row['txn_per_account'] + 0.3, j, f"{row['txn_per_account']:.1f}",
                 va='center', fontsize=9, fontweight='bold', color=GEN_COLORS['info'])

    fig.suptitle("Branch Spend & Activity Comparison",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.04)
    fig.text(0.5, 0.96, "Which branches have the highest-value and most active accounts?",
             ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    plt.show()
