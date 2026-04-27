# ===========================================================================
# ICS KPI DASHBOARD: Key Metrics at a Glance (Conference Edition)
# ===========================================================================
# 4 FancyBboxPatch cards. (18,5). Uses DATASET_LABEL for period context.

if 'ics_agg' not in dir() or len(ics_agg) == 0:
    print("    No ICS data available. Skipping KPI dashboard.")
else:
    ics_only = ics_agg[ics_agg['ics_account'] != 'Non-ICS']
    ics_acct_total = ics_only['unique_accounts'].sum()
    ics_acct_pct = ics_only['acct_pct'].sum()

    ref_row = ics_agg[ics_agg['ics_account'] == 'REF']
    dm_row = ics_agg[ics_agg['ics_account'] == 'DM']
    ref_tpm = ref_row['txns_per_acct_mo'].values[0] if len(ref_row) > 0 else 0
    dm_tpm = dm_row['txns_per_acct_mo'].values[0] if len(dm_row) > 0 else 0

    ics_avg = ics_df['amount'].mean() if len(ics_df) > 0 else 0
    non_ics_avg = non_ics_df['amount'].mean() if len(non_ics_df) > 0 else 0

    ics_spend_mo = ics_only['spend_per_acct_mo'].mean() if len(ics_only) > 0 else 0

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))

    kpi_data = [
        {
            'label': 'ICS Accounts',
            'value': f"{ics_acct_total:,}",
            'sub': f"{ics_acct_pct:.1f}% of all accounts",
            'color': GEN_COLORS['info'],
        },
        {
            'label': 'REF vs DM Activity',
            'value': f"{ref_tpm:.1f} / {dm_tpm:.1f}",
            'sub': 'txns per account per month',
            'color': GEN_COLORS['primary'],
        },
        {
            'label': 'ICS Avg Ticket',
            'value': f"${ics_avg:.2f}",
            'sub': f"vs Non-ICS ${non_ics_avg:.2f}",
            'color': GEN_COLORS['success'],
        },
        {
            'label': 'ICS Spend/Acct/Mo',
            'value': f"${ics_spend_mo:,.0f}",
            'sub': 'monthly card spend per ICS account',
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
                ha='center', va='center', fontsize=36, fontweight='bold',
                color='white',
                path_effects=[pe.withStroke(linewidth=2, foreground=kpi['color'])])
        ax.text(5, 2.3, kpi['sub'],
                ha='center', va='center', fontsize=11,
                color='white', alpha=0.8, style='italic')

    fig.suptitle("ICS Account Acquisition Overview",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
    fig.text(0.5, GEN_SUBTITLE_Y, f"{DATASET_LABEL}  ({DATASET_MONTHS} months)",
             ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
