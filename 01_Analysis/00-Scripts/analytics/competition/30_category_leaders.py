# ===========================================================================
# CATEGORY LEADERS: Top Competitor in Each Category (Conference Edition)
# ===========================================================================
# Horizontal grouped bar chart showing the #1 competitor per category,
# sized by total spend, with market-share annotation.

if len(all_competitor_data) > 0 and len(summary_data) > 0:
    _sdf = pd.DataFrame(summary_data)
    # Filter out payment ecosystems
    _sdf = _sdf[~_sdf['category'].isin(PAYMENT_ECOSYSTEMS)].copy()
    _sdf['category_label'] = _sdf['category'].apply(clean_category)
    _sdf['norm_name'] = _sdf['competitor'].apply(normalize_competitor_name)

    # Roll up normalized names within each category
    _rolled = (
        _sdf.groupby(['category', 'category_label', 'norm_name'])
        .agg(
            total_amount=('total_amount', 'sum'),
            unique_accounts=('unique_accounts', 'sum'),
            total_transactions=('total_transactions', 'sum'),
        )
        .reset_index()
    )

    # Top competitor per category (by total spend)
    _top_idx = _rolled.groupby('category')['total_amount'].idxmax()
    _top = _rolled.loc[_top_idx].copy()

    # Category total spend for market-share %
    _cat_totals = _rolled.groupby('category')['total_amount'].sum()
    _top['cat_total'] = _top['category'].map(_cat_totals)
    _top['market_share'] = _top['total_amount'] / _top['cat_total'] * 100

    # Monthly normalization
    _n_months = DATASET_MONTHS if 'DATASET_MONTHS' in dir() else 1
    _top['spend_per_mo'] = _top['total_amount'] / _n_months

    # Sort by spend descending, flip for horizontal bar
    _top = _top.sort_values('total_amount', ascending=True)

    # Bar colors from palette
    _bar_colors = [get_cat_color(cl) for cl in _top['category_label']]

    # Shorten names
    _top['short_name'] = _top['norm_name'].apply(
        lambda n: n[:25] + '..' if len(str(n)) > 27 else n
    )
    # Cast to str — category_label can be a Categorical dtype which breaks
    # string concatenation (#81: "Object with dtype category cannot perform the numpy op add").
    _top['bar_label'] = (
        _top['short_name'].astype(str)
        + '\n('
        + _top['category_label'].astype(str)
        + ')'
    )

    fig, ax = plt.subplots(figsize=(14, max(7, len(_top) * 0.9)))

    bars = ax.barh(
        range(len(_top)),
        _top['total_amount'],
        color=_bar_colors,
        edgecolor='white',
        linewidth=1.5,
        height=0.65,
        zorder=3,
    )

    # Value labels
    for i, (_, row) in enumerate(_top.iterrows()):
        ax.text(
            row['total_amount'] * 1.02, i,
            f"${row['total_amount']:,.0f}  |  {row['market_share']:.0f}% of category  |  {row['unique_accounts']:,} accts",
            fontsize=11, fontweight='bold',
            color=GEN_COLORS['dark_text'], va='center',
        )

    ax.set_yticks(range(len(_top)))
    ax.set_yticklabels(_top['bar_label'], fontsize=12, fontweight='bold')
    ax.set_xlabel('Total Spend', fontsize=16, fontweight='bold', labelpad=12)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_dollar))

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
    ax.set_axisbelow(True)
    ax.set_xlim(0, _top['total_amount'].max() * 1.65)

    _ds_label = DATASET_LABEL if 'DATASET_LABEL' in dir() else ''
    ax.set_title(
        'Category Leaders',
        fontsize=26, fontweight='bold',
        color=GEN_COLORS['dark_text'], pad=20, loc='left',
    )
    ax.text(
        0.0, 0.97,
        f"Dominant competitor in each category  |  {_ds_label}",
        transform=ax.transAxes, fontsize=14,
        color=GEN_COLORS['muted'], style='italic',
    )

    plt.tight_layout()
    plt.show()

    # Text callout
    _biggest = _top.iloc[-1]
    print(f"\n    INSIGHT: {_biggest['norm_name']} leads {_biggest['category_label']} "
          f"with ${_biggest['total_amount']:,.0f} ({_biggest['market_share']:.0f}% share).")
