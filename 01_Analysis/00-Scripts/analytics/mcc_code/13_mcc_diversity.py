# ===========================================================================
# MCC DIVERSITY: Account-Level Category Breadth (Conference Edition)
# ===========================================================================
# How many distinct MCCs does each account use? Distribution + engagement link.
# Dual panel: (left) histogram of MCC diversity, (right) diversity by engagement tier.
# (14,7).

if 'mcc_code' not in combined_df.columns or combined_df['mcc_code'].notna().sum() == 0:
    print("    No MCC code data available. Skipping diversity analysis.")
else:
    # Compute MCC diversity per account
    acct_diversity = combined_df.groupby('primary_account_num').agg(
        distinct_mccs=('mcc_code', 'nunique'),
        total_txns=('transaction_date', 'count'),
        total_spend=('amount', 'sum'),
    ).reset_index()

    # Summary stats
    median_mccs = acct_diversity['distinct_mccs'].median()
    mean_mccs = acct_diversity['distinct_mccs'].mean()
    max_mccs = acct_diversity['distinct_mccs'].max()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7),
                                     gridspec_kw={'width_ratios': [1.2, 1]})

    # --- LEFT: Distribution histogram ---
    bins = range(1, min(int(max_mccs) + 2, 31))
    ax1.hist(
        acct_diversity['distinct_mccs'],
        bins=bins, color=GEN_COLORS['info'], edgecolor='white', linewidth=1.5,
        alpha=0.85
    )

    # Median line
    ax1.axvline(x=median_mccs, color=GEN_COLORS['accent'], linewidth=2.5, linestyle='--')
    ax1.text(median_mccs + 0.3, ax1.get_ylim()[1] * 0.9,
             f"Median: {median_mccs:.0f} MCCs",
             fontsize=14, fontweight='bold', color=GEN_COLORS['accent'])

    ax1.set_xlabel("Distinct MCC Categories Used", fontsize=14, fontweight='bold', labelpad=8)
    ax1.set_ylabel("Number of Accounts", fontsize=14, fontweight='bold', labelpad=8)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)
    ax1.set_title("MCC Diversity Distribution", fontsize=20, fontweight='bold',
                   color=GEN_COLORS['dark_text'], pad=12)

    # --- RIGHT: Diversity by engagement tier ---
    # Merge engagement tier if available
    try:
        engage_div = acct_diversity.copy()
        engage_div.columns = ['account', 'distinct_mccs', 'total_txns', 'total_spend']
        engage_div = engage_div.merge(
            acct_txn_counts[['account', 'tier']], on='account', how='inner'
        )

        tier_diversity = engage_div.groupby('tier')['distinct_mccs'].agg(
            ['median', 'mean', 'count']
        ).reindex([t for t in ENGAGE_ORDER if t in engage_div['tier'].unique()])

        bars = ax2.barh(
            range(len(tier_diversity)), tier_diversity['median'],
            color=[ENGAGE_PALETTE.get(t, GEN_COLORS['muted']) for t in tier_diversity.index],
            edgecolor='white', linewidth=0.5, height=0.6
        )
        ax2.set_yticks(range(len(tier_diversity)))
        ax2.set_yticklabels(tier_diversity.index, fontsize=13, fontweight='bold')
        ax2.set_xlabel("Median Distinct MCCs", fontsize=14, fontweight='bold', labelpad=8)

        for j, (tier, row) in enumerate(tier_diversity.iterrows()):
            ax2.text(row['median'] + 0.2, j,
                     f"{row['median']:.0f}",
                     va='center', fontsize=13, fontweight='bold',
                     color=ENGAGE_PALETTE.get(tier, GEN_COLORS['muted']))

        gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
        ax2.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax2.set_axisbelow(True)
        ax2.set_title("Diversity by Engagement Tier", fontsize=20, fontweight='bold',
                       color=GEN_COLORS['dark_text'], pad=12)

    except NameError:
        ax2.text(0.5, 0.5, "Engagement data not available",
                 ha='center', va='center', fontsize=14, color=GEN_COLORS['muted'],
                 transform=ax2.transAxes)
        ax2.set_title("Diversity by Engagement Tier", fontsize=20, fontweight='bold',
                       color=GEN_COLORS['dark_text'], pad=12)
        gen_clean_axes(ax2, keep_left=False, keep_bottom=False)

    fig.suptitle("MCC Category Breadth per Account",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.04)
    fig.text(0.5, 0.96, "Do active accounts use more merchant categories?",
             ha='center', fontsize=15, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    plt.show()

    print(f"\n    Mean MCCs per account: {mean_mccs:.1f}")
    print(f"    Median MCCs per account: {median_mccs:.0f}")
    print(f"    Max MCCs used by one account: {max_mccs:.0f}")
