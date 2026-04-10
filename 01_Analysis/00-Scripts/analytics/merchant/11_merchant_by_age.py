# ===========================================================================
# MERCHANT BY AGE BAND: Where Each Generation Shops (Conference Edition)
# ===========================================================================
# Heatmap: top 12 merchants x member age band (% of age band txns). (14,8).
# Uses demo_df from general/11_demographic_data.

try:
    age_merch = demo_df[demo_df['age_band'].notna()].copy()

    top12_merchants = merch_agg.head(12)['merchant_consolidated'].tolist()
    age_merch_filtered = age_merch[age_merch['merchant_consolidated'].isin(top12_merchants)]

    merch_age_ct = pd.crosstab(
        age_merch_filtered['merchant_consolidated'],
        age_merch_filtered['age_band'],
        normalize='columns'
    ) * 100

    merch_age_ct = merch_age_ct[[b for b in AGE_ORDER if b in merch_age_ct.columns]]

    # Sort merchants by total share
    merch_order = merch_age_ct.sum(axis=1).sort_values(ascending=True).index
    merch_age_ct = merch_age_ct.reindex(merch_order)

    # Truncate names for display
    merch_age_ct.index = [n[:25] for n in merch_age_ct.index]

    fig, ax = plt.subplots(figsize=(14, 8))

    cmap = LinearSegmentedColormap.from_list('merch_heat', ['#FFFFFF', '#457B9D', '#1B2A4A'])

    sns.heatmap(
        merch_age_ct, annot=True, fmt='.1f', cmap=cmap,
        linewidths=2, linecolor='white',
        cbar_kws={'label': '% of Age Band Txns', 'shrink': 0.6},
        annot_kws={'fontsize': 11, 'fontweight': 'bold'},
        ax=ax
    )

    ax.set_xlabel('Member Age Band', fontsize=16, fontweight='bold', labelpad=10)
    ax.set_ylabel('Merchant', fontsize=16, fontweight='bold', labelpad=10)
    ax.set_xticklabels(ax.get_xticklabels(), fontsize=13, fontweight='bold', rotation=0)
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=11, fontweight='bold', rotation=0)

    ax.set_title("Top Merchant Usage by Age Group",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "Which merchants resonate with each generation?",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()

except NameError:
    print("demo_df not available. Run general/11_demographic_data first.")
