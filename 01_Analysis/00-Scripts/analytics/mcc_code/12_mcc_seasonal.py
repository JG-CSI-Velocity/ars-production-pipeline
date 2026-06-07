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

        # Window the crosstab to the LAST 12 COMPLETE MONTHS so each
        # calendar month appears exactly once. Without this, multi-year
        # data summed Jan-2024 + Jan-2025 into a single Jan column,
        # inflating January's seasonal index vs months that only
        # appeared once. Policy decision 2026-06-07 (option c: trim
        # rather than per-year averaging).
        _max_date = _top10_m['transaction_date'].max()
        # Last complete month is the month before _max_date's month --
        # _max_date itself may be partial.
        _last_complete = (_max_date.replace(day=1) - pd.Timedelta(days=1))
        # Window start is 11 months back from _last_complete's month start.
        _window_start = (
            _last_complete.replace(day=1)
            - pd.DateOffset(months=11)
        )
        _window_mask = (
            (_top10_m['transaction_date'] >= _window_start) &
            (_top10_m['transaction_date'] <= _last_complete)
        )
        _windowed = _top10_m[_window_mask]

        if _windowed.empty:
            print(
                f"    Less than one complete month of data "
                f"(max date {_max_date.date()}). Skipping seasonal patterns."
            )
            mcc_month_ct = pd.DataFrame()
        else:
            _windowed = _windowed.copy()
            _windowed['month_num'] = _windowed['transaction_date'].dt.month
            mcc_month_ct = pd.crosstab(
                _windowed['mcc_code'],
                _windowed['month_num'],
            )
            _seasonal_window_label = (
                f"{_window_start.strftime('%b %Y')} -- "
                f"{_last_complete.strftime('%b %Y')}"
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
            ax.text(
                0.0, 1.02,
                f"Which categories spike in which months? "
                f"(100 = category average)  |  Window: {_seasonal_window_label}",
                transform=ax.transAxes, fontsize=15,
                color=GEN_COLORS['muted'], style='italic',
            )

            plt.tight_layout()
            plt.show()
