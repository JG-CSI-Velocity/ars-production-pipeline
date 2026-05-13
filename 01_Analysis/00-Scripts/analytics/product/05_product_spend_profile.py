# ===========================================================================
# PRODUCT SPEND PROFILE: Avg Ticket & Activity by Product (Conference Edition)
# ===========================================================================
# Grouped bar: avg ticket and txns/account by product. (14,7).

if 'prod_agg' not in dir() or len(prod_agg) == 0:
    print("    No product data available. Skipping spend profile.")
else:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    plot_data = prod_agg.head(10).sort_values('avg_spend', ascending=True)
    names = [p[:22] for p in plot_data['product_label']]
    y_pos = range(len(plot_data))

    # --- LEFT: Average ticket ---
    ax1.barh(y_pos, plot_data['avg_spend'],
             color=GEN_COLORS['primary'], edgecolor='white', linewidth=0.5, height=0.65)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(names, fontsize=10, fontweight='bold')
    ax1.set_xlabel("Avg Ticket ($)", fontsize=13, fontweight='bold', labelpad=8)
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)
    ax1.set_title("Average Transaction Size", fontsize=20, fontweight='bold',
                   color=GEN_COLORS['primary'], pad=12)

    for j, (_, row) in enumerate(plot_data.iterrows()):
        ax1.text(row['avg_spend'] + 0.3, j, f"${row['avg_spend']:.2f}",
                 va='center', fontsize=9, fontweight='bold', color=GEN_COLORS['primary'])

    # --- RIGHT: Txns per account ---
    plot_data2 = prod_agg.head(10).sort_values('txn_per_account', ascending=True)
    names2 = [p[:22] for p in plot_data2['product_label']]

    ax2.barh(y_pos, plot_data2['txn_per_account'],
             color=GEN_COLORS['info'], edgecolor='white', linewidth=0.5, height=0.65)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(names2, fontsize=10, fontweight='bold')
    ax2.set_xlabel("Txns per Account", fontsize=13, fontweight='bold', labelpad=8)
    gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
    ax2.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax2.set_axisbelow(True)
    ax2.set_title("Activity per Account", fontsize=20, fontweight='bold',
                   color=GEN_COLORS['info'], pad=12)

    for j, (_, row) in enumerate(plot_data2.iterrows()):
        ax2.text(row['txn_per_account'] + 0.3, j, f"{row['txn_per_account']:.1f}",
                 va='center', fontsize=9, fontweight='bold', color=GEN_COLORS['info'])

    fig.suptitle("Product Spend & Activity Profile",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
    fig.text(0.5, GEN_SUBTITLE_Y, "Which products generate the highest-value and most frequent usage?",
             ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    plt.show()
