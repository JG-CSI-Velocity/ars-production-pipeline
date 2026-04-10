# ===========================================================================
# BRANCH MERCHANT HEATMAP: Geographic Preferences (Conference Edition)
# ===========================================================================
# Heatmap: top 8 branches x top 10 merchants (txn share). (14,8).

if 'br_agg' not in dir() or len(br_agg) == 0:
    print("    No branch data available. Skipping merchant heatmap.")
else:
    top8_branches = br_agg.head(8)['branch'].tolist()
    top10_merchants_br = combined_df['merchant_consolidated'].value_counts().head(10).index.tolist()

    br_heat_df = br_df[
        (br_df['branch'].isin(top8_branches)) &
        (br_df['merchant_consolidated'].isin(top10_merchants_br))
    ]

    br_merch_pivot = pd.crosstab(
        br_heat_df['branch'],
        br_heat_df['merchant_consolidated'],
        normalize='index'
    ) * 100

    # Sort branches by total volume
    branch_order = [b for b in top8_branches if b in br_merch_pivot.index]
    br_merch_pivot = br_merch_pivot.loc[branch_order]

    # Truncate merchant names
    br_merch_pivot.columns = [m[:20] for m in br_merch_pivot.columns]

    fig, ax = plt.subplots(figsize=(14, 8))

    br_cmap = LinearSegmentedColormap.from_list('br_heat',
        ['#FFFFFF', GEN_COLORS['accent'], GEN_COLORS['primary']])

    sns.heatmap(br_merch_pivot, annot=True, fmt='.1f', cmap=br_cmap,
                linewidths=1, linecolor='white', cbar_kws={'label': '% of Branch Txns'},
                ax=ax, annot_kws={'fontsize': 10, 'fontweight': 'bold'})

    ax.set_xlabel("Merchant", fontsize=13, fontweight='bold', labelpad=8)
    ax.set_ylabel("Branch", fontsize=13, fontweight='bold', labelpad=8)
    ax.tick_params(axis='x', rotation=45, labelsize=10)
    ax.tick_params(axis='y', rotation=0, labelsize=11)

    ax.set_title("Branch Merchant Preferences",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "Do different branches have different merchant spending patterns?",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
