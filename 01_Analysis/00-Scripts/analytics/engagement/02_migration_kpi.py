# ===========================================================================
# ENGAGEMENT MIGRATION KPI: 4-Card Dashboard (Conference Edition)
# ===========================================================================
# FancyBboxPatch cards: Net Direction, Stability Rate, Power Growth,
# Dormant Recovery. (18,5).

if 'migration_summary' not in dir() or not isinstance(migration_summary, pd.DataFrame) or len(migration_summary) == 0:
    print("    No migration data available. Skipping KPI dashboard.")
elif 'monthly_transitions' not in dir() or len(monthly_transitions) == 0:
    print("    No monthly transitions available. Skipping KPI dashboard.")
else:
    # KPI 1: Net migration direction (avg monthly)
    _avg_net = monthly_transitions['net_migration'].mean()
    _net_label = "Net Upgraders" if _avg_net > 0 else "Net Downgraders"
    _net_color = GEN_COLORS['success'] if _avg_net > 0 else GEN_COLORS['accent']

    # KPI 2: Average stability rate
    _avg_stability = monthly_transitions['stability_rate'].mean()

    # KPI 3: Power tier growth
    _power_row = migration_summary[migration_summary['tier'] == 'Power']
    _power_net = _power_row['net_change'].values[0] if len(_power_row) > 0 else 0
    _power_start = _power_row['start_count'].values[0] if len(_power_row) > 0 else 0
    _power_pct = _power_net / _power_start * 100 if _power_start > 0 else 0

    # KPI 4: Dormant recovery (dormant at start who upgraded by end)
    _dormant_start = migration_summary.loc[migration_summary['tier'] == 'Dormant', 'start_count'].values
    _dormant_start = _dormant_start[0] if len(_dormant_start) > 0 else 0
    _dormant_end = migration_summary.loc[migration_summary['tier'] == 'Dormant', 'end_count'].values
    _dormant_end = _dormant_end[0] if len(_dormant_end) > 0 else 0
    _dormant_recovered = max(0, _dormant_start - _dormant_end) if _dormant_start > _dormant_end else 0
    _recovery_rate = _dormant_recovered / _dormant_start * 100 if _dormant_start > 0 else 0

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))

    kpi_data = [
        {
            'label': _net_label + '/Month',
            'value': f"{abs(_avg_net):,.0f}",
            'sub': f"avg monthly net tier movement",
            'color': _net_color,
        },
        {
            'label': 'Tier Stability Rate',
            'value': f"{_avg_stability:.0f}%",
            'sub': "accounts staying in same tier month-over-month",
            'color': GEN_COLORS['info'],
        },
        {
            'label': 'Power Tier Growth',
            'value': f"{_power_pct:+.1f}%",
            'sub': f"net {_power_net:+,} Power accounts over period",
            'color': GEN_COLORS['success'] if _power_net > 0 else GEN_COLORS['warning'],
        },
        {
            'label': 'Dormant Recovery',
            'value': f"{_recovery_rate:.0f}%",
            'sub': f"{_dormant_recovered:,} dormant accounts reactivated",
            'color': GEN_COLORS['warning'],
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

    fig.suptitle("Engagement Migration Overview",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
    fig.text(0.5, GEN_SUBTITLE_Y, f"Are members becoming more or less engaged?  |  {DATASET_LABEL}",
             ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
