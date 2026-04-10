# ===========================================================================
# TXN TYPE DATA: Master Aggregation Pipeline (Conference Edition)
# ===========================================================================
# Builds: tt_agg, tt_monthly, tt_merch_pivot. Source: combined_df['transaction_type'].
# Values expected: PIN, SIG (and possibly ACH, CHK, other).

# ---------------------------------------------------------------------------
# Core transaction type aggregation
# ---------------------------------------------------------------------------
tt_agg = combined_df.groupby('transaction_type').agg(
    txn_count=('transaction_date', 'count'),
    unique_accounts=('primary_account_num', 'nunique'),
    total_spend=('amount', 'sum'),
    avg_spend=('amount', 'mean'),
    median_spend=('amount', 'median'),
).reset_index()

total_txns_tt = len(combined_df)
total_accts_tt = combined_df['primary_account_num'].nunique()

tt_agg['txn_pct'] = tt_agg['txn_count'] / total_txns_tt * 100
tt_agg['spend_pct'] = tt_agg['total_spend'] / tt_agg['total_spend'].sum() * 100
tt_agg['acct_pct'] = tt_agg['unique_accounts'] / total_accts_tt * 100
tt_agg['txn_per_account'] = tt_agg['txn_count'] / tt_agg['unique_accounts']
tt_agg = tt_agg.sort_values('txn_count', ascending=False).reset_index(drop=True)

# Convenience: PIN and SIG shares
tt_pin_pct = tt_agg.loc[tt_agg['transaction_type'] == 'PIN', 'txn_pct'].sum()
tt_sig_pct = tt_agg.loc[tt_agg['transaction_type'] == 'SIG', 'txn_pct'].sum()
tt_pin_avg = tt_agg.loc[tt_agg['transaction_type'] == 'PIN', 'avg_spend'].values
tt_sig_avg = tt_agg.loc[tt_agg['transaction_type'] == 'SIG', 'avg_spend'].values
tt_pin_avg_ticket = tt_pin_avg[0] if len(tt_pin_avg) > 0 else 0
tt_sig_avg_ticket = tt_sig_avg[0] if len(tt_sig_avg) > 0 else 0

# ---------------------------------------------------------------------------
# Monthly trend by transaction type
# ---------------------------------------------------------------------------
tt_monthly = combined_df.groupby(
    ['year_month', 'transaction_type']
).agg(
    txn_count=('transaction_date', 'count'),
    total_spend=('amount', 'sum'),
    avg_ticket=('amount', 'mean'),
    unique_accounts=('primary_account_num', 'nunique'),
).reset_index()

tt_month_totals = combined_df.groupby('year_month').agg(
    month_total=('transaction_date', 'count'),
    month_spend=('amount', 'sum'),
).reset_index()
tt_monthly = tt_monthly.merge(tt_month_totals, on='year_month')
tt_monthly['share_pct'] = tt_monthly['txn_count'] / tt_monthly['month_total'] * 100
tt_monthly['spend_share_pct'] = tt_monthly['total_spend'] / tt_monthly['month_spend'] * 100

# ---------------------------------------------------------------------------
# Merchant-level PIN vs SIG pivot (top 50 merchants)
# ---------------------------------------------------------------------------
top50_tt = combined_df[
    combined_df['merchant_consolidated'].isin(
        combined_df['merchant_consolidated'].value_counts().head(50).index
    )
]
tt_merch_pivot = pd.crosstab(
    top50_tt['merchant_consolidated'],
    top50_tt['transaction_type'],
    normalize='index'
) * 100

if 'PIN' in tt_merch_pivot.columns:
    tt_merch_pivot = tt_merch_pivot.sort_values('PIN', ascending=False)

# ---------------------------------------------------------------------------
# Conference-styled summary table
# ---------------------------------------------------------------------------
tt_display = tt_agg[['transaction_type', 'txn_count', 'txn_pct', 'unique_accounts',
                      'total_spend', 'avg_spend', 'txn_per_account']].copy()
tt_display.columns = ['Type', 'Transactions', 'Txn %', 'Accounts',
                       'Total Spend', 'Avg Ticket', 'Txns/Acct']

styled = (
    tt_display.style
    .hide(axis='index')
    .format({
        'Transactions': '{:,.0f}',
        'Txn %': '{:.1f}%',
        'Accounts': '{:,.0f}',
        'Total Spend': '${:,.0f}',
        'Avg Ticket': '${:.2f}',
        'Txns/Acct': '{:.1f}',
    })
    .set_properties(**{
        'font-size': '13px', 'font-weight': 'bold',
        'text-align': 'center', 'border': '1px solid #E9ECEF',
        'padding': '7px 10px',
    })
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', GEN_COLORS['success']),
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
    .set_caption("Transaction Type Summary")
    .bar(subset=['Transactions'], color=GEN_COLORS['success'], vmin=0)
)

display(styled)

print(f"\n    {len(tt_agg)} transaction types found")
print(f"    PIN share: {tt_pin_pct:.1f}%  |  SIG share: {tt_sig_pct:.1f}%")
print(f"    PIN avg ticket: ${tt_pin_avg_ticket:.2f}  |  SIG avg ticket: ${tt_sig_avg_ticket:.2f}")
print(f"    Merchant PIN/SIG pivot: {len(tt_merch_pivot)} merchants")
