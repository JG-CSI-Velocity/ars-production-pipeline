# ===========================================================================
# PERSONAL ACCOUNT DATA: Master Aggregation Pipeline (Conference Edition)
# ===========================================================================
# Single aggregation for personal account merchants.
# Builds: pers_agg, pers_top20, pers_monthly, pers_consistency_df, pers_cohort_df.

# ---------------------------------------------------------------------------
# Safety: fill any remaining NaN merchant names
# ---------------------------------------------------------------------------
_pers_nan = personal_df['merchant_consolidated'].isna().sum()
if _pers_nan > 0:
    personal_df['merchant_consolidated'] = personal_df['merchant_consolidated'].fillna('UNKNOWN MERCHANT')
    print(f"    Filled {_pers_nan:,} NaN merchant names with 'UNKNOWN MERCHANT'")

# ---------------------------------------------------------------------------
# Core merchant aggregation (personal accounts only)
# ---------------------------------------------------------------------------
pers_agg = personal_df.groupby('merchant_consolidated').agg(
    txn_count=('transaction_date', 'count'),
    unique_accounts=('primary_account_num', 'nunique'),
    total_spend=('amount', 'sum'),
    avg_spend=('amount', 'mean'),
    median_spend=('amount', 'median'),
).reset_index()

total_txns_pers = len(personal_df)
total_accts_pers = personal_df['primary_account_num'].nunique()

pers_agg['txn_pct'] = pers_agg['txn_count'] / total_txns_pers * 100
pers_agg['acct_pct'] = pers_agg['unique_accounts'] / total_accts_pers * 100
pers_agg['txn_per_account'] = pers_agg['txn_count'] / pers_agg['unique_accounts']
pers_agg = pers_agg.sort_values('txn_count', ascending=False).reset_index(drop=True)
pers_agg['cumulative_txn_pct'] = pers_agg['txn_pct'].cumsum()
pers_agg['rank'] = range(1, len(pers_agg) + 1)

# Top slices
pers_top20 = pers_agg.head(20).copy()
pers_top50 = pers_agg.head(50).copy()

# ---------------------------------------------------------------------------
# Monthly merchant trend (top 10 personal merchants)
# ---------------------------------------------------------------------------
top10_pers = pers_agg.head(10)['merchant_consolidated'].tolist()
pers_monthly = personal_df[personal_df['merchant_consolidated'].isin(top10_pers)].groupby(
    ['year_month', 'merchant_consolidated']
).agg(txn_count=('transaction_date', 'count')).reset_index()

monthly_totals_pers = personal_df.groupby('year_month').size().reset_index(name='month_total')
pers_monthly = pers_monthly.merge(monthly_totals_pers, on='year_month')
pers_monthly['share_pct'] = pers_monthly['txn_count'] / pers_monthly['month_total'] * 100

# ---------------------------------------------------------------------------
# Spend consistency (CV per merchant, personal transactions only)
# ---------------------------------------------------------------------------
p_monthly_spend = personal_df.groupby(
    ['merchant_consolidated', 'year_month']
)['amount'].sum().reset_index()

p_pivot = p_monthly_spend.pivot(
    index='merchant_consolidated', columns='year_month', values='amount'
).fillna(0)

pers_consist_rows = []
for merchant in p_pivot.index:
    vals = p_pivot.loc[merchant].values
    nonzero = vals[vals > 0]
    if len(nonzero) >= 3 and nonzero.mean() > 0:
        cv = nonzero.std() / nonzero.mean() * 100
        pers_consist_rows.append({
            'merchant_consolidated': merchant,
            'total_spend': nonzero.sum(),
            'mean_monthly': nonzero.mean(),
            'cv': cv,
            'months_active': len(nonzero),
        })

pers_consistency_df = pd.DataFrame(pers_consist_rows)
pers_consistency_df = pers_consistency_df[pers_consistency_df['total_spend'] >= 10000].copy()

# Cap CV at 500% to prevent renderer overflow
if len(pers_consistency_df) > 0:
    pers_consistency_df['cv'] = pers_consistency_df['cv'].clip(upper=500)

# ---------------------------------------------------------------------------
# Merchant cohort (new / returning / lost per month)
# ---------------------------------------------------------------------------
sorted_months_pers = sorted(personal_df['year_month'].unique())
_pers_valid = personal_df[personal_df['merchant_consolidated'].notna()]
first_month_map_pers = _pers_valid.groupby('merchant_consolidated')['year_month'].min()
monthly_sets_pers = {m: set(_pers_valid[_pers_valid['year_month'] == m]['merchant_consolidated'].unique())
                     for m in sorted_months_pers}

pers_cohort_rows = []
for i, month in enumerate(sorted_months_pers):
    current = monthly_sets_pers[month]
    new_m = {m for m in current if first_month_map_pers[m] == month}
    if i > 0:
        prev = monthly_sets_pers[sorted_months_pers[i - 1]]
        returning = {m for m in current if m not in prev and first_month_map_pers[m] != month}
        lost = prev - current
    else:
        returning = set()
        lost = set()
    continuing = current - new_m - returning

    pers_cohort_rows.append({
        'year_month': month,
        'total': len(current), 'new': len(new_m),
        'returning': len(returning), 'continuing': len(continuing),
        'lost': len(lost),
    })

pers_cohort_df = pd.DataFrame(pers_cohort_rows)

# ---------------------------------------------------------------------------
# Conference-styled top 20 table
# ---------------------------------------------------------------------------
p_display = pers_top20[['rank', 'merchant_consolidated', 'txn_count', 'txn_pct',
                         'unique_accounts', 'total_spend', 'txn_per_account']].copy()
p_display.columns = ['Rank', 'Merchant', 'Transactions', 'Txn %',
                      'Accounts', 'Total Spend', 'Txns/Acct']
p_display['Merchant'] = p_display['Merchant'].str[:35]

styled = (
    p_display.style
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
            ('background-color', GEN_COLORS['success']), ('color', 'white'),
            ('font-size', '14px'), ('font-weight', 'bold'),
            ('text-align', 'center'), ('padding', '8px 10px'),
        ]},
        {'selector': 'caption', 'props': [
            ('font-size', '22px'), ('font-weight', 'bold'),
            ('color', GEN_COLORS['dark_text']), ('text-align', 'left'),
            ('padding-bottom', '12px'),
        ]},
    ])
    .set_caption("Top 20 Personal Account Merchants by Transaction Volume")
    .bar(subset=['Transactions'], color=GEN_COLORS['success'], vmin=0)
)

display(styled)

top5_share_pers = pers_agg.head(5)['txn_pct'].sum()
top10_share_pers = pers_agg.head(10)['txn_pct'].sum()
print(f"\n    {len(pers_agg)} personal merchants")
print(f"    Top 5 = {top5_share_pers:.1f}% of personal transactions")
print(f"    Top 10 = {top10_share_pers:.1f}% of personal transactions")
print(f"    Top 20 = {pers_top20['txn_pct'].sum():.1f}% of personal transactions")
print(f"    Consistency metrics: {len(pers_consistency_df)} merchants with $10K+ personal spend")
