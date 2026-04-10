# ===========================================================================
# BUSINESS GROWTH: Growers vs Decliners (Conference Edition)
# ===========================================================================
# Diverging bar: top 10 growers + top 10 decliners by last-period spend change. (14,7).

if 'business_df' not in dir() or business_df is None or len(business_df) == 0:
    print("    No business data available. Skipping growth chart.")
else:
    sorted_months_biz_g = sorted(business_df['year_month'].unique())
    if len(sorted_months_biz_g) >= 2:
        prev_m_b = sorted_months_biz_g[-2]
        curr_m_b = sorted_months_biz_g[-1]
        period_label_b = f"{prev_m_b} to {curr_m_b}"

        prev_spend_b = business_df[business_df['year_month'] == prev_m_b].groupby(
            'merchant_consolidated')['amount'].sum()
        curr_spend_b = business_df[business_df['year_month'] == curr_m_b].groupby(
            'merchant_consolidated')['amount'].sum()

        common_b = set(prev_spend_b.index) & set(curr_spend_b.index)
        growth_rows_b = []
        for m in common_b:
            p, c = prev_spend_b[m], curr_spend_b[m]
            if max(p, c) >= 1000:
                growth_rows_b.append({
                    'merchant': m, 'prev': p, 'curr': c,
                    'change': c - p,
                    'change_pct': (c - p) / p * 100 if p > 0 else 0,
                })

        biz_growth_compare = pd.DataFrame(growth_rows_b)

        if len(biz_growth_compare) > 0:
            top_growers_b = biz_growth_compare.nlargest(10, 'change').copy()
            top_decliners_b = biz_growth_compare.nsmallest(10, 'change').copy()

            combined_gd_b = pd.concat([
                top_growers_b.assign(direction='Growth'),
                top_decliners_b.assign(direction='Decline'),
            ]).copy()
            combined_gd_b['short_name'] = combined_gd_b['merchant'].str[:28]
            combined_gd_b = combined_gd_b.sort_values('change', ascending=True)

            fig, ax = plt.subplots(figsize=(14, 7))

            colors = [GEN_COLORS['accent'] if v < 0 else GEN_COLORS['success']
                      for v in combined_gd_b['change']]

            ax.barh(range(len(combined_gd_b)), combined_gd_b['change'],
                    color=colors, edgecolor='white', linewidth=0.5, height=0.65)

            ax.set_yticks(range(len(combined_gd_b)))
            ax.set_yticklabels(combined_gd_b['short_name'], fontsize=11, fontweight='bold')
            ax.set_xlabel("Spend Change ($)", fontsize=16, fontweight='bold', labelpad=10)

            for i, (_, row) in enumerate(combined_gd_b.iterrows()):
                sign = '+' if row['change'] > 0 else ''
                ha = 'left' if row['change'] >= 0 else 'right'
                offset = abs(combined_gd_b['change'].max()) * 0.02 * (1 if row['change'] >= 0 else -1)
                ax.text(row['change'] + offset, i,
                        f"{sign}${row['change']:,.0f} ({row['change_pct']:+.0f}%)",
                        va='center', ha=ha, fontsize=9, fontweight='bold',
                        color=GEN_COLORS['dark_text'])

            ax.axvline(x=0, color=GEN_COLORS['dark_text'], linewidth=1.5, zorder=3)
            gen_clean_axes(ax, keep_left=True, keep_bottom=True)
            ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
            ax.set_axisbelow(True)

            ax.set_title("Business Merchant Growth vs Decline",
                         fontsize=26, fontweight='bold',
                         color=GEN_COLORS['dark_text'], pad=35, loc='left')
            ax.text(0.0, 1.02, f"Biggest business spend swings: {period_label_b}",
                    transform=ax.transAxes, fontsize=15,
                    color=GEN_COLORS['muted'], style='italic')

            legend_items = [
                plt.Rectangle((0, 0), 1, 1, fc=GEN_COLORS['success'], label='Growth'),
                plt.Rectangle((0, 0), 1, 1, fc=GEN_COLORS['accent'], label='Decline'),
            ]
            ax.legend(handles=legend_items, loc='lower right', fontsize=13, frameon=False)

            plt.tight_layout()
            plt.show()
        else:
            print("    No business merchants with $1K+ spend in both months.")
    else:
        print("    Need at least 2 months of business data for growth analysis.")
