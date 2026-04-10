# ===========================================================================
# PORTFOLIO DATA: Build monthly_summary and portfolio_kpis
# ===========================================================================
# All downstream cells depend on this. Conference-styled summary output.

# Ensure year_month exists
if 'year_month' not in combined_df.columns:
    combined_df['year_month'] = combined_df['transaction_date'].dt.to_period('M')

# ---------------------------------------------------------------------------
# Debit-only slice (SIG + PIN = actual card swipes)
# ---------------------------------------------------------------------------
DEBIT_TYPES = ['SIG', 'PIN']
debit_df = combined_df[combined_df['transaction_type'].isin(DEBIT_TYPES)]

# ---------------------------------------------------------------------------
# Monthly summary (all types for context, debit-only for reporting)
# ---------------------------------------------------------------------------
monthly_summary = combined_df.groupby('year_month').agg(
    txn_count=('transaction_date', 'count'),
    unique_accounts=('primary_account_num', 'nunique'),
    unique_merchants=('merchant_consolidated', 'nunique'),
    unique_mcc=('mcc_code', 'nunique'),
    total_spend=('amount', 'sum'),
    avg_spend=('amount', 'mean'),
    median_spend=('amount', 'median'),
).sort_index()

# Debit-only spend per month
_debit_monthly = debit_df.groupby('year_month').agg(
    debit_spend=('amount', 'sum'),
    debit_txns=('transaction_date', 'count'),
    debit_avg=('amount', 'mean'),
).sort_index()
monthly_summary = monthly_summary.join(_debit_monthly, how='left').fillna(0)

# Month-over-month growth (percentages)
monthly_summary['txn_growth'] = monthly_summary['txn_count'].pct_change() * 100
monthly_summary['acct_growth'] = monthly_summary['unique_accounts'].pct_change() * 100
monthly_summary['merchant_growth'] = monthly_summary['unique_merchants'].pct_change() * 100
monthly_summary['spend_growth'] = monthly_summary['total_spend'].pct_change() * 100
monthly_summary['debit_spend_growth'] = monthly_summary['debit_spend'].pct_change() * 100

# Rolling averages (3-month window)
monthly_summary['txn_rolling'] = monthly_summary['txn_count'].rolling(3, min_periods=1).mean()
monthly_summary['acct_rolling'] = monthly_summary['unique_accounts'].rolling(3, min_periods=1).mean()
monthly_summary['debit_spend_rolling'] = monthly_summary['debit_spend'].rolling(3, min_periods=1).mean()

# Transactions per account
monthly_summary['txn_per_account'] = monthly_summary['txn_count'] / monthly_summary['unique_accounts']

# ---------------------------------------------------------------------------
# Portfolio KPIs: single-number metrics for dashboards
# ---------------------------------------------------------------------------
total_months = len(monthly_summary)
total_txns = monthly_summary['txn_count'].sum()
total_accounts = combined_df['primary_account_num'].nunique()
total_merchants = combined_df['merchant_consolidated'].nunique()
avg_monthly_txns = monthly_summary['txn_count'].mean()
avg_txn_per_account = total_txns / total_accounts if total_accounts > 0 else 0

# Debit-only KPIs
total_debit_spend = monthly_summary['debit_spend'].sum()
total_debit_txns = int(monthly_summary['debit_txns'].sum())
avg_monthly_debit_spend = monthly_summary['debit_spend'].mean()
avg_debit_txn = total_debit_spend / total_debit_txns if total_debit_txns > 0 else 0

# Latest month growth
latest_txn_growth = monthly_summary['txn_growth'].iloc[-1] if total_months > 1 else 0
latest_acct_growth = monthly_summary['acct_growth'].iloc[-1] if total_months > 1 else 0
latest_debit_spend_growth = monthly_summary['debit_spend_growth'].iloc[-1] if total_months > 1 else 0

portfolio_kpis = {
    'total_months': total_months,
    'total_txns': total_txns,
    'total_accounts': total_accounts,
    'total_merchants': total_merchants,
    'avg_monthly_txns': avg_monthly_txns,
    'avg_txn_per_account': avg_txn_per_account,
    'latest_txn_growth': latest_txn_growth,
    'latest_acct_growth': latest_acct_growth,
    'total_debit_spend': total_debit_spend,
    'total_debit_txns': total_debit_txns,
    'avg_monthly_debit_spend': avg_monthly_debit_spend,
    'avg_debit_txn': avg_debit_txn,
    'latest_debit_spend_growth': latest_debit_spend_growth,
}

# ---------------------------------------------------------------------------
# Conference-styled summary
# ---------------------------------------------------------------------------
kpi_display = pd.DataFrame([
    {'Metric': 'Total Months', 'Value': f"{total_months}"},
    {'Metric': 'Total Transactions (All Types)', 'Value': f"{total_txns:,}"},
    {'Metric': 'Debit Card Transactions (SIG+PIN)', 'Value': f"{total_debit_txns:,}"},
    {'Metric': 'Debit Card Spend', 'Value': f"${total_debit_spend:,.0f}"},
    {'Metric': 'Avg Monthly Debit Spend', 'Value': f"${avg_monthly_debit_spend:,.0f}"},
    {'Metric': 'Avg Debit Transaction', 'Value': f"${avg_debit_txn:,.2f}"},
    {'Metric': 'Unique Accounts', 'Value': f"{total_accounts:,}"},
    {'Metric': 'Unique Merchants', 'Value': f"{total_merchants:,}"},
    {'Metric': 'Latest MoM Txn Growth', 'Value': f"{latest_txn_growth:+.1f}%"},
    {'Metric': 'Latest MoM Debit Spend Growth', 'Value': f"{latest_debit_spend_growth:+.1f}%"},
])

styled = (
    kpi_display.style
    .hide(axis='index')
    .set_properties(**{
        'font-size': '15px',
        'font-weight': 'bold',
        'text-align': 'left',
        'border': '1px solid #E9ECEF',
        'padding': '10px 16px',
    })
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', GEN_COLORS['primary']),
            ('color', 'white'),
            ('font-size', '16px'),
            ('font-weight', 'bold'),
            ('text-align', 'left'),
            ('padding', '10px 16px'),
        ]},
        {'selector': 'caption', 'props': [
            ('font-size', '22px'),
            ('font-weight', 'bold'),
            ('color', GEN_COLORS['dark_text']),
            ('text-align', 'left'),
            ('padding-bottom', '12px'),
        ]},
    ])
    .set_caption("Portfolio Data Pipeline")
)

display(styled)
