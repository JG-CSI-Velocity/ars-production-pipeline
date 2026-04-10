# ===========================================================================
# PERSONAL BY AGE BAND: Where Each Generation Shops (Conference Edition)
# ===========================================================================
# Heatmap: top 12 personal merchants x member age band. (14,8).
# Uses demo_df from general/11_demographic_data, filtered to personal accounts.

try:
    # Filter to personal accounts with age data -- select only needed columns
    _needed_cols = ['merchant_consolidated', 'age_band']
    age_merch_p = demo_df.loc[
        (demo_df['business_flag'] == 'No') & (demo_df['age_band'].notna()),
        _needed_cols
    ]

    top12_pers_m = pers_agg.head(12)['merchant_consolidated'].tolist()
    age_merch_filtered_p = age_merch_p[age_merch_p['merchant_consolidated'].isin(top12_pers_m)]

    if len(age_merch_filtered_p) == 0:
        print("    No personal age-band data available. Skipping heatmap.")
    else:
        merch_age_ct_p = pd.crosstab(
            age_merch_filtered_p['merchant_consolidated'],
            age_merch_filtered_p['age_band'],
            normalize='columns'
        ) * 100

        merch_age_ct_p = merch_age_ct_p[[b for b in AGE_ORDER if b in merch_age_ct_p.columns]]

        if merch_age_ct_p.empty:
            print("    Empty crosstab. Skipping heatmap.")
        else:
            # Sort merchants by total share
            merch_order_p = merch_age_ct_p.sum(axis=1).sort_values(ascending=True).index
            merch_age_ct_p = merch_age_ct_p.reindex(merch_order_p)

            # Truncate names for display
            merch_age_ct_p.index = [n[:25] for n in merch_age_ct_p.index]

            fig, ax = plt.subplots(figsize=(14, 8))

            cmap = LinearSegmentedColormap.from_list('pers_heat', ['#FFFFFF', '#2EC4B6', '#1B2A4A'])

            sns.heatmap(
                merch_age_ct_p, annot=True, fmt='.1f', cmap=cmap,
                linewidths=2, linecolor='white',
                cbar_kws={'label': '% of Age Band Txns', 'shrink': 0.6},
                annot_kws={'fontsize': 11, 'fontweight': 'bold'},
                ax=ax
            )

            ax.set_xlabel('Member Age Band', fontsize=16, fontweight='bold', labelpad=10)
            ax.set_ylabel('Merchant', fontsize=16, fontweight='bold', labelpad=10)
            ax.set_xticklabels(ax.get_xticklabels(), fontsize=13, fontweight='bold', rotation=0)
            ax.set_yticklabels(ax.get_yticklabels(), fontsize=11, fontweight='bold', rotation=0)

            ax.set_title("Personal Merchant Usage by Age Group",
                         fontsize=26, fontweight='bold',
                         color=GEN_COLORS['dark_text'], pad=35, loc='left')
            ax.text(0.0, 1.02, "Which merchants resonate with each generation? (personal accounts only)",
                    transform=ax.transAxes, fontsize=15,
                    color=GEN_COLORS['muted'], style='italic')

            plt.tight_layout()
            plt.show()

except NameError:
    print("    demo_df not available. Run general/11_demographic_data first.")
