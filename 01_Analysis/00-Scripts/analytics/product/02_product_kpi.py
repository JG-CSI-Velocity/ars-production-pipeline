# ===========================================================================
# PRODUCT KPI DASHBOARD: Key Metrics at a Glance (Conference Edition)
# ===========================================================================
# 4 FancyBboxPatch cards. (18,5).

if 'prod_agg' not in dir() or len(prod_agg) == 0:
    print("    No product data available. Skipping KPI dashboard.")
else:
    top_prod = prod_agg.iloc[0]
    best_ticket_prod = prod_agg.loc[prod_agg['avg_spend'].idxmax()]
    most_accts_prod = prod_agg.loc[prod_agg['unique_accounts'].idxmax()]

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))

    kpi_data = [
        {
            'label': 'Total Products',
            'value': f"{len(prod_agg)}",
            'sub': 'distinct card products',
            'color': GEN_COLORS['primary'],
        },
        {
            'label': 'Dominant Product',
            'value': f"{top_prod['txn_pct']:.1f}%",
            'sub': top_prod['product_label'][:28],
            'color': GEN_COLORS['info'],
        },
        {
            'label': 'Highest Avg Ticket',
            'value': f"${best_ticket_prod['avg_spend']:.2f}",
            'sub': best_ticket_prod['product_label'][:28],
            'color': GEN_COLORS['success'],
        },
        {
            'label': 'Most Accounts',
            'value': f"{int(most_accts_prod['unique_accounts']):,}",
            'sub': most_accts_prod['product_label'][:28],
            'color': GEN_COLORS['accent'],
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
                ha='center', va='center', fontsize=12,
                color='white', alpha=0.8, style='italic')

    fig.suptitle("Card Product Overview",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)

    plt.tight_layout()
    plt.show()
