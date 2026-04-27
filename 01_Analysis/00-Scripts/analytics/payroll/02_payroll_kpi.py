# ===========================================================================
# PAYROLL KPI DASHBOARD: Key Metrics at a Glance
# ===========================================================================
# 4 FancyBboxPatch cards showing payroll detection headline numbers.

fig, axes = plt.subplots(1, 4, figsize=(18, 5))

# ---------------------------------------------------------------------------
# Compute KPI values
# ---------------------------------------------------------------------------
n_total = len(payroll_df)
n_payroll = int(payroll_df['has_payroll'].sum())
pct_payroll = n_payroll / n_total * 100 if n_total > 0 else 0

total_payroll_deposits = payroll_df.loc[payroll_df['has_payroll'], 'payroll_count'].sum()

avg_payroll_amt = payroll_df.loc[payroll_df['has_payroll'], 'avg_payroll_amount'].mean()

# Balance comparison: payroll vs non-payroll
bal_col = None
for col_name in ['avg_balance', 'curr_balance']:
    if col_name in payroll_df.columns:
        bal_col = col_name
        break

if bal_col:
    payroll_bal = payroll_df.loc[payroll_df['has_payroll'], bal_col].mean()
    non_payroll_bal = payroll_df.loc[~payroll_df['has_payroll'], bal_col].mean()
    bal_multiplier = payroll_bal / non_payroll_bal if non_payroll_bal > 0 else 0
    bal_display = f"{bal_multiplier:.1f}x"
    bal_sub = f"${payroll_bal:,.0f} vs ${non_payroll_bal:,.0f}"
else:
    bal_display = "N/A"
    bal_sub = "balance data unavailable"

kpi_data = [
    {
        'label': 'Payroll Accounts',
        'value': f"{pct_payroll:.1f}%",
        'sub': f"{n_payroll:,} of {n_total:,} accounts",
        'color': GEN_COLORS['primary'],
    },
    {
        'label': 'Payroll Deposits',
        'value': gen_fmt_count(total_payroll_deposits, None),
        'sub': 'total deposits detected',
        'color': GEN_COLORS['info'],
    },
    {
        'label': 'Avg Payroll Amount',
        'value': f"${avg_payroll_amt:,.0f}" if avg_payroll_amt > 0 else "N/A",
        'sub': 'per deposit',
        'color': GEN_COLORS['success'],
    },
    {
        'label': 'Balance Multiplier',
        'value': bal_display,
        'sub': bal_sub,
        'color': GEN_COLORS['accent'],
    },
]

# ---------------------------------------------------------------------------
# Render cards
# ---------------------------------------------------------------------------
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

fig.suptitle("Payroll & Direct Deposit Detection",
             fontsize=28, fontweight='bold',
             color=GEN_COLORS['dark_text'], x=0.01, ha='left', y=GEN_TITLE_Y)
fig.text(0.01, 1.00,
         f"Primary Financial Institution signal  --  {DATASET_LABEL}",
         fontsize=14, style='italic', color=GEN_COLORS['muted'],
         ha='left', transform=fig.transFigure)

plt.tight_layout()
plt.show()
