# ===========================================================================
# MATERIAL THREATS: Scatter -- Penetration vs Spend (Conference Edition)
# ===========================================================================
# Filters out noise (min thresholds) and plots the banks that actually
# matter: high penetration AND/OR high spend. Uses a quadrant layout
# with configurable thresholds.

if len(all_competitor_data) > 0:
    bank_categories = BANK_CATEGORIES
    total_accounts = combined_df['primary_account_num'].nunique()
    _n_months = DATASET_MONTHS if 'DATASET_MONTHS' in dir() else 1

    # Minimum thresholds to be considered "material"
    MIN_ACCOUNTS = 100
    MIN_SPEND = 50_000

    _rows = []
    for competitor, comp_txns in all_competitor_data.items():
        category = comp_txns['competitor_category'].iloc[0]
        if category not in bank_categories:
            continue

        _rows.append({
            'bank': normalize_competitor_name(competitor),
            'category': category,
            'total_spend': comp_txns['amount'].sum(),
            'unique_accounts': comp_txns['primary_account_num'].nunique(),
            'transactions': len(comp_txns),
        })

    if len(_rows) > 0:
        _mdf = pd.DataFrame(_rows)

        # Roll up normalized names
        _mdf = (
            _mdf.groupby(['bank', 'category'], as_index=False)
            .agg(
                total_spend=('total_spend', 'sum'),
                unique_accounts=('unique_accounts', 'sum'),
                transactions=('transactions', 'sum'),
            )
        )

        _mdf['penetration_pct'] = _mdf['unique_accounts'] / total_accounts * 100
        _mdf['spend_per_mo'] = _mdf['total_spend'] / _n_months
        _mdf['category_label'] = _mdf['category'].apply(clean_category)

        # Apply minimum thresholds
        _material = _mdf[
            (_mdf['unique_accounts'] >= MIN_ACCOUNTS) &
            (_mdf['total_spend'] >= MIN_SPEND)
        ].copy()

        if len(_material) > 0:
            # Quadrant thresholds (medians of material set)
            _pen_mid = _material['penetration_pct'].median()
            _spend_mid = _material['total_spend'].median()

            fig, ax = plt.subplots(figsize=(14, 9))

            # Quadrant shading
            ax.axhline(_spend_mid, color=GEN_COLORS['grid'], linewidth=1.5, linestyle='--', zorder=1)
            ax.axvline(_pen_mid, color=GEN_COLORS['grid'], linewidth=1.5, linestyle='--', zorder=1)

            # Scatter by category
            for cat_label in _material['category_label'].unique():
                _subset = _material[_material['category_label'] == cat_label]
                ax.scatter(
                    _subset['penetration_pct'],
                    _subset['total_spend'],
                    s=_subset['transactions'].clip(upper=5000) / 5 + 40,
                    color=get_cat_color(cat_label),
                    edgecolors='white',
                    linewidths=1.2,
                    alpha=0.85,
                    label=cat_label,
                    zorder=4,
                )

            # Label points
            for _, row in _material.iterrows():
                short = row['bank'][:18] + '..' if len(row['bank']) > 20 else row['bank']
                ax.annotate(
                    short,
                    (row['penetration_pct'], row['total_spend']),
                    fontsize=9, fontweight='bold',
                    color=GEN_COLORS['dark_text'],
                    textcoords='offset points', xytext=(6, 6),
                )

            # Quadrant labels
            _x_max = ax.get_xlim()[1]
            _y_max = ax.get_ylim()[1]
            ax.text(_pen_mid * 0.4, _y_max * 0.92, 'LOW PENETRATION\nHIGH SPEND',
                    fontsize=10, color=GEN_COLORS['muted'], ha='center', alpha=0.6)
            ax.text(_x_max * 0.85, _y_max * 0.92, 'HIGH PENETRATION\nHIGH SPEND',
                    fontsize=10, color=GEN_COLORS['accent'], ha='center', fontweight='bold', alpha=0.8)
            ax.text(_pen_mid * 0.4, _spend_mid * 0.3, 'LOW PENETRATION\nLOW SPEND',
                    fontsize=10, color=GEN_COLORS['muted'], ha='center', alpha=0.4)
            ax.text(_x_max * 0.85, _spend_mid * 0.3, 'HIGH PENETRATION\nLOW SPEND',
                    fontsize=10, color=GEN_COLORS['muted'], ha='center', alpha=0.6)

            ax.set_xlabel('Account Penetration (%)', fontsize=16, fontweight='bold', labelpad=12)
            ax.set_ylabel('Total Spend', fontsize=16, fontweight='bold', labelpad=12)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_dollar))
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.1f}%"))

            gen_clean_axes(ax, keep_left=True, keep_bottom=True)
            ax.grid(True, color=GEN_COLORS['grid'], linewidth=0.3, alpha=0.4)
            ax.set_axisbelow(True)

            ax.legend(fontsize=12, frameon=False, loc='upper left')

            _ds_label = DATASET_LABEL if 'DATASET_LABEL' in dir() else ''
            ax.set_title(
                'Material Competitive Threats',
                fontsize=26, fontweight='bold',
                color=GEN_COLORS['dark_text'], pad=20, loc='left',
            )
            ax.text(
                0.0, 0.97,
                f"Minimum: {MIN_ACCOUNTS:,} accounts and ${MIN_SPEND:,} spend  |  {_ds_label}",
                transform=ax.transAxes, fontsize=14,
                color=GEN_COLORS['muted'], style='italic',
            )

            plt.tight_layout()
            plt.show()

            # Top-right quadrant callout
            _top_right = _material[
                (_material['penetration_pct'] >= _pen_mid) &
                (_material['total_spend'] >= _spend_mid)
            ].sort_values('total_spend', ascending=False)

            if len(_top_right) > 0:
                print(f"\n    HIGHEST THREATS (top-right quadrant): {len(_top_right)} banks")
                for _, row in _top_right.head(5).iterrows():
                    print(f"      {row['bank']:30s}  {row['penetration_pct']:.1f}% penetration  "
                          f"${row['total_spend']:>12,.0f} spend  "
                          f"${row['spend_per_mo']:>10,.0f}/mo")
            print(f"\n    {len(_material)} banks pass material thresholds "
                  f"(of {len(_mdf)} total competitors).")
        else:
            print(f"No banks meet minimum thresholds ({MIN_ACCOUNTS:,} accounts, ${MIN_SPEND:,} spend)")
