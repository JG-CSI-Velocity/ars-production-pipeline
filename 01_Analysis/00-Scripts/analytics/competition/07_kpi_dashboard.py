# ===========================================================================
# KPI DASHBOARD: High-Level Competitor Metrics (Conference Edition)
# ===========================================================================
# Big bold numbers for a stage screen. No tables, no dollars.
# Shows: % of accounts using competitors, % of transactions, competitor count

if len(all_competitor_data) > 0:
    summary_df = pd.DataFrame(summary_data).sort_values('total_amount', ascending=False)

    total_competitor_trans = summary_df['total_transactions'].sum()
    total_competitor_accounts = summary_df['unique_accounts'].sum()
    total_competitors_found = len(all_competitor_data)

    total_all_trans = len(combined_df)
    total_all_accounts = combined_df['primary_account_num'].nunique()

    pct_trans = (total_competitor_trans / total_all_trans * 100) if total_all_trans > 0 else 0
    pct_accounts = (total_competitor_accounts / total_all_accounts * 100) if total_all_accounts > 0 else 0
    avg_txn_per_account = (total_competitor_trans / total_competitor_accounts) if total_competitor_accounts > 0 else 0

    # ----- KPI card layout -----
    kpis = [
        (f"{pct_accounts:.1f}%",   "of Accounts\nUsing Competitors",  GEN_COLORS['accent']),
        (f"{pct_trans:.1f}%",      "of Transactions\nGo to Competitors", GEN_COLORS['info']),
        (f"{total_competitors_found}", "Competitors\nDetected",        GEN_COLORS['warning']),
        (f"{avg_txn_per_account:.1f}", "Avg Transactions\nper Account", GEN_COLORS['success']),
    ]

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))
    fig.patch.set_facecolor('#FFFFFF')

    for ax, (value, label, color) in zip(axes, kpis):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # Card background
        card = FancyBboxPatch(
            (0.03, 0.05), 0.94, 0.90,
            boxstyle="round,pad=0.05",
            facecolor=color,
            alpha=0.08,
            edgecolor=color,
            linewidth=2.5
        )
        ax.add_patch(card)

        # Big number
        ax.text(0.5, 0.62, value, transform=ax.transAxes,
                fontsize=48, fontweight='bold', color=color,
                ha='center', va='center')

        # Label
        ax.text(0.5, 0.20, label, transform=ax.transAxes,
                fontsize=15, fontweight='bold', color=GEN_COLORS['dark_text'],
                ha='center', va='center', linespacing=1.4)

    # Supertitle
    fig.suptitle("Competitive Exposure at a Glance",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'],
                 y=1.04)

    plt.tight_layout()
    plt.show()

    # Opportunity callout
    if pct_accounts < 20:
        print(f"\n    OPPORTUNITY: Only {pct_accounts:.1f}% of accounts show competitor activity.")
        print("    Competitor footprint is limited -- defend these relationships now before it grows.")
    elif pct_accounts > 40:
        print(f"\n    WARNING: {pct_accounts:.1f}% of accounts show competitor activity.")
        print("    Significant competitive overlap -- targeted retention strategy needed.")
