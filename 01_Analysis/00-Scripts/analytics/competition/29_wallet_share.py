# ===========================================================================
# WALLET SHARE: Top Accounts CU vs Competitor (Conference Edition)
# ===========================================================================
# For each top-N competitor, stacked bar showing CU spend + competitor spend
# for the top 20 accounts by total spend. Shows wallet share visually.

if len(competitor_spend_analysis) > 0 and len(deep_dive_competitors) > 0:
    for comp_name in deep_dive_competitors:
        df = competitor_spend_analysis[comp_name]
        top = df.sort_values('total_spend', ascending=False).head(20)
        top = top.sort_values('total_spend')
        n = len(top)

        fig_h = max(5, n * 0.45 + 3)
        fig, ax = plt.subplots(figsize=(14, fig_h))

        ax.barh(range(n), top['your_spend'],
                color=GEN_COLORS['success'], label='Your Spend',
                edgecolor='white', linewidth=1, height=0.6, zorder=3)
        ax.barh(range(n), top['competitor_spend'],
                left=top['your_spend'],
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
        for i, (_, row) in enumerate(top.iterrows()):
            total = row['total_spend']
            pct = row['competitor_pct']
            ax.text(total * 1.02, i,
                    f"${total:,.0f} ({pct:.0f}% at comp)",
                    va='center', fontsize=10, fontweight='bold',
                    color=GEN_COLORS['dark_text'])

        ax.set_title(f'Wallet Share: {comp_name}',
                     fontsize=22, fontweight='bold',
                     color=GEN_COLORS['dark_text'], pad=16, loc='left')
        ax.text(0.0, 0.97,
                f"Top {n} accounts by total spend  |  How much goes to competitor?",
                transform=ax.transAxes, fontsize=12,
                color=GEN_COLORS['muted'], style='italic')

        ax.legend(loc='lower right', fontsize=11, frameon=True,
                  facecolor='white', edgecolor=GEN_COLORS['grid'])

        plt.tight_layout()
        plt.show()

        # Summary
        avg_pct = top['competitor_pct'].mean()
        total_at_comp = top['competitor_spend'].sum()
        print(f"    {comp_name} top {n}: avg wallet share {avg_pct:.1f}%, "
              f"${total_at_comp:,.0f} at competitor")
