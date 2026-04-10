# ===========================================================================
# BUSINESS KPI DASHBOARD: Key Metrics at a Glance (Conference Edition)
# ===========================================================================
# 4 FancyBboxPatch cards. (18,5).

if 'biz_agg' not in dir() or len(biz_agg) == 0:
    print("    No business data available. Skipping KPI dashboard.")
else:
    fig, axes = plt.subplots(1, 4, figsize=(18, 5))

    kpi_data = [
        {
            'label': 'Business Merchants',
            'value': f"{len(biz_agg):,}",
            'sub': 'unique consolidated names',
            'color': GEN_COLORS['primary'],
        },
        {
            'label': 'Top 10 Share',
            'value': f"{top10_share_biz:.1f}%",
            'sub': 'of business transactions',
            'color': GEN_COLORS['info'],
        },
        {
            'label': 'Avg Txns / Merchant',
            'value': f"{biz_agg['txn_count'].mean():.0f}",
            'sub': f"median {biz_agg['txn_count'].median():.0f}",
            'color': GEN_COLORS['success'],
        },
        {
            'label': '#1 Merchant',
            'value': f"{biz_agg.iloc[0]['txn_pct']:.1f}%",
            'sub': biz_agg.iloc[0]['merchant_consolidated'][:28],
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

    fig.suptitle("Business Account Portfolio Overview",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.04)

    plt.tight_layout()
    plt.show()
