# ===========================================================================
# SPEND vs FREQUENCY: Engagement Scatter (Conference Edition)
# ===========================================================================
# For each top-N competitor, scatter of transaction count (x) vs total
# competitor spend (y), colored by recency. Identifies high-engagement
# accounts at each competitor.

if len(all_account_summaries) > 0 and len(deep_dive_competitors) > 0:
    for comp_name in deep_dive_competitors:
        if comp_name not in all_account_summaries:
            continue
        acct = all_account_summaries[comp_name]
        if len(acct) < 5:
            continue

        fig, ax = plt.subplots(figsize=(14, 8))

        scatter = ax.scatter(
            acct['txn_count'], acct['total_amount'],
            s=90, alpha=0.6,
            c=acct['recency_days'], cmap='RdYlGn_r',
            edgecolors='white', linewidth=0.6,
            zorder=3,
        )

        ax.set_xlabel('Transaction Count', fontsize=16, fontweight='bold', labelpad=10)
        ax.set_ylabel('Total Competitor Spend ($)', fontsize=16,
                      fontweight='bold', labelpad=10)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))

        gen_clean_axes(ax)
        ax.grid(alpha=0.3, color=GEN_COLORS['grid'], linewidth=0.5)
        ax.set_axisbelow(True)

        # Colorbar
        cbar = plt.colorbar(scatter, ax=ax, shrink=0.8)
        cbar.set_label('Days Since Last Transaction', rotation=270,
                       labelpad=20, fontsize=12, fontweight='bold')

        # Median crosshairs for quadrant reference
        med_txn = acct['txn_count'].median()
        med_spend = acct['total_amount'].median()
        ax.axvline(med_txn, color=GEN_COLORS['muted'], linestyle='--',
                   alpha=0.4, linewidth=2)
        ax.axhline(med_spend, color=GEN_COLORS['muted'], linestyle='--',
                   alpha=0.4, linewidth=2)

        # Quadrant labels
        ax.text(0.97, 0.97, 'High Value + Frequent',
                transform=ax.transAxes, ha='right', va='top',
                bbox=dict(boxstyle='round', facecolor=GEN_COLORS['accent'],
                          alpha=0.7, edgecolor='white'),
                fontsize=10, fontweight='bold', color='white')
        ax.text(0.03, 0.97, 'High Value + Infrequent',
                transform=ax.transAxes, ha='left', va='top',
                bbox=dict(boxstyle='round', facecolor=GEN_COLORS['warning'],
                          alpha=0.7, edgecolor='white'),
                fontsize=10, fontweight='bold', color='white')

        ax.set_title(f'Engagement Profile: {comp_name}',
                     fontsize=22, fontweight='bold',
                     color=GEN_COLORS['dark_text'], pad=20, loc='left')
        ax.text(0.0, 0.97,
                f"{len(acct):,} accounts  |  Green = recent  |  Red = dormant",
                transform=ax.transAxes, fontsize=12,
                color=GEN_COLORS['muted'], style='italic')

        plt.tight_layout()
        plt.show()

        # Stats
        high_engage = len(acct[(acct['txn_count'] > med_txn) &
                               (acct['total_amount'] > med_spend)])
        print(f"    {comp_name}: {high_engage:,} high-value frequent accounts "
              f"({high_engage/len(acct)*100:.1f}% of total)")
