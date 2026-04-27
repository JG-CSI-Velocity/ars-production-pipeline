# ===========================================================================
# BALANCE KPI DASHBOARD: Key Metrics at a Glance (Conference Edition)
# ===========================================================================
# 4 FancyBboxPatch cards showing deposit health metrics.

fig, axes = plt.subplots(1, 4, figsize=(18, 5))

kpi_data = [
    {
        'label': 'Total Deposits',
        'value': gen_fmt_dollar(total_deposits, None),
        'sub': f"{total_accounts:,} accounts",
        'color': GEN_COLORS['primary'],
    },
    {
        'label': 'Average Balance',
        'value': gen_fmt_dollar(avg_balance, None),
        'sub': f"across all accounts",
        'color': GEN_COLORS['info'],
    },
    {
        'label': 'Zero-Balance Accts',
        'value': f"{zero_bal_pct:.1f}%",
        'sub': f"{zero_bal_count:,} accounts at $0",
        'color': GEN_COLORS['accent'],
    },
    {
        'label': 'Median Balance',
        'value': gen_fmt_dollar(median_balance, None),
        'sub': 'typical member balance',
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

fig.suptitle("Deposit Portfolio Overview",
             fontsize=28, fontweight='bold',
             color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)

plt.tight_layout()
plt.show()
