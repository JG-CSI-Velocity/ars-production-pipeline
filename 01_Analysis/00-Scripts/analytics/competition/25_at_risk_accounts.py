# ===========================================================================
# AT-RISK ACCOUNTS: Competitor-Heavy Stacked Bar (Conference Edition)
# ===========================================================================
# For each top-N competitor, shows accounts where >50% of spend goes to
# the competitor. Stacked bar: CU spend + competitor spend.
# Limited to DEEP_DIVE_TOP_N competitors.

if len(competitor_spend_analysis) > 0 and len(deep_dive_competitors) > 0:
    for comp_name in deep_dive_competitors:
        df = competitor_spend_analysis[comp_name]
        at_risk = df[df['segment'] == 'Competitor-Heavy'].copy()

        if len(at_risk) == 0:
            continue

        at_risk = at_risk.sort_values('total_spend', ascending=False)
        top_n = at_risk.head(20).sort_values('total_spend')
        n = len(top_n)

        fig_h = max(5, n * 0.45 + 3)
        fig, ax = plt.subplots(figsize=(14, fig_h))

        ax.barh(range(n), top_n['your_spend'],
                color=GEN_COLORS['success'], label='Your Spend',
                edgecolor='white', linewidth=1, height=0.6, zorder=3)
        ax.barh(range(n), top_n['competitor_spend'],
                left=top_n['your_spend'],
                color=GEN_COLORS['accent'], label=f'{comp_name} Spend',
                edgecolor='white', linewidth=1, height=0.6, zorder=3)

        ax.set_yticks(range(n))
        ax.set_yticklabels([f"Account {i+1}" for i in range(n)],
                           fontsize=11, fontweight='bold')
        ax.set_xlabel('Total Spend ($)', fontsize=14, fontweight='bold', labelpad=10)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))

        gen_clean_axes(ax)
        ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
        ax.set_axisbelow(True)

        # Value labels
        for i, (_, row) in enumerate(top_n.iterrows()):
            total = row['total_spend']
            pct = row['competitor_pct']
            ax.text(total * 1.02, i,
                    f"${total:,.0f} ({pct:.0f}%)",
                    va='center', fontsize=10, fontweight='bold',
                    color=GEN_COLORS['dark_text'])

        # Summary stats box
        total_at_risk = len(at_risk)
        total_spend = at_risk['total_spend'].sum()
        total_comp_spend = at_risk['competitor_spend'].sum()
        avg_pct = at_risk['competitor_pct'].mean()

        summary = (
            f"COMPETITOR-HEAVY ACCOUNTS\n"
            f"{'_' * 30}\n"
            f"Accounts:     {total_at_risk:,}\n"
            f"Total Spend:  ${total_spend:,.0f}\n"
            f"At Competitor: ${total_comp_spend:,.0f}\n"
            f"Avg Share:    {avg_pct:.1f}%"
        )
        ax.text(0.02, 0.98, summary, transform=ax.transAxes,
                va='top', ha='left',
                bbox=dict(boxstyle='round', facecolor='#FFE5E5',
                          alpha=0.95, edgecolor=GEN_COLORS['accent'],
                          linewidth=2),
                fontsize=10, fontweight='bold', family='monospace')

        ax.set_title(f'At-Risk Accounts: {comp_name}',
                     fontsize=22, fontweight='bold',
                     color=GEN_COLORS['accent'], pad=16, loc='left')
        ax.text(0.0, 0.97,
                f"Top {n} accounts with >50% spend at competitor",
                transform=ax.transAxes, fontsize=12,
                color=GEN_COLORS['muted'], style='italic')

        ax.legend(loc='lower right', fontsize=11, frameon=True,
                  facecolor='white', edgecolor=GEN_COLORS['grid'])

        plt.tight_layout()
        plt.show()

        print(f"    {comp_name}: {total_at_risk:,} Competitor-Heavy accounts, "
              f"${total_comp_spend:,.0f} at competitor")
