# ===========================================================================
# PERSONAL VS PORTFOLIO: Segment Merchant Comparison (Conference Edition)
# ===========================================================================
# Two-panel: personal top 10 share vs same merchants' full portfolio share. (14,7).

try:
    seg_top10_p = pers_agg.head(10)[['merchant_consolidated', 'txn_pct']].copy()
    seg_top10_p = seg_top10_p.sort_values('txn_pct', ascending=True)

    # Look up same merchants in the overall portfolio
    portfolio_share = merch_agg.set_index('merchant_consolidated')['txn_pct']
    seg_top10_p['portfolio_pct'] = seg_top10_p['merchant_consolidated'].map(portfolio_share).fillna(0)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    names = seg_top10_p['merchant_consolidated'].str[:22].tolist()
    y_pos = range(len(seg_top10_p))

    # --- LEFT: Personal share ---
    ax1.barh(y_pos, seg_top10_p['txn_pct'],
             color=GEN_COLORS['success'], edgecolor='white', linewidth=0.5, height=0.65)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(names, fontsize=10, fontweight='bold')
    ax1.set_xlabel("% of Personal Txns", fontsize=13, fontweight='bold', labelpad=8)
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)
    ax1.set_title("Personal Account Share", fontsize=20, fontweight='bold',
                   color=GEN_COLORS['success'], pad=12)

    for j, (_, row) in enumerate(seg_top10_p.iterrows()):
        ax1.text(row['txn_pct'] + 0.2, j, f"{row['txn_pct']:.1f}%",
                 va='center', fontsize=10, fontweight='bold', color=GEN_COLORS['success'])

    # --- RIGHT: Full portfolio share for same merchants ---
    ax2.barh(y_pos, seg_top10_p['portfolio_pct'],
             color=GEN_COLORS['muted'], edgecolor='white', linewidth=0.5, height=0.65)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(names, fontsize=10, fontweight='bold')
    ax2.set_xlabel("% of All Portfolio Txns", fontsize=13, fontweight='bold', labelpad=8)
    ax2.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
    gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
    ax2.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax2.set_axisbelow(True)
    ax2.set_title("Full Portfolio Share", fontsize=20, fontweight='bold',
                   color=GEN_COLORS['muted'], pad=12)

    for j, (_, row) in enumerate(seg_top10_p.iterrows()):
        ax2.text(row['portfolio_pct'] + 0.2, j, f"{row['portfolio_pct']:.1f}%",
                 va='center', fontsize=10, fontweight='bold', color=GEN_COLORS['muted'])

    fig.suptitle("Personal vs Full Portfolio",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
    fig.text(0.5, GEN_SUBTITLE_Y, "How do personal account top merchants compare to the overall member base?",
             ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    plt.show()

except NameError:
    print("    merch_agg not available. Run merchant/01_merchant_data first for portfolio comparison.")
