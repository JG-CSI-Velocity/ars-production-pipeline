# ===========================================================================
# RETENTION KPI: 4-Card Dashboard (Conference Edition)
# ===========================================================================
# FancyBboxPatch cards: Closed Rate, Avg Tenure, At-Risk Count, Attrition $.
# (18,5).

if 'retention_df' not in dir() or len(retention_df) == 0:
    print("    No retention data available. Skipping KPI dashboard.")
else:
    _total = len(retention_df)

    # KPI 1: Closed account rate
    _closed = (retention_df['health_status'] == 'Closed').sum()
    _closed_rate = _closed / _total * 100 if _total > 0 else 0

    # KPI 2: Avg tenure at close (months)
    _closed_df = retention_df[retention_df['health_status'] == 'Closed']
    _avg_tenure = _closed_df['tenure_months'].mean() if len(_closed_df) > 0 and retention_df['tenure_months'].notna().any() else 0

    # KPI 3: At-risk accounts (declining + cooling + dormant)
    _at_risk = retention_df['health_status'].isin(['Declining', 'Cooling', 'Dormant']).sum()

    # KPI 4: Estimated annual attrition revenue
    _attrition_rev = _closed_df['pre_close_monthly_spend'].sum() * 12 if len(_closed_df) > 0 else 0

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))

    kpi_data = [
        {
            'label': 'Closed Account Rate',
            'value': f"{_closed_rate:.1f}%",
            'sub': f"{_closed:,} of {_total:,} accounts",
            'color': GEN_COLORS['accent'],
        },
        {
            'label': 'Avg Tenure at Close',
            'value': f"{_avg_tenure:.0f} mo" if _avg_tenure > 0 else "N/A",
            'sub': "months from open to close",
            'color': GEN_COLORS['info'],
        },
        {
            'label': 'At-Risk Accounts',
            'value': f"{_at_risk:,}",
            'sub': f"declining + cooling + dormant ({_at_risk / _total * 100:.1f}%)",
            'color': GEN_COLORS['warning'],
        },
        {
            'label': 'Est. Annual Attrition $',
            'value': f"${_attrition_rev:,.0f}",
            'sub': "annualized spend lost from closed accounts",
            'color': GEN_COLORS['primary'],
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
                ha='center', va='center', fontsize=11,
                color='white', alpha=0.8, style='italic')

    fig.suptitle("Retention & Churn Overview",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
    fig.text(0.5, GEN_SUBTITLE_Y, f"Account health classification  |  {DATASET_LABEL}",
             ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
