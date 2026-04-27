# ===========================================================================
# RELATIONSHIP VALUE: The Staircase Effect (Conference Edition)
# ===========================================================================
# How member value increases with each additional product held.
# X = products held, Y = avg balance / avg spend / avg tenure.

if 'rel_df' not in dir() or len(rel_df) == 0:
    print("    No relationship data available. Skipping relationship value chart.")
else:
    # ------------------------------------------------------------------
    # Aggregate metrics by product count
    # ------------------------------------------------------------------
    max_tier = min(rel_df['product_count'].max(), 6)
    value_df = rel_df.copy()
    value_df['product_group'] = value_df['product_count'].clip(upper=max_tier)
    value_df['product_group_label'] = value_df['product_group'].apply(
        lambda x: f"{x}+" if x == max_tier and max_tier < rel_df['product_count'].max()
        else str(int(x))
    )

    agg_dict = {
        'txn_count': 'mean',
        'total_spend': 'mean',
        'active_months': 'mean',
    }

    # Add balance if available
    bal_col = None
    if 'avg_bal' in value_df.columns and value_df['avg_bal'].notna().sum() > 0:
        agg_dict['avg_bal'] = 'mean'
        bal_col = 'avg_bal'
    elif 'curr_bal' in value_df.columns and value_df['curr_bal'].notna().sum() > 0:
        agg_dict['curr_bal'] = 'mean'
        bal_col = 'curr_bal'

    # Add tenure if available
    tenure_col = None
    if 'account_age' in value_df.columns and value_df['account_age'].notna().sum() > 0:
        agg_dict['account_age'] = 'mean'
        tenure_col = 'account_age'

    agg_dict['account_number'] = 'count'

    staircase = (
        value_df.groupby('product_group')
        .agg(agg_dict)
        .reset_index()
        .sort_values('product_group')
    )
    staircase.rename(columns={'account_number': 'member_count'}, inplace=True)

    # Determine which metrics to plot (up to 3 panels)
    panels = []

    if bal_col and staircase[bal_col].sum() > 0:
        panels.append({
            'col': bal_col,
            'title': 'Avg Balance',
            'formatter': gen_fmt_dollar,
            'color': GEN_COLORS['primary'],
        })

    panels.append({
        'col': 'total_spend',
        'title': f'Avg Spend ({DATASET_MONTHS}mo)',
        'formatter': gen_fmt_dollar,
        'color': GEN_COLORS['info'],
    })

    panels.append({
        'col': 'txn_count',
        'title': f'Avg Transactions ({DATASET_MONTHS}mo)',
        'formatter': gen_fmt_count,
        'color': GEN_COLORS['success'],
    })

    if tenure_col:
        panels.append({
            'col': tenure_col,
            'title': 'Avg Tenure',
            'formatter': gen_fmt_count,
            'color': GEN_COLORS['warning'],
        })

    # Limit to 3 panels
    panels = panels[:3]
    n_panels = len(panels)

    # ------------------------------------------------------------------
    # Multi-panel chart
    # ------------------------------------------------------------------
    fig, axes = plt.subplots(1, n_panels, figsize=(max(14, 5 * n_panels), 7))
    if n_panels == 1:
        axes = [axes]

    x_labels = [
        f"{int(g)}+" if g == max_tier else str(int(g))
        for g in staircase['product_group']
    ]

    for ax, panel in zip(axes, panels):
        values = staircase[panel['col']].values
        x_pos = range(len(values))

        bars = ax.bar(
            x_pos, values,
            color=panel['color'], edgecolor='white', linewidth=2,
            width=0.6, zorder=3, alpha=0.85
        )

        # Overlay line for staircase effect
        ax.plot(x_pos, values, color=panel['color'], linewidth=3,
                marker='o', markersize=10, markerfacecolor='white',
                markeredgecolor=panel['color'], markeredgewidth=2.5, zorder=4)

        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_labels, fontsize=15, fontweight='bold')
        ax.set_xlabel("Products Held", fontsize=15, fontweight='bold', labelpad=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(panel['formatter']))

        gen_clean_axes(ax)
        ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)

        ax.set_title(panel['title'], fontsize=18, fontweight='bold',
                     color=GEN_COLORS['dark_text'], pad=12)

        # Value labels on bars
        max_v = max(values) if len(values) > 0 else 1
        for i, v in enumerate(values):
            ax.text(i, v + max_v * 0.03, panel['formatter'](v, None),
                    ha='center', va='bottom', fontsize=14, fontweight='bold',
                    color=GEN_COLORS['dark_text'])

        ax.set_ylim(0, max_v * 1.2)

    # Compute value multiplier for suptitle
    base_spend = staircase.iloc[0]['total_spend'] if staircase.iloc[0]['total_spend'] > 0 else 1
    top_spend = staircase.iloc[-1]['total_spend']
    multiplier = top_spend / base_spend if base_spend > 0 else 0

    fig.suptitle("The Staircase Effect: More Products = More Value",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
    fig.text(0.01, 1.01,
             f"Each additional product adds significant member value  |  "
             f"Top-tier members worth {multiplier:.1f}x single-product  |  {DATASET_LABEL}",
             fontsize=16, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
