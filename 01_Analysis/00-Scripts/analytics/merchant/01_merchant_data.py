# ===========================================================================
# MERCHANT DATA: Master Aggregation Pipeline (Conference Edition)
# ===========================================================================
# Single aggregation replacing 3 duplicated top-50 cells.
# Builds: merch_agg, merch_top20, merch_monthly, consistency_df, cohort_df.

# ---------------------------------------------------------------------------
# Core merchant aggregation
# ---------------------------------------------------------------------------
merch_agg = combined_df.groupby('merchant_consolidated').agg(
    txn_count=('transaction_date', 'count'),
    unique_accounts=('primary_account_num', 'nunique'),
    total_spend=('amount', 'sum'),
    avg_spend=('amount', 'mean'),
    median_spend=('amount', 'median'),
).reset_index()

total_txns_merch = len(combined_df)
total_accts_merch = combined_df['primary_account_num'].nunique()

merch_agg['txn_pct'] = merch_agg['txn_count'] / total_txns_merch * 100
merch_agg['acct_pct'] = merch_agg['unique_accounts'] / total_accts_merch * 100
merch_agg['txn_per_account'] = merch_agg['txn_count'] / merch_agg['unique_accounts']
merch_agg = merch_agg.sort_values('txn_count', ascending=False).reset_index(drop=True)
merch_agg['cumulative_txn_pct'] = merch_agg['txn_pct'].cumsum()
merch_agg['rank'] = range(1, len(merch_agg) + 1)

# Top slices
merch_top20 = merch_agg.head(20).copy()
merch_top50 = merch_agg.head(50).copy()

# ---------------------------------------------------------------------------
# Monthly merchant trend (top 10)
# ---------------------------------------------------------------------------
top10_merchants = merch_agg.head(10)['merchant_consolidated'].tolist()
merch_monthly = combined_df[combined_df['merchant_consolidated'].isin(top10_merchants)].groupby(
    ['year_month', 'merchant_consolidated']
).agg(txn_count=('transaction_date', 'count')).reset_index()

monthly_totals_m = combined_df.groupby('year_month').size().reset_index(name='month_total')
merch_monthly = merch_monthly.merge(monthly_totals_m, on='year_month')
merch_monthly['share_pct'] = merch_monthly['txn_count'] / merch_monthly['month_total'] * 100

# ---------------------------------------------------------------------------
# Spend consistency (coefficient of variation per merchant)
# ---------------------------------------------------------------------------
m_monthly_spend = combined_df.groupby(
    ['merchant_consolidated', 'year_month']
)['amount'].sum().reset_index()

m_pivot = m_monthly_spend.pivot(
    index='merchant_consolidated', columns='year_month', values='amount'
).fillna(0)

consist_rows = []
for merchant in m_pivot.index:
    vals = m_pivot.loc[merchant].values
    nonzero = vals[vals > 0]
    if len(nonzero) >= 3 and nonzero.mean() > 0:
        cv = nonzero.std() / nonzero.mean() * 100
        consist_rows.append({
            'merchant_consolidated': merchant,
            'total_spend': nonzero.sum(),
            'mean_monthly': nonzero.mean(),
            'cv': cv,
            'months_active': len(nonzero),
        })

consistency_df = pd.DataFrame(consist_rows)
consistency_df = consistency_df[consistency_df['total_spend'] >= 10000].copy()

# Cap CV at 500% to prevent renderer overflow from extreme outliers
if len(consistency_df) > 0:
    consistency_df['cv'] = consistency_df['cv'].clip(upper=500)

# ---------------------------------------------------------------------------
# Merchant cohort (new / returning / lost per month)
# ---------------------------------------------------------------------------
sorted_months_m = sorted(combined_df['year_month'].unique())
_merch_valid = combined_df[combined_df['merchant_consolidated'].notna()]
first_month_map = _merch_valid.groupby('merchant_consolidated')['year_month'].min()
monthly_sets = {m: set(_merch_valid[_merch_valid['year_month'] == m]['merchant_consolidated'].unique())
                for m in sorted_months_m}

cohort_rows = []
for i, month in enumerate(sorted_months_m):
    current = monthly_sets[month]
    new_m = {m for m in current if m in first_month_map.index and first_month_map[m] == month}
    if i > 0:
        prev = monthly_sets[sorted_months_m[i - 1]]
        returning = {m for m in current if m not in prev and m in first_month_map.index and first_month_map[m] != month}
        lost = prev - current
    else:
        returning = set()
        lost = set()
    continuing = current - new_m - returning

    cohort_rows.append({
        'year_month': month,
        'total': len(current), 'new': len(new_m),
        'returning': len(returning), 'continuing': len(continuing),
        'lost': len(lost),
    })

cohort_df = pd.DataFrame(cohort_rows)

# ---------------------------------------------------------------------------
# Conference-styled top 20 table
# ---------------------------------------------------------------------------
m_display = merch_top20[['rank', 'merchant_consolidated', 'txn_count', 'txn_pct',
                          'unique_accounts', 'total_spend', 'txn_per_account']].copy()
m_display.columns = ['Rank', 'Merchant', 'Transactions', 'Txn %',
                      'Accounts', 'Total Spend', 'Txns/Acct']
m_display['Merchant'] = m_display['Merchant'].str[:35]

styled = (
    m_display.style
    .hide(axis='index')
    .format({
        'Rank': '{:.0f}',
        'Transactions': '{:,.0f}',
        'Txn %': '{:.1f}%',
        'Accounts': '{:,.0f}',
        'Total Spend': '${:,.0f}',
        'Txns/Acct': '{:.1f}',
    })
    .set_properties(**{
        'font-size': '13px', 'font-weight': 'bold',
        'text-align': 'center', 'border': '1px solid #E9ECEF',
        'padding': '7px 10px',
    })
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', GEN_COLORS['primary']), ('color', 'white'),
            ('font-size', '14px'), ('font-weight', 'bold'),
            ('text-align', 'center'), ('padding', '8px 10px'),
        ]},
        {'selector': 'caption', 'props': [
            ('font-size', '22px'), ('font-weight', 'bold'),
            ('color', GEN_COLORS['dark_text']), ('text-align', 'left'),
            ('padding-bottom', '12px'),
        ]},
    ])
    .set_caption("Top 20 Merchants by Transaction Volume")
    .bar(subset=['Transactions'], color=GEN_COLORS['info'], vmin=0)
)

display(styled)

top5_share_m = merch_agg.head(5)['txn_pct'].sum()
top10_share_m = merch_agg.head(10)['txn_pct'].sum()
print(f"\n    {len(merch_agg)} total merchants")
print(f"    Top 5 = {top5_share_m:.1f}% of transactions")
print(f"    Top 10 = {top10_share_m:.1f}% of transactions")
print(f"    Top 20 = {merch_top20['txn_pct'].sum():.1f}% of transactions")
print(f"    Consistency metrics: {len(consistency_df)} merchants with $10K+ spend")
