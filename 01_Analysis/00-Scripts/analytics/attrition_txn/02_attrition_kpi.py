# ===========================================================================
# ATTRITION KPI DASHBOARD: Risk at a Glance (Conference Edition)
# ===========================================================================
# 4 bold cards. FancyBboxPatch styling consistent with general KPI dashboard.

# ---------------------------------------------------------------------------
# Compute KPI values
# ---------------------------------------------------------------------------
_total = len(attrition_df)
_declining = attrition_df[attrition_df['risk_tier'] == 'Declining']
_dormant = attrition_df[attrition_df['risk_tier'] == 'Dormant']
_growing = attrition_df[attrition_df['risk_tier'] == 'Growing']
_at_risk = attrition_df[attrition_df['risk_tier'].isin(['Declining', 'Dormant'])]

at_risk_count = len(_at_risk)
at_risk_pct = (at_risk_count / _total * 100) if _total > 0 else 0
growing_pct = (len(_growing) / _total * 100) if _total > 0 else 0

# Estimated annual spend at risk
_spend_col = 'last_12mo_spend' if 'last_12mo_spend' in attrition_df.columns else None
at_risk_spend = _at_risk[_spend_col].sum() if _spend_col else 0

kpis = [
    (f"{at_risk_pct:.1f}%", "At Risk\n(Declining + Dormant)",
     GEN_COLORS['accent']),
    (f"{at_risk_count:,}", "Accounts\nAt Risk",
     GEN_COLORS['warning']),
    (gen_fmt_dollar(at_risk_spend, None), "Annual Spend\nAt Risk",
     GEN_COLORS['accent'] if at_risk_spend > 0 else GEN_COLORS['muted']),
    (f"{growing_pct:.1f}%", "Growing\nAccounts",
     GEN_COLORS['success']),
]

# ---------------------------------------------------------------------------
# Render 4-card dashboard
# ---------------------------------------------------------------------------
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
            fontsize=44, fontweight='bold', color=color,
            ha='center', va='center')

    ax.text(0.5, 0.20, label, transform=ax.transAxes,
            fontsize=14, fontweight='bold', color=GEN_COLORS['dark_text'],
            ha='center', va='center', linespacing=1.4)

fig.suptitle("Attrition Risk at a Glance",
             fontsize=28, fontweight='bold',
             color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
fig.text(0.5, 0.98, f"Based on 3-month vs 12-month velocity ratios | {DATASET_LABEL}",
         fontsize=14, color=GEN_COLORS['muted'], style='italic',
         ha='center')

plt.tight_layout()
plt.show()

print(f"\n    INSIGHT: {at_risk_pct:.1f}% of the portfolio ({at_risk_count:,} accounts) "
      f"is declining or dormant")
print(f"    INSIGHT: {gen_fmt_dollar(at_risk_spend, None)} in annual spend at risk")
print(f"    INSIGHT: {growing_pct:.1f}% of accounts show positive growth momentum")
