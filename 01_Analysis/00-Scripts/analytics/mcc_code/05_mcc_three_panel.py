# ===========================================================================
# MCC THREE-PANEL: Spend vs Txns vs Accounts (Conference Edition)
# ===========================================================================
# Replaces old 04-viz-comparison. Conference theme, correct size. (18,8).

if 'mcc_agg' not in dir() or len(mcc_agg) == 0:
    print("    No MCC data available. Skipping three-panel chart.")
else:
    top15 = mcc_agg.head(15).sort_values('txn_count', ascending=True).copy()
    mcc_labels = top15['mcc_code'].astype(str).values

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 8), sharey=True)

    y_pos = np.arange(len(top15))

    # --- Panel 1: Total Spend ---
    ax1.barh(y_pos, top15['total_spend'], color=GEN_COLORS['info'],
             edgecolor='white', linewidth=1, height=0.7)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(mcc_labels, fontsize=12, fontweight='bold')
    ax1.set_xlabel("Total Spend", fontsize=14, fontweight='bold')
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(
        lambda x, _: f"${x/1e6:.1f}M" if x >= 1e6 else f"${x/1e3:.0f}K"
    ))
    ax1.set_title("By Total Spend", fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], pad=12)
    gen_clean_axes(ax1)
    ax1.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)

    # --- Panel 2: Transaction Count ---
    ax2.barh(y_pos, top15['txn_count'], color=GEN_COLORS['success'],
             edgecolor='white', linewidth=1, height=0.7)
    ax2.set_xlabel("Transactions", fontsize=14, fontweight='bold')
    ax2.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
    ax2.set_title("By Transaction Count", fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], pad=12)
    gen_clean_axes(ax2)
    ax2.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax2.set_axisbelow(True)

    # --- Panel 3: Unique Accounts ---
    ax3.barh(y_pos, top15['unique_accounts'], color=GEN_COLORS['warning'],
             edgecolor='white', linewidth=1, height=0.7)
    ax3.set_xlabel("Unique Accounts", fontsize=14, fontweight='bold')
    ax3.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
    ax3.set_title("By Account Reach", fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], pad=12)
    gen_clean_axes(ax3)
    ax3.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax3.set_axisbelow(True)

    fig.suptitle("Top 15 MCC Categories -- Three Perspectives",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.02)

    plt.tight_layout()
    plt.show()
