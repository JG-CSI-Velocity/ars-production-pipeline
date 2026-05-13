# ===========================================================================
# RELATIONSHIP KPI DASHBOARD: 4-Card Relationship Health (Conference Edition)
# ===========================================================================
# Cards: Avg Products, % Single-Product, % 3+ Products, Balance Multiplier

if 'rel_df' not in dir() or len(rel_df) == 0:
    print("    No relationship data available. Skipping KPI dashboard.")
else:
    total_members = len(rel_df)
    avg_products = rel_df['product_count'].mean()
    single_pct = (rel_df['product_count'] == 1).mean() * 100
    three_plus_pct = (rel_df['product_count'] >= 3).mean() * 100

    # Balance comparison: 3+ products vs 1 product
    bal_col = None
    if 'avg_bal' in rel_df.columns and rel_df['avg_bal'].notna().sum() > 0:
        bal_col = 'avg_bal'
    elif 'curr_bal' in rel_df.columns and rel_df['curr_bal'].notna().sum() > 0:
        bal_col = 'curr_bal'

    if bal_col:
        avg_bal_single = rel_df.loc[rel_df['product_count'] == 1, bal_col].mean()
        avg_bal_3plus = rel_df.loc[rel_df['product_count'] >= 3, bal_col].mean()
        if avg_bal_single > 0:
            bal_multiplier = avg_bal_3plus / avg_bal_single
            bal_label = f"{bal_multiplier:.1f}x"
            bal_sub = f"3+ products vs single-product balance"
        else:
            bal_label = f"${avg_bal_3plus:,.0f}"
            bal_sub = "avg balance, 3+ product members"
    else:
        # Fallback: use spend as proxy
        avg_spend_single = rel_df.loc[rel_df['product_count'] == 1, 'total_spend'].mean()
        avg_spend_3plus = rel_df.loc[rel_df['product_count'] >= 3, 'total_spend'].mean()
        if avg_spend_3plus > 0 and avg_spend_single > 0:
            bal_multiplier = avg_spend_3plus / avg_spend_single
            bal_label = f"{bal_multiplier:.1f}x"
            bal_sub = "3+ products vs single-product spend"
        else:
            bal_label = "N/A"
            bal_sub = "insufficient data"

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))

    kpi_data = [
        {
            'label': 'Avg Products/Member',
            'value': f"{avg_products:.1f}",
            'sub': f"across {total_members:,} members",
            'color': GEN_COLORS['primary'],
        },
        {
            'label': 'Single-Product Members',
            'value': f"{single_pct:.0f}%",
            'sub': f"{int(rel_df['product_count'].eq(1).sum()):,} members at flight risk",
            'color': GEN_COLORS['accent'],
        },
        {
            'label': 'Members with 3+ Products',
            'value': f"{three_plus_pct:.0f}%",
            'sub': f"{int((rel_df['product_count'] >= 3).sum()):,} sticky members",
            'color': GEN_COLORS['success'],
        },
        {
            'label': 'Value Multiplier',
            'value': bal_label,
            'sub': bal_sub,
            'color': GEN_COLORS['info'],
        },
    ]

    for ax, kpi in zip(axes, kpi_data):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')

        card = FancyBboxPatch(
            (0.3, 0.3), 9.4, 9.4,
            boxstyle="round,pad=0.3",
            facecolor=kpi['color'], edgecolor='white', linewidth=3
        )
        ax.add_patch(card)

        ax.text(5, 6.8, kpi['label'],
                ha='center', va='center', fontsize=14, fontweight='bold',
                color='white', alpha=0.85)
        ax.text(5, 4.5, kpi['value'],
                ha='center', va='center', fontsize=42, fontweight='bold',
                color='white',
                path_effects=[pe.withStroke(linewidth=2, foreground=kpi['color'])])
        ax.text(5, 2.3, kpi['sub'],
                ha='center', va='center', fontsize=14,
                color='white', alpha=0.8, style='italic')

    fig.suptitle("Member Relationship Depth",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
    fig.text(0.01, GEN_SUBTITLE_Y,
             f"Single-product members are 3x more likely to leave  |  {DATASET_LABEL}",
             fontsize=14, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
