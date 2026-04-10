# ===========================================================================
# MERCHANT NEW ENTRANTS: Recent Additions (Conference Edition)
# ===========================================================================
# Conference-styled table: newest merchants from last 3 months.

sorted_months_ne = sorted(combined_df['year_month'].unique())
recent_3 = sorted_months_ne[-3:] if len(sorted_months_ne) >= 3 else sorted_months_ne

# New merchants = first appearance in these months
first_appearance = combined_df.groupby('merchant_consolidated')['year_month'].min().reset_index()
first_appearance.columns = ['merchant_consolidated', 'first_month']

new_merchants = first_appearance[first_appearance['first_month'].isin(recent_3)]

if len(new_merchants) > 0:
    # Get stats for new merchants
    new_stats = combined_df[
        combined_df['merchant_consolidated'].isin(new_merchants['merchant_consolidated'])
    ].groupby('merchant_consolidated').agg(
        txn_count=('transaction_date', 'count'),
        unique_accounts=('primary_account_num', 'nunique'),
        total_spend=('amount', 'sum'),
        avg_spend=('amount', 'mean'),
    ).reset_index()

    new_stats = new_stats.merge(new_merchants, on='merchant_consolidated')
    new_stats = new_stats.sort_values('txn_count', ascending=False).head(20)
    new_stats['first_month_str'] = new_stats['first_month'].astype(str)

    ne_display = new_stats[['merchant_consolidated', 'first_month_str', 'txn_count',
                             'unique_accounts', 'total_spend', 'avg_spend']].copy()
    ne_display.columns = ['Merchant', 'First Month', 'Transactions', 'Accounts',
                           'Total Spend', 'Avg Txn']
    ne_display['Merchant'] = ne_display['Merchant'].str[:35]

    styled = (
        ne_display.style
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
        .set_caption("Top 20 New Merchant Entrants (Last 3 Months)")
        .bar(subset=['Transactions'], color=GEN_COLORS['warning'], vmin=0)
    )

    display(styled)

    total_new = len(first_appearance[first_appearance['first_month'].isin(recent_3)])
    print(f"\n    Total new merchants (last 3 months): {total_new}")
    print(f"    Avg transactions per new merchant: {new_stats['txn_count'].mean():.0f}")
    print(f"    Avg accounts per new merchant: {new_stats['unique_accounts'].mean():.0f}")
else:
    print("No new merchants in the last 3 months.")
