# ===========================================================================
# MCC SEASONAL PATTERNS: Monthly Index by Category (Conference Edition)
# ===========================================================================
# Heatmap: top 10 MCCs x calendar month, indexed to average=100. (14,8).
# Shows which categories spike in which months.

if 'mcc_agg' not in dir() or len(mcc_agg) == 0:
    print("    No MCC data available. Skipping seasonal patterns.")
elif 'mcc_code' not in combined_df.columns:
    print("    No mcc_code column available. Skipping seasonal patterns.")
else:
    # Monthly txn counts for top 10 MCCs
    top10_monthly = combined_df[combined_df['mcc_code'].isin(top10_codes)]

    if len(top10_monthly) == 0:
        print("    No transactions for top 10 MCCs. Skipping seasonal patterns.")
    else:
        _top10_m = top10_monthly.copy()
        _top10_m['month_num'] = _top10_m['transaction_date'].dt.month

        mcc_month_ct = pd.crosstab(
            _top10_m['mcc_code'],
            _top10_m['month_num']
        )

        if mcc_month_ct.empty:
            print("    Empty seasonal cross-tab. Skipping.")
        else:
            # Index to average = 100 (each MCC's row average)
            row_means = mcc_month_ct.mean(axis=1)
            # Guard against zero-mean rows
            row_means = row_means.replace(0, 1)
            mcc_month_idx = mcc_month_ct.div(row_means, axis=0) * 100

            # Rename columns to month abbreviations
            import calendar
            month_labels = {i: calendar.month_abbr[i] for i in range(1, 13)}
            mcc_month_idx.columns = [month_labels.get(c, c) for c in mcc_month_idx.columns]

            # Sort MCCs by variance (most seasonal at top)
            mcc_month_idx['variance'] = mcc_month_idx.var(axis=1)
            mcc_month_idx = mcc_month_idx.sort_values('variance', ascending=False)
            mcc_month_idx = mcc_month_idx.drop(columns='variance')

            fig, ax = plt.subplots(figsize=(14, 8))

            # Diverging colormap centered on 100
            cmap = LinearSegmentedColormap.from_list(
                'seasonal', ['#457B9D', '#FFFFFF', '#E63946']
            )

            sns.heatmap(
                mcc_month_idx, annot=True, fmt='.0f', cmap=cmap,
                center=100, vmin=50, vmax=150,
                linewidths=2, linecolor='white',
                cbar_kws={'label': 'Seasonal Index (100 = Average)', 'shrink': 0.6},
                annot_kws={'fontsize': 11, 'fontweight': 'bold'},
                ax=ax
            )

            ax.set_xlabel('Month', fontsize=16, fontweight='bold', labelpad=10)
            ax.set_ylabel('MCC Code', fontsize=16, fontweight='bold', labelpad=10)
            ax.set_xticklabels(ax.get_xticklabels(), fontsize=13, fontweight='bold', rotation=0)
            ax.set_yticklabels(ax.get_yticklabels(), fontsize=13, fontweight='bold', rotation=0)

            ax.set_title("MCC Seasonal Patterns",
                         fontsize=26, fontweight='bold',
                         color=GEN_COLORS['dark_text'], pad=35, loc='left')
            ax.text(0.0, 1.02, "Which categories spike in which months? (100 = category average)",
                    transform=ax.transAxes, fontsize=15,
                    color=GEN_COLORS['muted'], style='italic')

            plt.tight_layout()
            plt.show()
