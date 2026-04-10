# ===========================================================================
# BUSINESS NEW ENTRANTS: Recent Additions (Conference Edition)
# ===========================================================================
# Conference-styled table: newest business merchants from last 3 months.

if 'business_df' not in dir() or business_df is None or len(business_df) == 0:
    print("    No business data available. Skipping new entrants.")
else:
    sorted_months_ne_biz = sorted(business_df['year_month'].unique())
    recent_3_b = sorted_months_ne_biz[-3:] if len(sorted_months_ne_biz) >= 3 else sorted_months_ne_biz

    first_appear_b = business_df.groupby('merchant_consolidated')['year_month'].min().reset_index()
    first_appear_b.columns = ['merchant_consolidated', 'first_month']

    new_merchants_b = first_appear_b[first_appear_b['first_month'].isin(recent_3_b)]

    if len(new_merchants_b) > 0:
        new_stats_b = business_df[
            business_df['merchant_consolidated'].isin(new_merchants_b['merchant_consolidated'])
        ].groupby('merchant_consolidated').agg(
            txn_count=('transaction_date', 'count'),
            unique_accounts=('primary_account_num', 'nunique'),
            total_spend=('amount', 'sum'),
            avg_spend=('amount', 'mean'),
        ).reset_index()

        new_stats_b = new_stats_b.merge(new_merchants_b, on='merchant_consolidated')
        new_stats_b = new_stats_b.sort_values('txn_count', ascending=False).head(20)
        new_stats_b['first_month_str'] = new_stats_b['first_month'].astype(str)

        ne_display_b = new_stats_b[['merchant_consolidated', 'first_month_str', 'txn_count',
                                     'unique_accounts', 'total_spend', 'avg_spend']].copy()
        ne_display_b.columns = ['Merchant', 'First Month', 'Transactions', 'Accounts',
                                 'Total Spend', 'Avg Txn']
        ne_display_b['Merchant'] = ne_display_b['Merchant'].str[:35]

        styled = (
            ne_display_b.style
            .hide(axis='index')
            .format({
                'Transactions': '{:,.0f}',
                'Accounts': '{:,.0f}',
                'Total Spend': '${:,.0f}',
                'Avg Txn': '${:,.0f}',
            })
            .set_properties(**{
                'font-size': '13px', 'font-weight': 'bold',
                'text-align': 'center', 'border': '1px solid #E9ECEF',
                'padding': '7px 10px',
            })
            .set_table_styles([
                {'selector': 'th', 'props': [
                    ('background-color', GEN_COLORS['warning']),
                    ('color', 'white'), ('font-size', '14px'),
                    ('font-weight', 'bold'), ('text-align', 'center'),
                    ('padding', '8px 10px'),
                ]},
                {'selector': 'caption', 'props': [
                    ('font-size', '22px'), ('font-weight', 'bold'),
                    ('color', GEN_COLORS['dark_text']), ('text-align', 'left'),
                    ('padding-bottom', '12px'),
                ]},
            ])
            .set_caption("Top 20 New Business Merchant Entrants (Last 3 Months)")
            .bar(subset=['Transactions'], color=GEN_COLORS['warning'], vmin=0)
        )

        display(styled)

        total_new_b = len(first_appear_b[first_appear_b['first_month'].isin(recent_3_b)])
        print(f"\n    Total new business merchants (last 3 months): {total_new_b}")
        print(f"    Avg transactions per new merchant: {new_stats_b['txn_count'].mean():.0f}")
        print(f"    Avg accounts per new merchant: {new_stats_b['unique_accounts'].mean():.0f}")
    else:
        print("    No new business merchants in the last 3 months.")
