# ===========================================================================
# REG E KPI DASHBOARD: Opt-In Health at a Glance
# ===========================================================================
# 4 bold cards. FancyBboxPatch styling consistent with general theme.

# ---------------------------------------------------------------------------
# Compute KPI values
# ---------------------------------------------------------------------------
_total = len(rege_df)
_opted_in = len(rege_df[rege_df['current_status'] == 'Opted-In'])
_optin_rate = (_opted_in / _total * 100) if _total > 0 else 0

_avg_od_limit = rege_df.loc[
    rege_df['current_status'] == 'Opted-In', 'current_od_limit'
].mean()
_avg_od_limit = _avg_od_limit if not pd.isna(_avg_od_limit) else 0

_changed_count = int(rege_df['status_changed'].sum())

kpis = [
    (f"{_optin_rate:.1f}%", "Current\nOpt-In Rate",
     GEN_COLORS['success'] if _optin_rate >= 50 else GEN_COLORS['accent']),
    (f"{_opted_in:,}", "Accounts\nOpted In",
     GEN_COLORS['info']),
    (gen_fmt_dollar(_avg_od_limit, None), "Avg OD Limit\n(Opted-In Accounts)",
     GEN_COLORS['warning']),
    (f"{_changed_count:,}", "Accounts That\nChanged Status",
     GEN_COLORS['accent'] if _changed_count > 0 else GEN_COLORS['muted']),
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

fig.suptitle("Reg E Opt-In Health at a Glance",
             fontsize=28, fontweight='bold',
             color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
fig.text(0.5, 0.98,
         f"Overdraft coverage enrollment across all accounts | {DATASET_LABEL}",
         fontsize=14, color=GEN_COLORS['muted'], style='italic',
         ha='center')

plt.tight_layout()
plt.show()

print(f"\n    INSIGHT: {_optin_rate:.1f}% of accounts ({_opted_in:,}) are currently opted in")
print(f"    INSIGHT: Average OD limit for opted-in accounts: "
      f"{gen_fmt_dollar(_avg_od_limit, None)}")
print(f"    INSIGHT: {_changed_count:,} accounts changed Reg E status during the period")
