# ===========================================================================
# MCC BY AGE BAND: Where Each Generation Spends (Conference Edition)
# ===========================================================================
# Heatmap: top 12 MCC x age band (% of age band's txns). (14,8).
# Uses demo_df from general/11_demographic_data.

if 'mcc_agg' not in dir() or len(mcc_agg) == 0:
    print("    No MCC data available. Skipping MCC by age band heatmap.")
elif 'mcc_code' not in combined_df.columns:
    print("    No mcc_code column available. Skipping MCC by age band heatmap.")
else:
    age_matched_mcc = demo_df[demo_df['age_band'].notna()].copy()

    # Top 12 MCCs overall
    top12_codes = mcc_agg.head(12)['mcc_code'].tolist()
    age_mcc_data = age_matched_mcc[age_matched_mcc['mcc_code'].isin(top12_codes)]

    # Cross-tab: MCC x age band, normalized per age band (column %)
    if len(age_mcc_data) == 0:
        print("    No age-matched MCC data available. Skipping MCC by age band heatmap.")
    else:
        mcc_age_ct = pd.crosstab(
            age_mcc_data['mcc_code'],
            age_mcc_data['age_band'],
            normalize='columns'
        ) * 100

        # Ensure age band order
        mcc_age_ct = mcc_age_ct[[b for b in AGE_ORDER if b in mcc_age_ct.columns]]

        if mcc_age_ct.empty or mcc_age_ct.shape[0] == 0 or mcc_age_ct.shape[1] == 0:
            print("    Empty MCC x age band cross-tab. Skipping heatmap.")
        else:
            # Sort MCCs by total share
            mcc_order = mcc_age_ct.sum(axis=1).sort_values(ascending=True).index
            mcc_age_ct = mcc_age_ct.reindex(mcc_order)

            fig, ax = plt.subplots(figsize=(14, 8))

            cmap = LinearSegmentedColormap.from_list('mcc_heat', ['#FFFFFF', '#457B9D', '#1B2A4A'])

            sns.heatmap(
                mcc_age_ct, annot=True, fmt='.1f', cmap=cmap,
                linewidths=2, linecolor='white',
                cbar_kws={'label': '% of Age Band Txns', 'shrink': 0.6},
                annot_kws={'fontsize': 12, 'fontweight': 'bold'},
                ax=ax
            )

            ax.set_xlabel('Member Age Band', fontsize=16, fontweight='bold', labelpad=10)
            ax.set_ylabel('MCC Code', fontsize=16, fontweight='bold', labelpad=10)
            ax.set_xticklabels(ax.get_xticklabels(), fontsize=13, fontweight='bold', rotation=0)
            ax.set_yticklabels(ax.get_yticklabels(), fontsize=13, fontweight='bold', rotation=0)

            ax.set_title("MCC Category Usage by Age Group",
                         fontsize=26, fontweight='bold',
                         color=GEN_COLORS['dark_text'], pad=35, loc='left')
            ax.text(0.0, 1.02, "Which merchant categories resonate with each generation?",
                    transform=ax.transAxes, fontsize=15,
                    color=GEN_COLORS['muted'], style='italic')

            plt.tight_layout()
            plt.show()
