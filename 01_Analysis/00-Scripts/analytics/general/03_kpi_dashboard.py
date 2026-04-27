# ===========================================================================
# KPI DASHBOARD: Portfolio at a Glance (Conference Edition)
# ===========================================================================
# 4 bold cards. No tables, no dollars.

kpis = [
    (f"{portfolio_kpis['total_accounts']:,}", "Active\nAccounts",
     GEN_COLORS['primary']),
    (f"{portfolio_kpis['avg_monthly_txns']:,.0f}", "Avg Monthly\nTransactions",
     GEN_COLORS['info']),
    (f"{portfolio_kpis['latest_txn_growth']:+.1f}%", "MoM Transaction\nGrowth",
     GEN_COLORS['success'] if portfolio_kpis['latest_txn_growth'] >= 0 else GEN_COLORS['accent']),
    (f"{portfolio_kpis['total_merchants']:,}", "Unique\nMerchants",
     GEN_COLORS['warning']),
]

fig, axes = plt.subplots(1, 4, figsize=(18, 5))
fig.patch.set_facecolor('#FFFFFF')

for ax, (value, label, color) in zip(axes, kpis):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    card = FancyBboxPatch(
        (0.03, 0.05), 0.94, 0.90,
        boxstyle="round,pad=0.05",
        facecolor=color, alpha=0.08,
        edgecolor=color, linewidth=2.5
    )
    ax.add_patch(card)

    ax.text(0.5, 0.62, value, transform=ax.transAxes,
            fontsize=48, fontweight='bold', color=color,
            ha='center', va='center')

    ax.text(0.5, 0.20, label, transform=ax.transAxes,
            fontsize=15, fontweight='bold', color=GEN_COLORS['dark_text'],
            ha='center', va='center', linespacing=1.4)

fig.suptitle("Portfolio at a Glance",
             fontsize=28, fontweight='bold',
             color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)

plt.tight_layout()
plt.show()
