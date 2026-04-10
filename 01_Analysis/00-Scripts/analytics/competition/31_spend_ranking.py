# ===========================================================================
# SPEND RANKING: Top 15 Banks by Total Spend (Conference Edition)
# ===========================================================================
# Horizontal bar chart -- follow the money. Which banks are capturing
# the most dollar volume from your members?

if len(all_competitor_data) > 0:
    bank_categories = BANK_CATEGORIES
    total_accounts = combined_df['primary_account_num'].nunique()
    _n_months = DATASET_MONTHS if 'DATASET_MONTHS' in dir() else 1

    _spend_rows = []

    for competitor, comp_txns in all_competitor_data.items():
        category = comp_txns['competitor_category'].iloc[0]
        if category not in bank_categories:
            continue

        _spend_rows.append({
            'bank': normalize_competitor_name(competitor),
            'category': category,
            'total_spend': comp_txns['amount'].sum(),
            'unique_accounts': comp_txns['primary_account_num'].nunique(),
            'transactions': len(comp_txns),
        })

    if len(_spend_rows) > 0:
        _sdf = pd.DataFrame(_spend_rows)

        # Roll up normalized names
        _sdf = (
            _sdf.groupby(['bank', 'category'], as_index=False)
            .agg(
                total_spend=('total_spend', 'sum'),
                unique_accounts=('unique_accounts', 'sum'),
                transactions=('transactions', 'sum'),
            )
        )

        _sdf['spend_per_mo'] = _sdf['total_spend'] / _n_months
        _sdf['avg_txn'] = _sdf['total_spend'] / _sdf['transactions']
        _sdf['category_label'] = _sdf['category'].apply(clean_category)

        _top15 = _sdf.sort_values('total_spend', ascending=False).head(15)
        _plot = _top15.iloc[::-1]  # flip for barh (top at top)

        _bar_colors = [get_cat_color(cl) for cl in _plot['category_label']]

        _plot['short_name'] = _plot['bank'].apply(
            lambda n: n[:25] + '..' if len(str(n)) > 27 else n
        )

        fig, ax = plt.subplots(figsize=(14, 9))

        ax.barh(
            range(len(_plot)),
            _plot['total_spend'],
            color=_bar_colors,
            edgecolor='white',
            linewidth=1,
            height=0.65,
            zorder=3,
        )

        for i, (_, row) in enumerate(_plot.iterrows()):
            ax.text(
                row['total_spend'] * 1.02, i,
                f"${row['total_spend']:,.0f}  ({row['unique_accounts']:,} accts, ${row['avg_txn']:,.0f} avg)",
                fontsize=11, fontweight='bold',
                color=GEN_COLORS['dark_text'], va='center',
            )

        ax.set_yticks(range(len(_plot)))
        ax.set_yticklabels(_plot['short_name'], fontsize=13, fontweight='bold')
        ax.set_xlabel('Total Spend', fontsize=16, fontweight='bold', labelpad=12)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_dollar))

        gen_clean_axes(ax, keep_left=True, keep_bottom=True)
        ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
        ax.set_axisbelow(True)
        ax.set_xlim(0, _plot['total_spend'].max() * 1.55)

        # Legend
        _legend_cats = _plot['category_label'].unique()
        _handles = [
            plt.Rectangle((0, 0), 1, 1, fc=get_cat_color(c), edgecolor='white', label=c)
            for c in _legend_cats
        ]
        ax.legend(handles=_handles, loc='lower right', fontsize=12, frameon=False)

        _ds_label = DATASET_LABEL if 'DATASET_LABEL' in dir() else ''
        ax.set_title(
            'Top 15 Banks by Total Spend',
            fontsize=26, fontweight='bold',
            color=GEN_COLORS['dark_text'], pad=20, loc='left',
        )
        ax.text(
            0.0, 0.97,
            f"Follow the money -- where is spend going?  |  {_ds_label}",
            transform=ax.transAxes, fontsize=14,
            color=GEN_COLORS['muted'], style='italic',
        )

        plt.tight_layout()
        plt.show()

        # Callout
        _top3_spend = _top15.head(3)['total_spend'].sum()
        _all_spend = _sdf['total_spend'].sum()
        print(f"\n    INSIGHT: Top 3 banks capture ${_top3_spend:,.0f} "
              f"({_top3_spend / _all_spend * 100:.0f}% of all competitor bank spend).")
        print(f"    Monthly run rate: ${_top15.head(3)['spend_per_mo'].sum():,.0f}/mo across top 3.")
