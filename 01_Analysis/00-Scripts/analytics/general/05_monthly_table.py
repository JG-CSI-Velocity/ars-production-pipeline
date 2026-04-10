# ===========================================================================
# MONTHLY TABLE: Styled Summary (Conference Edition)
# ===========================================================================
# Full monthly view with spend amounts, counts, and growth.

table_df = monthly_summary.reset_index().copy()
table_df['year_month'] = table_df['year_month'].astype(str)

# Select and rename columns for display
table_display = table_df[['year_month', 'unique_accounts', 'debit_txns',
                           'debit_spend', 'debit_avg', 'unique_merchants',
                           'txn_per_account', 'debit_spend_growth']].copy()
table_display.columns = ['Month', 'Accounts', 'Debit Txns', 'Debit Spend',
                          'Avg Debit Txn', 'Merchants', 'Txns/Account', 'MoM Growth %']

# Format numeric columns
styled = (
    table_display.style
    .hide(axis='index')
    .format({
        'Accounts': '{:,.0f}',
        'Debit Txns': '{:,.0f}',
        'Debit Spend': '${:,.0f}',
        'Avg Debit Txn': '${:,.2f}',
        'Merchants': '{:,.0f}',
        'Txns/Account': '{:.1f}',
        'MoM Growth %': lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/A",
    })
    .set_properties(**{
        'font-size': '14px',
        'font-weight': 'bold',
        'text-align': 'center',
        'border': '1px solid #E9ECEF',
        'padding': '8px 12px',
    })
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', GEN_COLORS['primary']),
            ('color', 'white'),
            ('font-size', '15px'),
            ('font-weight', 'bold'),
            ('text-align', 'center'),
            ('padding', '10px 12px'),
        ]},
        {'selector': 'caption', 'props': [
            ('font-size', '22px'),
            ('font-weight', 'bold'),
            ('color', GEN_COLORS['dark_text']),
            ('text-align', 'left'),
            ('padding-bottom', '12px'),
        ]},
    ])
    .set_caption("Monthly Portfolio Summary")
    .applymap(
        lambda x: f"color: {GEN_COLORS['success']}" if isinstance(x, (int, float)) and x > 0
        else f"color: {GEN_COLORS['accent']}" if isinstance(x, (int, float)) and x < 0
        else "",
        subset=['MoM Growth %']
    )
)

display(styled)
