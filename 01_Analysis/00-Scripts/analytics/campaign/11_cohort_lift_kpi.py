# ===========================================================================
# COHORT LIFT KPI: 4-Card Dashboard (Conference Edition)
# ===========================================================================
# FancyBboxPatch cards: Total Responders, Avg DID Lift, Protected Spend,
# Activated Penetration. (18,5).

if 'cohort_summary' not in dir() or len(cohort_summary) == 0:
    print("    No cohort data available. Skipping KPI dashboard.")
else:
    # Compute KPIs
    total_unique_resp = cohort_acct[cohort_acct['status'] == 'Responder']['acct_number'].nunique()

    avg_did_lift = cohort_summary['did_spend_lift'].mean()

    # Protected spend = sum of (DID lift * responder count * post-window months) across waves
    protected_spend = 0
    for _, row in cohort_summary.iterrows():
        wc = WAVE_CONFIG.get(row['wave'], {})
        post_mo = len(wc.get('post_3mo', []))
        protected_spend += row['did_spend_lift'] * row['responded'] * max(post_mo, 1)

    total_mailed_unique = cohort_acct['acct_number'].nunique()
    penetration_pct = total_unique_resp / total_mailed_unique * 100 if total_mailed_unique > 0 else 0

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))

    kpi_data = [
        {
            'label': 'Unique Responders',
            'value': f"{total_unique_resp:,}",
            'sub': f"across {len(cohort_summary)} analyzed waves",
            'color': GEN_COLORS['success'],
        },
        {
            'label': 'Avg DID Spend Lift',
            'value': f"${avg_did_lift:,.0f}",
            'sub': "per account per month vs non-responders",
            'color': GEN_COLORS['info'],
        },
        {
            'label': 'Protected Spend',
            'value': f"${protected_spend:,.0f}",
            'sub': "incremental spend attributable to ARS",
            'color': GEN_COLORS['warning'],
        },
        {
            'label': 'Activated Penetration',
            'value': f"{penetration_pct:.1f}%",
            'sub': f"of {total_mailed_unique:,} mailed accounts responded",
            'color': GEN_COLORS['accent'],
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
                ha='center', va='center', fontsize=14,
                color='white', alpha=0.8, style='italic')

    fig.suptitle("ARS Cohort Lift Overview",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.04)
    fig.text(0.5, 0.97, f"Difference-in-Differences methodology  ({DATASET_LABEL})",
             ha='center', fontsize=14, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
