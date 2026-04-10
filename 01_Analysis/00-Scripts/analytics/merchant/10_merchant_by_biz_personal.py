# ===========================================================================
# MERCHANT BY BIZ/PERSONAL: Top Merchants per Segment (Conference Edition)
# ===========================================================================
# Side-by-side horizontal bars: top 10 merchants for each segment. (14,7).

if 'business_flag' in combined_df.columns:
    biz_merch = combined_df[combined_df['business_flag'] == 'Yes'].groupby(
        'merchant_consolidated').size().reset_index(name='txn_count')
    biz_total = (combined_df['business_flag'] == 'Yes').sum()
    biz_merch['pct'] = biz_merch['txn_count'] / biz_total * 100
    biz_merch = biz_merch.sort_values('pct', ascending=False).head(10)

    per_merch = combined_df[combined_df['business_flag'] == 'No'].groupby(
        'merchant_consolidated').size().reset_index(name='txn_count')
    per_total = (combined_df['business_flag'] == 'No').sum()
    per_merch['pct'] = per_merch['txn_count'] / per_total * 100
    per_merch = per_merch.sort_values('pct', ascending=False).head(10)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    # --- LEFT: Business ---
    biz_plot = biz_merch.sort_values('pct', ascending=True)
    ax1.barh(range(len(biz_plot)), biz_plot['pct'],
             color=GEN_COLORS['primary'], edgecolor='white', linewidth=0.5, height=0.65)
    ax1.set_yticks(range(len(biz_plot)))
    ax1.set_yticklabels(biz_plot['merchant_consolidated'].str[:22], fontsize=10, fontweight='bold')
    ax1.set_xlabel("% of Business Txns", fontsize=13, fontweight='bold', labelpad=8)
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)
    ax1.set_title("Business", fontsize=20, fontweight='bold',
                   color=GEN_COLORS['primary'], pad=12)

    for j, (_, row) in enumerate(biz_plot.iterrows()):
        ax1.text(row['pct'] + 0.2, j, f"{row['pct']:.1f}%",
                 va='center', fontsize=10, fontweight='bold', color=GEN_COLORS['primary'])

    # --- RIGHT: Personal ---
    per_plot = per_merch.sort_values('pct', ascending=True)
    ax2.barh(range(len(per_plot)), per_plot['pct'],
             color=GEN_COLORS['success'], edgecolor='white', linewidth=0.5, height=0.65)
    ax2.set_yticks(range(len(per_plot)))
    ax2.set_yticklabels(per_plot['merchant_consolidated'].str[:22], fontsize=10, fontweight='bold')
    ax2.set_xlabel("% of Personal Txns", fontsize=13, fontweight='bold', labelpad=8)
    ax2.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
    gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
    ax2.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax2.set_axisbelow(True)
    ax2.set_title("Personal", fontsize=20, fontweight='bold',
                   color=GEN_COLORS['success'], pad=12)

    for j, (_, row) in enumerate(per_plot.iterrows()):
        ax2.text(row['pct'] + 0.2, j, f"{row['pct']:.1f}%",
                 va='center', fontsize=10, fontweight='bold', color=GEN_COLORS['success'])

    fig.suptitle("Top Merchants: Business vs Personal",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.04)
    fig.text(0.5, 0.96, "Do business and personal accounts rely on different merchants?",
             ha='center', fontsize=15, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    plt.show()

    biz_set = set(biz_merch['merchant_consolidated'])
    per_set = set(per_merch['merchant_consolidated'])
    overlap = biz_set & per_set
    print(f"\n    Overlap: {len(overlap)} merchants in both top 10")
    if biz_set - per_set:
        print(f"    Business-only: {', '.join(sorted(biz_set - per_set))[:80]}")
    if per_set - biz_set:
        print(f"    Personal-only: {', '.join(sorted(per_set - biz_set))[:80]}")
else:
    print("No business_flag column. Skipping biz/personal merchant split.")
