# ===========================================================================
# BRANCH KPI DASHBOARD: Key Metrics at a Glance (Conference Edition)
# ===========================================================================
# 4 FancyBboxPatch cards. (18,5).

if 'br_agg' not in dir() or len(br_agg) == 0:
    print("    No branch data available. Skipping KPI dashboard.")
else:
    top_branch = br_agg.iloc[0]
    best_ticket = br_agg.loc[br_agg['avg_spend'].idxmax()]

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))

    kpi_data = [
        {
            'label': 'Total Branches',
            'value': f"{len(br_agg):,}",
            'sub': 'with transaction activity',
            'color': GEN_COLORS['accent'],
        },
        {
            'label': 'Largest Branch',
            'value': f"{top_branch['txn_pct']:.1f}%",
            'sub': f"Branch {str(top_branch['branch'])[:20]}",
            'color': GEN_COLORS['primary'],
        },
        {
            'label': 'Avg Txns / Branch',
            'value': f"{br_agg['txn_count'].mean():,.0f}",
            'sub': f"median {br_agg['txn_count'].median():,.0f}",
            'color': GEN_COLORS['info'],
        },
        {
            'label': 'Highest Avg Ticket',
            'value': f"${best_ticket['avg_spend']:.2f}",
            'sub': f"Branch {str(best_ticket['branch'])[:20]}",
            'color': GEN_COLORS['success'],
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

    fig.suptitle("Branch Geographic Overview",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.04)

    plt.tight_layout()
    plt.show()
