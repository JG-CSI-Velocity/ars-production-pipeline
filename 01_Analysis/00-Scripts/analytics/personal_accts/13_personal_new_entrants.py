# ===========================================================================
# PERSONAL NEW ENTRANTS: Recent Additions (Conference Edition)
# ===========================================================================
# Conference-styled table: newest personal merchants from last 3 months.

sorted_months_ne_pers = sorted(personal_df['year_month'].unique())
recent_3_p = sorted_months_ne_pers[-3:] if len(sorted_months_ne_pers) >= 3 else sorted_months_ne_pers

# New merchants = first appearance in these months (personal txns only)
first_appear_p = personal_df.groupby('merchant_consolidated')['year_month'].min().reset_index()
first_appear_p.columns = ['merchant_consolidated', 'first_month']

new_merchants_p = first_appear_p[first_appear_p['first_month'].isin(recent_3_p)]

if len(new_merchants_p) > 0:
    # Get stats for new merchants
    new_stats_p = personal_df[
        personal_df['merchant_consolidated'].isin(new_merchants_p['merchant_consolidated'])
    ].groupby('merchant_consolidated').agg(
        txn_count=('transaction_date', 'count'),
        unique_accounts=('primary_account_num', 'nunique'),
        total_spend=('amount', 'sum'),
        avg_spend=('amount', 'mean'),
    ).reset_index()

    new_stats_p = new_stats_p.merge(new_merchants_p, on='merchant_consolidated')
    new_stats_p = new_stats_p.sort_values('txn_count', ascending=False).head(20)
    new_stats_p['first_month_str'] = new_stats_p['first_month'].astype(str)

    ne_display_p = new_stats_p[['merchant_consolidated', 'first_month_str', 'txn_count',
                                 'unique_accounts', 'total_spend', 'avg_spend']].copy()
    ne_display_p.columns = ['Merchant', 'First Month', 'Transactions', 'Accounts',
                             'Total Spend', 'Avg Txn']
    ne_display_p['Merchant'] = ne_display_p['Merchant'].str[:35]

    styled = (
        ne_display_p.style
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
        .set_caption("Top 20 New Personal Merchant Entrants (Last 3 Months)")
        .bar(subset=['Transactions'], color=GEN_COLORS['warning'], vmin=0)
    )

    display(styled)

    total_new_p = len(first_appear_p[first_appear_p['first_month'].isin(recent_3_p)])
    print(f"\n    Total new personal merchants (last 3 months): {total_new_p}")
    print(f"    Avg transactions per new merchant: {new_stats_p['txn_count'].mean():.0f}")
    print(f"    Avg accounts per new merchant: {new_stats_p['unique_accounts'].mean():.0f}")
else:
    print("    No new personal merchants in the last 3 months.")
