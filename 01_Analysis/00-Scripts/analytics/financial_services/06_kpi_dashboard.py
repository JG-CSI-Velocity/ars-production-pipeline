# ===========================================================================
# KPI DASHBOARD: Financial Services Leakage at a Glance
# ===========================================================================

total_members = combined_df['primary_account_num'].nunique()
leaking_members = len(multi_product_df)
pct_leaking = (leaking_members / total_members * 100) if total_members > 0 else 0
multi_product_count = len(multi_product_df[multi_product_df['category_count'] >= 2])
pct_multi = (multi_product_count / total_members * 100) if total_members > 0 else 0
avg_categories = multi_product_df['category_count'].mean()
active_30d = len(multi_product_df[multi_product_df['recency_days'] <= 30])

kpis = [
    (f"{pct_leaking:.1f}%",     "of Account Holders Pay\nExternal FinServ",   GEN_COLORS['accent']),
    (f"{len(financial_services_data)}", "Product Categories\nDetected",  GEN_COLORS['info']),
    (f"{avg_categories:.1f}",   "Avg External Services\nper Account Holder",  GEN_COLORS['warning']),
    (f"{active_30d:,}",         "Active Leakage\n(Last 30 Days)",     GEN_COLORS['success']),
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

fig.suptitle("Financial Services Leakage at a Glance",
             fontsize=28, fontweight='bold',
             color=GEN_COLORS['dark_text'], y=1.04)

plt.tight_layout()
plt.show()

if pct_leaking > 30:
    print(f"\n    INSIGHT: {pct_leaking:.0f}% of your account holders are making payments to external financial services.")
    print(f"    That is {leaking_members:,} account holders with active relationships elsewhere.")
