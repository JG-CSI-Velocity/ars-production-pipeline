# ===========================================================================
# MCC BY ACCOUNT AGE: New vs Mature Account Categories (Conference Edition)
# ===========================================================================
# Heatmap: top 12 MCC x account age band. (14,8).
# Uses lifecycle_df from general/23_account_age_data.

if 'mcc_agg' not in dir() or len(mcc_agg) == 0:
    print("    No MCC data available. Skipping MCC by account age heatmap.")
elif 'lifecycle_df' not in dir() or len(lifecycle_df) == 0:
    print("    No lifecycle data available. Skipping MCC by account age heatmap.")
elif 'mcc_code' not in combined_df.columns:
    print("    No mcc_code column available. Skipping MCC by account age heatmap.")
else:
    lifecycle_mcc = lifecycle_df[lifecycle_df['acct_age_band'].notna()].copy()

    # Merge MCC from combined_df transactions
    acct_mcc = combined_df[['primary_account_num', 'mcc_code']].copy()
    acct_mcc.columns = ['account_number', 'mcc_code']

    lc_mcc = lifecycle_mcc[['account_number', 'acct_age_band']].drop_duplicates()
    lc_mcc_txns = acct_mcc.merge(lc_mcc, on='account_number', how='inner')

    # Top 12 MCCs
    top12_codes_lc = mcc_agg.head(12)['mcc_code'].tolist()
    lc_mcc_filtered = lc_mcc_txns[lc_mcc_txns['mcc_code'].isin(top12_codes_lc)]

    if len(lc_mcc_filtered) == 0:
        print("    No account-age-matched MCC data available. Skipping heatmap.")
    else:
        # Cross-tab: MCC x account age band, normalized per band
        mcc_acctage_ct = pd.crosstab(
            lc_mcc_filtered['mcc_code'],
            lc_mcc_filtered['acct_age_band'],
            normalize='columns'
        ) * 100

        # Ensure order
        mcc_acctage_ct = mcc_acctage_ct[[b for b in ACCT_AGE_ORDER if b in mcc_acctage_ct.columns]]

        if mcc_acctage_ct.empty or mcc_acctage_ct.shape[0] == 0 or mcc_acctage_ct.shape[1] == 0:
            print("    Empty MCC x account age cross-tab. Skipping heatmap.")
        else:
            # Sort MCCs by total
            mcc_order_lc = mcc_acctage_ct.sum(axis=1).sort_values(ascending=True).index
            mcc_acctage_ct = mcc_acctage_ct.reindex(mcc_order_lc)

            fig, ax = plt.subplots(figsize=(14, 8))

            cmap = LinearSegmentedColormap.from_list('acct_heat', ['#FFFFFF', '#FF9F1C', '#E63946'])

            sns.heatmap(
                mcc_acctage_ct, annot=True, fmt='.1f', cmap=cmap,
                linewidths=2, linecolor='white',
                cbar_kws={'label': '% of Account Age Band Txns', 'shrink': 0.6},
                annot_kws={'fontsize': 11, 'fontweight': 'bold'},
                ax=ax
            )

            ax.set_xlabel('Account Age Band', fontsize=16, fontweight='bold', labelpad=10)
            ax.set_ylabel('MCC Code', fontsize=16, fontweight='bold', labelpad=10)
            ax.set_xticklabels(ax.get_xticklabels(), fontsize=11, fontweight='bold', rotation=45, ha='right')
            ax.set_yticklabels(ax.get_yticklabels(), fontsize=13, fontweight='bold', rotation=0)

            ax.set_title("MCC Usage: New vs Mature Accounts",
                         fontsize=26, fontweight='bold',
                         color=GEN_COLORS['dark_text'], pad=35, loc='left')
            ax.text(0.0, 1.02, "Do new accounts use different merchant categories than established ones?",
                    transform=ax.transAxes, fontsize=15,
                    color=GEN_COLORS['muted'], style='italic')

            plt.tight_layout()
            plt.show()
