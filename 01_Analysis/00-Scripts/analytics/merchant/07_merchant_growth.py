# ===========================================================================
# MERCHANT GROWTH: Growers vs Decliners (Conference Edition)
# ===========================================================================
# Diverging bar: top 10 growers + top 10 decliners by last-period spend change. (14,7).

# Compute last month-pair growth for each merchant
sorted_months_g = sorted(combined_df['year_month'].unique())
if len(sorted_months_g) >= 2:
    prev_m = sorted_months_g[-2]
    curr_m = sorted_months_g[-1]
    period_label = f"{prev_m} to {curr_m}"

    prev_spend = combined_df[combined_df['year_month'] == prev_m].groupby(
        'merchant_consolidated')['amount'].sum()
    curr_spend = combined_df[combined_df['year_month'] == curr_m].groupby(
        'merchant_consolidated')['amount'].sum()

    # Merchants present in both months with $1K+ in either
    common = set(prev_spend.index) & set(curr_spend.index)
    growth_rows = []
    for m in common:
        p, c = prev_spend[m], curr_spend[m]
        if max(p, c) >= 1000:
            growth_rows.append({
                'merchant': m, 'prev': p, 'curr': c,
                'change': c - p,
                'change_pct': (c - p) / p * 100 if p > 0 else 0,
            })

    growth_compare = pd.DataFrame(growth_rows)

    top_growers = growth_compare.nlargest(10, 'change').copy()
    top_decliners = growth_compare.nsmallest(10, 'change').copy()

    combined_gd = pd.concat([
        top_growers.assign(direction='Growth'),
        top_decliners.assign(direction='Decline'),
    ]).copy()
    combined_gd['short_name'] = combined_gd['merchant'].str[:28]

    # Sort: decliners at top (negative), growers at bottom (positive)
    combined_gd = combined_gd.sort_values('change', ascending=True)

    fig, ax = plt.subplots(figsize=(14, 7))

    colors = [GEN_COLORS['accent'] if v < 0 else GEN_COLORS['success']
              for v in combined_gd['change']]

    ax.barh(range(len(combined_gd)), combined_gd['change'],
            color=colors, edgecolor='white', linewidth=0.5, height=0.65)

    ax.set_yticks(range(len(combined_gd)))
    ax.set_yticklabels(combined_gd['short_name'], fontsize=11, fontweight='bold')
    ax.set_xlabel("Spend Change ($)", fontsize=16, fontweight='bold', labelpad=10)

    # Value labels
    for i, (_, row) in enumerate(combined_gd.iterrows()):
        sign = '+' if row['change'] > 0 else ''
        ha = 'left' if row['change'] >= 0 else 'right'
        offset = abs(combined_gd['change'].max()) * 0.02 * (1 if row['change'] >= 0 else -1)
        ax.text(row['change'] + offset, i,
                f"{sign}${row['change']:,.0f} ({row['change_pct']:+.0f}%)",
                va='center', ha=ha, fontsize=9, fontweight='bold',
                color=GEN_COLORS['dark_text'])

    ax.axvline(x=0, color=GEN_COLORS['dark_text'], linewidth=1.5, zorder=3)
    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    ax.set_title("Merchant Growth vs Decline",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, f"Biggest spend swings: {period_label}",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    # Legend
    from matplotlib.lines import Line2D
    legend_items = [
        plt.Rectangle((0, 0), 1, 1, fc=GEN_COLORS['success'], label='Growth'),
        plt.Rectangle((0, 0), 1, 1, fc=GEN_COLORS['accent'], label='Decline'),
    ]
    ax.legend(handles=legend_items, loc='lower right', fontsize=13, frameon=False)

    plt.tight_layout()
    plt.show()
else:
    print("Need at least 2 months of data for growth analysis.")
